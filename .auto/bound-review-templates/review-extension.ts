import { Type } from './dependencies.mjs';

/** Separate auxiliary tool; never writes an NLI recommendation. */
export function factoryReviewTool(schema: any, bridge: (args: any) => Promise<any>) {
  let attempts = 0;
  let accepted = false;
  return (pi: any) => pi.registerTool({
    name: 'review_source', label: 'Independent source review',
    description: 'Select at most one relevant claim/source fragment ID pair on number, negation, condition or speaker, INCLUDING matching facts. checks:[] means no pair, not agreement or any semantic verdict. No NLI label or vote. At most one repair.',
    executionMode: 'sequential', parameters: Type.Unsafe(schema),
    execute: async (_id: any, args: any) => {
      if (accepted || ++attempts > 2) return { content: [{ type: 'text', text: 'REVIEW_LIMIT' }], isError: true, terminate: true };
      const result = await bridge(args);
      accepted = result.ok === true;
      return { content: [{ type: 'text', text: JSON.stringify(result) }], details: result, isError: !accepted, terminate: accepted || attempts >= 2 };
    },
  });
}
