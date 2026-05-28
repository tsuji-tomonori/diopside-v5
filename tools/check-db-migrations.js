import { createHash } from "node:crypto";
import { requiredTables } from "../packages/db-schema/src/tables.js";
import { assert, listFiles, readText } from "./lib.js";

const migrationFiles = listFiles(["packages/db-migrations/migrations"], (path) => /\/V\d+__.+\.sql$/.test(path));
assert(migrationFiles.length >= 1, "at least one Flyway versioned SQL migration is required");

for (const file of migrationFiles) {
  const name = file.split("/").at(-1);
  const body = readText(file);
  assert(/^V\d+__[\w_]+\.sql$/.test(name), `migration name is not Flyway-compatible: ${name}`);
  assert(!/drizzle|prisma|typeorm|sequelize/i.test(body), `${file} must not contain ORM auto migration markers`);
  assert(!/DROP\s+TABLE|DROP\s+COLUMN|TRUNCATE\s+TABLE/i.test(body), `${file} contains destructive migration statement`);
  assert(createHash("sha256").update(body).digest("hex").length === 64, `${file} checksum could not be calculated`);
}

const initial = readText("packages/db-migrations/migrations/V001__initial_saphnexa_schema.sql");
for (const table of requiredTables) {
  assert(new RegExp(`CREATE TABLE ${table}\\b`, "i").test(initial), `migration missing required table ${table}`);
}
for (const column of ["version", "script", "checksum", "execution_time", "success"]) {
  assert(new RegExp(`\\b${column}\\b`, "i").test(initial), `schema_migrations missing ${column}`);
}

const packageFiles = listFiles(["packages"], (path) => /package\.json$/.test(path));
for (const file of packageFiles) {
  const body = readText(file);
  assert(!/drizzle-kit|prisma migrate|typeorm migration|sequelize-cli/i.test(body), `${file} must not define ORM auto migration command`);
}

console.log(`DB migration check passed (${migrationFiles.length} versioned SQL files, ${requiredTables.length} required tables)`);
