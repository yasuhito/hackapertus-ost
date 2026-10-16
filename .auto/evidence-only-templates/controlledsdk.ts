/** Actual Pi 1.1.0 sessions. Nonstream wire completions bridged through Python. */
import { createHash } from 'node:crypto';
import { sdk, ai, AuthStorage, loadExtensionFromFactory } from './dependencies.mjs';
import { createSubmitExtension, SUBMIT_PROTOCOL } from './submit-extension.ts';
import { packageReview } from './package-review.mjs';
import { factoryReviewTool } from './review-extension.ts';

const MODELS = ['swiss-ai/Apertus-v1.5-8B', 'swiss-ai/Apertus-v1.5-70B'];
const zeroUsage = () => ({ input: 0, output: 0, cacheRead: 0, cacheWrite: 0, reasoning: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } });

/** Wire-only projection. Pi and the Python assembler retain strict local schemas. */
export function nativeTools(tools: any[], ids: string[], reviewSchema: any) {
  return tools.map(t => {
    let parameters: any;
    if (t.name === 'submit') parameters = {
      type: 'object', additionalProperties: false, required: ['label', 'candidate_ids'],
      properties: {
        label: { type: 'integer', enum: [0, 1, 2] },
        candidate_ids: { type: 'array', items: { type: 'string', enum: [...ids] }, maxItems: 5 },
      },
    };
    else if (t.name === 'subagent') parameters = {
      type: 'object', additionalProperties: false, required: ['mode'],
      properties: { mode: { type: 'string', enum: ['source_only'] } },
    };
    else if (t.name === 'review_source') parameters = reviewSchema;
    else throw new Error('UNDECLARED_NATIVE_TOOL');
    return { type: 'function', function: { name: t.name, description: t.description, parameters } };
  });
}

function wireMessages(context: any) {
  const collapsed = ai.collapseSystemMessages(context);
  return collapsed.messages.map((m: any) => {
    if (m.role === 'toolResult') return { role: 'tool', tool_call_id: m.toolCallId, content: m.content.map((b: any) => b.text ?? '').join('') };
    if (m.role === 'assistant') {
      const calls = m.content.filter((b: any) => b.type === 'toolCall');
      return { role: 'assistant', content: m.content.filter((b: any) => b.type === 'text').map((b: any) => b.text).join('') || null,
        ...(calls.length ? { tool_calls: calls.map((b: any) => ({ id: b.id, type: 'function', function: { name: b.name, arguments: JSON.stringify(b.arguments) } })) } : {}) };
    }
    return { role: m.role, content: m.role === 'system' ? ai.getSystemMessageText(m) : (typeof m.content === 'string' ? m.content : m.content.map((b: any) => b.text ?? '').join('')) };
  });
}

