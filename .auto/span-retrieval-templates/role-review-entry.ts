import { createInterface } from 'node:readline';
import { runSdk } from './controlledsdk.ts';
const lines = createInterface({ input: process.stdin });
let init: any;
let pending: ((value: any) => void) | undefined;
let sequence = 0;
const emit = (value: any) => process.stdout.write(JSON.stringify(value) + '\n');
lines.on('line', line => {
  const value = JSON.parse(line);
  if (!init) {
    init = value;
    void runSdk(init, (kind, data) => new Promise(resolve => {
      if (pending) throw new Error('CONCURRENT_BRIDGE_REFUSED');
      pending = resolve; emit({ kind, data, sequence: ++sequence });
    })).then(result => { emit({ kind: 'done', result }); lines.close(); })
      .catch(() => { emit({ kind: 'fatal', error: 'SDK_FAILED' }); lines.close(); process.exitCode = 1; });
  } else {
    if (!pending || value.sequence !== sequence) throw new Error('BRIDGE_SEQUENCE');
    const resolve = pending; pending = undefined; resolve(value.result);
  }
});
