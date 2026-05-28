import { assert, listFiles, readJson, readText } from "./lib.js";

const packageFiles = listFiles(["apps", "packages"], (path) => path.endsWith("package.json"));
for (const file of packageFiles) {
  const pkg = readJson(file);
  assert(pkg.name?.startsWith("@saphnexa/") || pkg.name === "saphnexa", `${file} has invalid package name`);
  assert(pkg.type === "module", `${file} must use ESM type=module`);
}

for (const file of listFiles(["packages/api-contract", "packages/tool-contract", "packages/domain"], (path) => path.endsWith(".js"))) {
  const body = readText(file);
  assert(body.includes("export "), `${file} must export its public surface`);
}

console.log("type surface check passed");
