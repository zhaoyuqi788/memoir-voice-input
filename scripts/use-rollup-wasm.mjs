import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);

try {
  require("rollup/dist/native.js");
  process.exit(0);
} catch (error) {
  if (!String(error?.message ?? "").includes("@rollup/rollup-")) {
    console.warn("Rollup native loader failed, but not with the optional native package error.");
  }
}

try {
  require("@rollup/wasm-node/dist/native.js");
} catch {
  console.warn("@rollup/wasm-node is unavailable; leaving Rollup native loader unchanged.");
  process.exit(0);
}

const projectRoot = dirname(fileURLToPath(new URL("../package.json", import.meta.url)));
const nativePath = join(projectRoot, "node_modules", "rollup", "dist", "native.js");
const shim = `const wasmNative = require("@rollup/wasm-node/dist/native.js");

module.exports.parse = wasmNative.parse;
module.exports.parseAsync = wasmNative.parseAsync;
module.exports.xxhashBase64Url = wasmNative.xxhashBase64Url;
module.exports.xxhashBase36 = wasmNative.xxhashBase36;
module.exports.xxhashBase16 = wasmNative.xxhashBase16;
`;

writeFileSync(nativePath, shim, "utf8");
console.log("Patched Rollup to use @rollup/wasm-node native shim.");
