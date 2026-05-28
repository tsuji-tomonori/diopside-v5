import { acceptanceCatalog, acceptanceCatalogPath, acceptanceIds, allowedTraceStates } from "./acceptance-ids.js";
import { assert, readText } from "./lib.js";

const trace = readText("docs/acceptance/traceability.md");
const rows = [...trace.matchAll(/^\| (AC-\d{3}) \| ([a-z_]+) \| (.+) \|$/gm)];
const seen = new Map(rows.map((match) => [match[1], match[2]]));

for (const id of acceptanceIds) {
  assert(seen.has(id), `traceability is missing ${id}`);
}

for (const [id, state] of seen) {
  assert(acceptanceIds.includes(id), `traceability has unknown ID ${id}`);
  assert(allowedTraceStates.includes(state), `${id} has invalid state ${state}`);
}

assert(seen.size === acceptanceIds.length, `expected ${acceptanceIds.length} AC rows from ${acceptanceCatalogPath}, got ${seen.size}`);
assert(seen.size === acceptanceCatalog.item_count, "traceability row count must match source catalog item_count");
console.log("acceptance trace check passed");
