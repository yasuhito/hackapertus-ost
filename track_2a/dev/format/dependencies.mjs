// Explicit package override is code location only, never a config directory.
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
const root = process.env.PI_PACKAGE_ROOT;
const entry = root ? pathToFileURL(join(root, 'dist/index.js')).href : import.meta.resolve('@earendil-works/pi-coding-agent');
const require = createRequire(entry);
export const sdk = await import(entry);
export const ai = await import(new URL('../../pi-ai/dist/index.js', entry));
export const { Type } = ai;
export const { AuthStorage } = await import(new URL('./core/auth-storage.js', entry));
export const { loadExtensionFromFactory } = await import(new URL('./core/extensions/loader.js', entry));
const packageInfo = require(join(dirname(new URL(entry).pathname), '../package.json'));
if (packageInfo.version !== '1.1.0') throw new Error('PI_VERSION_REFUSED');