export async function runSdk(input: any, bridge: (kind: string, data: any) => Promise<any>) {
  if (!MODELS.includes(input.model)) throw new Error('MODEL_REFUSED');
  const strategy = input.strategy ?? 'B';
  const childModel = input.child_model ?? input.model;
  if (!(strategy === 'B' && childModel === input.model || strategy === 'C' && input.model === MODELS[1] && childModel === MODELS[0])) throw new Error('ROLE_MODEL_REFUSED');
  if (strategy !== 'C') throw new Error('ROLE_MODEL_REFUSED');
  const counts = { parent: 0, child: 0, reviewer: 0 };
  let helperInvoked = false;
  let reviewReport: any;
  let reviewReason = 'no_accepted_report';
  const events: any[] = [];
  const ids = input.ids;
  const runtime = await sdk.ModelRuntime.create({ credentials: AuthStorage.inMemory(), modelsPath: null, modelsStore: new ai.InMemoryModelsStore(), refreshOnCreate: false, allowModelNetwork: false });
  async function sessionRun(role: 'parent' | 'child') {
    let recommendation: any;
    const usage = zeroUsage();
    const provider = 'ost-stdio-' + role;
    const roleModel = role === 'parent' ? input.model : childModel;
    const model: any = { id: roleModel, name: roleModel, provider, api: 'ost-stdio-completions', baseUrl: 'stdio://python', reasoning: false, input: ['text'], contextWindow: 262144, maxTokens: 256, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } };
    runtime.registerProvider(provider, {
      api: model.api, apiKey: 'stdio-not-a-credential', models: [model],
      streamSimple: (m: any, context: any, options: any = {}) => {
        const stream = new ai.AssistantMessageEventStream();
        const message: any = { role: 'assistant', api: m.api, provider: m.provider, model: m.id, timestamp: Date.now(), stopReason: 'pending', content: [], usage: zeroUsage() };
        (async () => {
          try {
            if (options.signal?.aborted) throw new Error('ABORTED');
            if (recommendation || (role === 'child' && reviewReport) || counts[role] >= (role === 'parent' ? 3 : 2)) throw new Error('CALL_LIMIT');
            const tools = nativeTools(ai.getCurrentTools(context.messages), ids, input.review_schema);
            const messages = wireMessages(context);
            // Only normalize package-generated environment metadata, never source.
            if (role !== 'parent') {
              const part = 'review';
              const cwd = process.env.HOME + '/' + part + '-workspace';
              messages[0].content = messages[0].content.replace('Working directory: ' + cwd, 'Working directory: /tmp/ost-private-' + part)
                .replace('\n\n<cwd>\n' + cwd + '\n</cwd>', '\n\n<cwd>\n/tmp/ost-private-' + part + '\n</cwd>');
            }
            let payload: any = { model: m.id, messages, temperature: 0, max_tokens: 256, stream: false, tools,
              tool_choice: { type: 'function', function: { name: role === 'child' ? 'review_source' : role === 'parent' && counts.parent === 0 ? 'subagent' : 'submit' } } };
            payload = await options.onPayload?.(payload, m) ?? payload;
            counts[role]++;
            const response = await bridge('request', { role, payload });
            await options.onResponse?.({ status: 200, headers: {} }, m);
            await options.onProviderStreamEvent?.(response, m);
            stream.push({ type: 'start', partial: message });
            const u = response.usage;
            const cacheRead = u.prompt_tokens_details?.cached_tokens ?? 0;
            message.usage = { ...zeroUsage(), input: u.prompt_tokens - cacheRead, output: u.completion_tokens, cacheRead, totalTokens: u.total_tokens, reasoning: u.completion_tokens_details?.reasoning_tokens ?? 0 };
            usage.input += message.usage.input; usage.output += message.usage.output; usage.cacheRead += cacheRead; usage.reasoning += message.usage.reasoning; usage.totalTokens += u.total_tokens;
            const choice = response.choices[0];
            if (role === 'child') {
              if (response.review_rejection) reviewReason = response.review_rejection;
              else if (choice.finish_reason === 'length') reviewReason = 'incomplete_review';
              else if (!choice.message.tool_calls?.length) reviewReason = 'no_review_tool_call';
            }
            message.responseId = response.id;
            message.rawStopReason = choice.finish_reason;
            if (typeof choice.message.content === 'string' && choice.message.content.length) {
              const text = choice.message.content;
              const i = message.content.length; message.content.push({ type: 'text', text: '' });
              stream.push({ type: 'text_start', contentIndex: i, partial: message });
              message.content[i].text = text; stream.push({ type: 'text_delta', contentIndex: i, delta: text, partial: message });
              stream.push({ type: 'text_end', contentIndex: i, content: text, partial: message });
            }
            for (const call of choice.message.tool_calls ?? []) {
              const i = message.content.length;
              const block = { type: 'toolCall', id: call.id, name: call.function.name, arguments: {} };
              message.content.push(block); stream.push({ type: 'toolcall_start', contentIndex: i, partial: message });
              const raw = call.function.arguments;
              // Python has parsed duplicate keys strictly. It returns parsed_arguments.
              block.arguments = call.parsed_arguments;
              stream.push({ type: 'toolcall_delta', contentIndex: i, delta: raw, partial: message });
              stream.push({ type: 'toolcall_end', contentIndex: i, toolCall: block, partial: message });
            }
            message.stopReason = choice.finish_reason === 'length' ? 'length' : (message.content.some((b: any) => b.type === 'toolCall') ? 'toolUse' : 'stop');
            stream.push({ type: 'done', reason: message.stopReason, message });
          } catch (error: any) {
            message.stopReason = options.signal?.aborted ? 'aborted' : 'error';
            message.errorMessage = error.message === 'CALL_LIMIT' ? 'CALL_LIMIT' : 'BRIDGE_FAILED';
            stream.push({ type: 'error', reason: message.stopReason, error: message });
          } finally { stream.end(); }
        })();
        return stream;
      },
    });
    const extensionRuntime = sdk.createExtensionRuntime();
    const submitFactory = role === 'child' ? factoryReviewTool(input.review_schema, async (args: any) => {
      const result = await bridge('review', { role, args });
      if (result.ok) reviewReport = result.source_review;
      else reviewReason = result.error;
      return result;
    }) : createSubmitExtension(ids, async (kind, args) => {
      const result = await bridge(kind, { role, args });
      if (result.ok) recommendation = args;
      return result;
    }, role === 'parent' ? async () => {
      if (helperInvoked) throw new Error('DUPLICATE_HELPER_INVOCATION');
      helperInvoked = true;
      const reviewed = await sessionRun('child');
      events.push({ role: 'parent', type: 'subagent_usage', usage: reviewed.usage });
      return { recommendation: { source_review: reviewReport ?? { status: 'review_unavailable', reason: reviewReason, note: input.review_note } }, usage: reviewed.usage };
    } : undefined);
    const factory = (pi: any) => {
      submitFactory(role === 'parent' ? new Proxy(pi, { get(target, key) {
        if (key === 'registerTool') return (tool: any) => target.registerTool(tool.name === 'subagent' ? { ...tool, description: 'Obtain one independent depth-one source-fact localization report, including matching facts. The helper provides no NLI recommendation, verdict or vote. Call with compact arguments {"mode":"source_only"}; no blank lines. Parent must submit the final decision.' } : tool);
        const value = target[key]; return typeof value === 'function' ? value.bind(target) : value;
      } }) : pi);
      for (const type of ['before_provider_request', 'after_provider_response', 'provider_stream_event']) pi.on(type, () => { events.push({ role, type, model: model.id }); });
    };
    if (role === 'child') {
      events.push({ role, type: 'independent_input', sha256: createHash('sha256').update(input.review_user).digest('hex'), model: model.id });
      await packageReview({ input, model, runtime, factory, events });
      return { usage };
    }
    const extension = await loadExtensionFromFactory(factory, '/tmp', sdk.createEventBus(), extensionRuntime, 'ost-submit');
    const resourceLoader = {
      getExtensions: () => ({ extensions: [extension], errors: [], runtime: extensionRuntime }),
      getSkills: () => ({ skills: [], diagnostics: [] }), getPrompts: () => ({ prompts: [], diagnostics: [] }),
      getThemes: () => ({ themes: [], diagnostics: [] }), getAgentsFiles: () => ({ agentsFiles: [] }),
      getSystemPrompt: () => input.system + '\nUse only the declared tools. Do not return a text submission. ' + SUBMIT_PROTOCOL + ' ' + (role === 'child' ? 'Submit a recommendation. Use compact JSON arguments, no blank lines.' : 'First call subagent with compact arguments {"mode":"source_only"}; no blank lines. Then submit your final decision.'),
      getSystemPromptSource: () => undefined, getAppendSystemPrompt: () => [], getAppendSystemPromptSources: () => [], extendResources: () => {}, reload: async () => {},
    };
    const settingsManager = sdk.SettingsManager.inMemory({ defaultTools: [], compaction: { enabled: false }, retry: { enabled: false, maxRetries: 0, provider: { maxRetries: 0 } }, cacheWarming: 'off', enableInstallTelemetry: false, enableAnalytics: false });
    const { session } = await sdk.createAgentSession({ cwd: '/tmp', agentDir: '/tmp/ost-no-discovery', modelRuntime: runtime, model, thinkingLevel: 'off', resourceLoader, tools: role === 'parent' ? ['submit', 'subagent'] : ['submit'], sessionManager: sdk.SessionManager.inMemory('/tmp'), settingsManager });
    const unsubscribe = session.subscribe((event: any) => {
      if (['agent_settled', 'tool_execution_start', 'tool_execution_end', 'auto_retry_start', 'auto_compaction_start'].includes(event.type)) events.push({ role, type: event.type, toolName: event.toolName, isError: event.isError });
    });
    try {
      await session.bindExtensions({});
      await session.prompt(input.user, { expandPromptTemplates: false });
      await session.waitForIdle();
      return { recommendation, usage };
    } finally { unsubscribe(); session.dispose(); }
  }
  const result = await sessionRun('parent');
  return { recommendation: result.recommendation ?? null, counts, events, source_review: reviewReport ?? { status: 'review_unavailable', reason: reviewReason, note: input.review_note } };
}
