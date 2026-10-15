import { Compile } from '/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/typebox/build/compile/index.mjs';
let input = '';
for await (const chunk of process.stdin) input += chunk;
const rows = JSON.parse(input);
console.log(JSON.stringify(rows.map(({schema, value}) => Compile(schema).Check(value))));
