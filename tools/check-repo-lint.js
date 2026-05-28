import { assert, listFiles, readText } from "./lib.js";

const files = listFiles(["apps", "packages", "infra", "docs", "tests", "tools"], (path) => /\.(js|ts|tsx|json|md|yml|yaml|sql)$/.test(path));

for (const file of files) {
  const body = readText(file);
  assert(!body.includes("\r\n"), `${file} contains CRLF line endings`);
  assert(!/[ \t]$/m.test(body), `${file} has trailing whitespace`);
  if (file.endsWith(".json")) JSON.parse(body);
}

console.log(`repo lint passed (${files.length} files)`);
