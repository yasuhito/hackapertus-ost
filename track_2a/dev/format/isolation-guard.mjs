// Offline test preload. Denies config/discovery reads and ALL Node networking.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import net from 'node:net';
import http from 'node:http';
import https from 'node:https';
import { syncBuiltinESMExports } from 'node:module';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
function check(path) {
  const p = path instanceof URL ? fileURLToPath(path) : String(path);
  // The package is permitted to inspect only its private noncredential config.
  // Authentication/model files remain forbidden even in that directory.
  if (/(?:^|\/)(?:auth\.json|models\.json|models-store\.json)$/.test(p)) throw new Error('AUTH_OR_MODEL_FILE_READ_DENIED');
  const home = process.env.HOME;
  if (home?.startsWith('/tmp/ost-pi-') && p.startsWith(home + '/')) return;
  const packages = process.env.PI_SUBAGENTS_ROOT;
  if (packages && p.startsWith(dirname(dirname(packages)) + '/')) return;
  if (/(?:^|\/)(?:auth\.json|models\.json|models-store\.json|settings\.json|mcp\.json|AGENTS(?:\.override)?\.md|CLAUDE\.md|SYSTEM\.md|APPEND_SYSTEM\.md)$/.test(p) || /\/\.pi\/(?!agent\/install\/releases\/)/.test(p) || /\/\.config\//.test(p)) throw new Error('GLOBAL_CONFIG_READ_DENIED');
}
for (const name of ['readFileSync', 'openSync', 'readdirSync', 'statSync', 'existsSync', 'accessSync']) {
  const original = fs[name];
  fs[name] = function(path, ...rest) { check(path); return original.call(this, path, ...rest); };
}
for (const name of ['readFile', 'open', 'readdir', 'stat', 'access']) {
  const original = fsp[name];
  fsp[name] = function(path, ...rest) { check(path); return original.call(this, path, ...rest); };
}
const deny = () => { throw new Error('NODE_NETWORK_DENIED'); };
net.connect = deny; net.createConnection = deny; net.Socket.prototype.connect = deny;
http.request = deny; http.get = deny; https.request = deny; https.get = deny;
globalThis.fetch = deny;
syncBuiltinESMExports();
