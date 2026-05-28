import { assert, listFiles, readJson } from "./lib.js";

const packageFiles = listFiles(["."], (path) => path.endsWith("package.json"));
const deniedLicenses = new Set(["GPL-2.0", "GPL-3.0", "AGPL-3.0"]);

for (const file of packageFiles) {
  const pkg = readJson(file);
  assert(pkg.private === true, `${file} must be private until license policy is finalized`);
  for (const section of ["dependencies", "devDependencies", "optionalDependencies"]) {
    const deps = pkg[section] || {};
    for (const [name, value] of Object.entries(deps)) {
      assert(typeof value === "string" && value.length > 0, `${file} has invalid dependency ${name}`);
    }
  }
  if (pkg.license) assert(!deniedLicenses.has(pkg.license), `${file} uses denied license ${pkg.license}`);
}

console.log(`license scan passed (${packageFiles.length} package manifests)`);
