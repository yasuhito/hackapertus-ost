import { Type } from './dependencies.mjs';

/** Separate auxiliary tool; never writes an NLI recommendation. */
export function factoryReviewTool(schema: any, bridge: (args: any) => Promise<any>) {
  let attempts = 0;
  let accepted = false;
  return (pi: any) => pi.registerTool({
    name: 'select_source_spans', label: 'Original source-span retrieval',
    description: 'Retrieve up to two complete original source spans bearing on the same full claim proposition, supporting or opposing. candidate_ids:[] means no selection, not global proof or any verdict. At most one repair.',
    executionMode: 'sequential', parameters: Type.Unsafe(schema),
    execute: async (_id: any, args: any) => {
      if (accepted || ++attempts > 2) return { content: [{ type: 'text', text: 'REVIEW_LIMIT' }], isError: true, terminate: true };
      const result = await bridge(args);
      accepted = result.ok === true;
      return { content: [{ type: 'text', text: JSON.stringify(result) }], details: result, isError: !accepted, terminate: accepted || attempts >= 2 };
    },
  });
}
