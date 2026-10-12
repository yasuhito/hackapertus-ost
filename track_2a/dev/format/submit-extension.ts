import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Type } from './dependencies.mjs';

type Bridge = (kind: string, data: unknown) => Promise<any>;

/** Scoped factory. Normal Pi loaders can supply the same frozen bridge via configure. */
export function createSubmitExtension(ids: string[], bridge: Bridge, child?: () => Promise<any>) {
  let attempts = 0;
  let accepted = false;
  let delegated = false;
  return (pi: ExtensionAPI) => {
    pi.registerTool({
      name: 'submit', label: 'Submit NLI',
      description: 'Select the NLI label and exact supporting candidate IDs. Script restores original evidence. At most one schema repair.',
      executionMode: 'sequential',
      parameters: Type.Object({
        label: Type.Union([Type.Literal(0), Type.Literal(1), Type.Literal(2)], { type: 'integer', enum: [0, 1, 2] }),
        candidate_ids: Type.Array(ids.length ? Type.Union(ids.map(id => Type.Literal(id))) : Type.Never(), { maxItems: 5, uniqueItems: true }),
      }, { additionalProperties: false }),
      execute: async (_id, params) => {
        if (accepted || ++attempts > 2) return { content: [{ type: 'text', text: 'SUBMIT_LIMIT' }], details: undefined, isError: true, terminate: true };
        const result = await bridge('assemble', params);
        accepted = result.ok === true;
        return { content: [{ type: 'text', text: JSON.stringify(result) }], details: result, isError: !accepted, terminate: accepted || attempts >= 2 };
      },
    });
    if (child) pi.registerTool({
      name: 'subagent', label: 'Source-only recommendation',
      description: 'Ask one depth-one agent with the same model and frozen source for a recommendation. Parent must submit the final decision.',
      executionMode: 'sequential', parameters: Type.Object({}, { additionalProperties: false }),
      execute: async () => {
        if (delegated || accepted) throw new Error('DELEGATION_LIMIT');
        delegated = true;
        const result = await child();
        return { content: [{ type: 'text', text: JSON.stringify(result.recommendation ?? { error: 'NO_CHILD_SUBMIT' }) }], details: result, usage: result.usage };
      },
    });
  };
}

// A normal Pi extension loads safely but requires host-owned source/assembler wiring.
export default function (pi: ExtensionAPI) {
  createSubmitExtension([], async () => ({ ok: false, error: 'NO_FROZEN_CASE_BRIDGE' }))(pi);
}
