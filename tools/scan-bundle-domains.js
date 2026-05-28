import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const roots = ["apps/web", "packages/api-client"];
const forbidden = ["execute-api", "appsync-api", "appsync-realtime-api"];
const checkedFiles = [];

for (const root of roots) {
  walk(root);
}

for (const file of checkedFiles) {
  const body = readFileSync(file, "utf8");
  for (const token of forbidden) {
    if (body.includes(token)) {
      throw new Error(`${file} contains forbidden domain token ${token}`);
    }
  }
}

console.log(`bundle domain scan passed (${checkedFiles.length} files)`);

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      walk(path);
    } else if (/\.(ts|tsx|js|jsx)$/.test(path)) {
      checkedFiles.push(path);
    }
  }
}
