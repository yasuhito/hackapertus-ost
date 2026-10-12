// Explicitly loaded by the pinned package runner inside one private Node case.
export default function (pi: any) {
  const context = (globalThis as any)[Symbol.for('ost-safe-child-context')];
  if (!context) throw new Error('NO_SAFE_CHILD_CONTEXT');
  context.register(pi);
}
