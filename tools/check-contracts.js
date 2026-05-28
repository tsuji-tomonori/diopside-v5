import { readFileSync } from "node:fs";
import { assertPublicApiContract, errorResponseSchema, publicApiRoutes } from "../packages/api-contract/src/routes.js";
import { assertToolContract, toolContracts } from "../packages/tool-contract/src/tools.js";
import { requiredTables } from "../packages/db-schema/src/tables.js";
import { saphnexaConstructs } from "../infra/stacks/saphnexa-app-stack.js";

assertPublicApiContract();
assertToolContract();

if (!errorResponseSchema.required.includes("trace_id") || !errorResponseSchema.required.includes("error_code")) {
  throw new Error("ErrorResponse must include trace_id and error_code");
}

const migration = readFileSync("packages/db-migrations/migrations/V001__initial_saphnexa_schema.sql", "utf8");
for (const table of requiredTables) {
  if (!migration.includes(`CREATE TABLE ${table}`)) {
    throw new Error(`migration is missing ${table}`);
  }
}

if (saphnexaConstructs.length !== 7) {
  throw new Error(`expected 7 CDK construct definitions, got ${saphnexaConstructs.length}`);
}

const adminRoutes = publicApiRoutes.filter((route) => route.viewerPath.startsWith("/api/admin/"));
if (adminRoutes.some((route) => route.roles.join(",") !== "admin")) {
  throw new Error("admin routes must be admin-only");
}

const auditedTools = toolContracts.filter((tool) => tool.auditTable === "tool_invocations");
if (auditedTools.length !== 6) {
  throw new Error("all tools must audit to tool_invocations");
}

console.log("contract checks passed");
