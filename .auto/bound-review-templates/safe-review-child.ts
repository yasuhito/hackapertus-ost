// Explicitly loaded by the pinned package runner inside one private Node case.
export default function (pi: any) {
  const context = (globalThis as any)[Symbol.for('ost-safe-review-context')];
  if (!context) throw new Error('NO_SAFE_REVIEW_CONTEXT');
  context.register(pi);
}
