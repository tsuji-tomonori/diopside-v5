import { readFile } from "node:fs/promises";
import { join } from "node:path";

const files = [
  "apps/web/public/app.js"
];

const forbidden = [
  "innerHTML",
  "outerHTML",
  "insertAdjacentHTML",
  "document.write",
  "DOMParser"
];

const violations = [];

for (const file of files) {
  const source = await readFile(join(process.cwd(), file), "utf8");
  for (const pattern of forbidden) {
    if (source.includes(pattern)) {
      violations.push(`${file}: forbidden DOM sink ${pattern}`);
    }
  }
}

if (violations.length) {
  throw new Error(`web DOM safety check failed:\n${violations.join("\n")}`);
}

console.log(`web DOM safety check passed (${files.length} files)`);
