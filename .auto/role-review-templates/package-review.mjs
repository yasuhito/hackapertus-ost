// Pinned runAgent adapter, not a generic manager or model-selecting tool.
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { registerHooks } from 'node:module';
import { sdk } from './dependencies.mjs';


export async function packageReview({ input, model, runtime, factory, events }) {
  const home = process.env.HOME;
  if (!home?.startsWith('/tmp/ost-pi-') || home !== process.env.PI_CODING_AGENT_DIR) throw new Error('PRIVATE_REVIEW_CONFIG_REQUIRED');
  const root = process.env.PI_SUBAGENTS_ROOT ?? dirname(fileURLToPath(import.meta.resolve('@tintinweb/pi-subagents/package.json')));
  if (JSON.parse(readFileSync(join(root, 'package.json'), 'utf8')).version !== '0.19.0') throw new Error('SUBAGENTS_VERSION_REFUSED');
  const sdkEntry = process.env.PI_PACKAGE_ROOT ? pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')).href : import.meta.resolve('@earendil-works/pi-coding-agent');
  // Installed Pi packages omit host peers. Resolve only those code modules to
  // the exact Pi installation already loaded, preserving its class/runtime identity.
  const aliases = {
    '@earendil-works/pi-coding-agent': sdkEntry,
    '@earendil-works/pi-ai': new URL('../../pi-ai/dist/index.js', sdkEntry).href,
    '@earendil-works/pi-tui': new URL('../../pi-tui/dist/index.js', sdkEntry).href,
    '@earendil-works/pi-agent-core': new URL('../../pi-agent-core/dist/index.js', sdkEntry).href,
  };
  const symbol = Symbol.for('ost-safe-review-context');
  const workspace = join(home, 'review-workspace');
  mkdirSync(workspace, { mode: 0o700 });
  const settings = { defaultTools: [], compaction: { enabled: false }, retry: { enabled: false, maxRetries: 0, provider: { maxRetries: 0 } }, cacheWarming: 'off', enableInstallTelemetry: false, enableAnalytics: false, defaultProjectTrust: 'never', extensions: ['-builtin:mcp', '-builtin:llama.cpp', '-builtin:codemode', '-builtin:tool-search'] };
  // Ordinary child created pinned deny settings. Reviewer reuses read-only.
  if (readFileSync(join(home, 'settings.json'), 'utf8') !== JSON.stringify(settings)) throw new Error('REVIEW_SETTINGS_REFUSED');
  if (globalThis[symbol]) throw new Error('REVIEW_CONTEXT_ALREADY_SET');
  const hook = registerHooks({ resolve(specifier, context, next) {
    if (context.parentURL?.startsWith(pathToFileURL(root + '/').href) && aliases[specifier]) return { url: aliases[specifier], shortCircuit: true };
    return next(specifier, context);
  } });
  let types;
  globalThis[symbol] = Object.freeze({ register: factory });
  try {
    const runner = await import(pathToFileURL(join(root, 'dist/agent-runner.js')).href);
    types = await import(pathToFileURL(join(root, 'dist/agent-types.js')).href);
    types.setDefaultsDisabled(true); types.setFallbackSubagent('none');
    const plugin = fileURLToPath(new URL('./safe-review-child.ts', import.meta.url));
    types.registerAgents(new Map([['ost-safe-review', {
      name: 'ost-safe-review', description: 'Independent limited-axis source review',
      builtinToolNames: [], extSelectors: ['ext:safe-review-child/review_source'],
      extensions: [plugin], skills: false, persistSession: false, outputTranscript: false,
      allowedSubagents: [], promptMode: 'replace',
      systemPrompt: input.review_system,
    }]]));
    runner.setRememberAgents(false); runner.setGraceTurns(1);
    const ctx = { cwd: workspace, model, modelRegistry: new sdk.ModelRegistry(runtime), sessionManager: sdk.SessionManager.inMemory(workspace), getSystemPrompt: () => input.review_system };
    // The package probes git via pi.exec. This headless host grants no process
    // execution; detectEnv catches refusal and records "not a git repository".
    const pi = { exec: async () => { throw new Error('CHILD_PROCESS_EXECUTION_DENIED'); } };
    events.push({ role: 'reviewer', type: 'package_review_started', package: '@tintinweb/pi-subagents', version: '0.19.0', api: 'runAgent' });
    // Soft limit deliberately exceeds the hard two-completion provider cap:
    // maxTurns=2 would queue a gratuitous steering turn after a valid repair.
    const result = await runner.runAgent(ctx, 'ost-safe-review', input.user, { pi, model, cwd: workspace, configCwd: workspace, nested: true, inheritContext: false, thinkingLevel: 'off', maxTurns: 3,
      onToolActivity: activity => events.push({ role: 'reviewer', type: 'package_tool_' + activity.type, toolName: activity.toolName }),
    });
    try {
      await result.session.waitForIdle();
      const tools = result.session.getActiveToolNames();
      if (result.session.model.id !== model.id || result.session.model.provider !== model.provider || tools.length !== 1 || tools[0] !== 'review_source') throw new Error('PACKAGE_REVIEW_SCOPE_REFUSED');
      events.push({ role: 'reviewer', type: 'package_review_completed', api: 'runAgent', model: result.session.model.id, provider: model.provider, tools, steered: result.steered, aborted: result.aborted });
      events.push({ role: 'reviewer', type: 'agent_settled' });
    } finally { result.session.dispose(); }
  } finally {
    try { types?.registerAgents(new Map()); }
    finally { delete globalThis[symbol]; hook.deregister(); }
  }
}
