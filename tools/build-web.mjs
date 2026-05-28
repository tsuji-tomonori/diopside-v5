import { cp, mkdir, rm } from "node:fs/promises";
import { join } from "node:path";

const out = "build/web";
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
await cp("apps/web/public", out, { recursive: true });
await mkdir(join(out, "data"), { recursive: true });
await cp("data/fixtures/public/latest-manifest.json", join(out, "data/latest-manifest.json"));
await cp("data/fixtures/public/data", join(out, "data"), { recursive: true });
console.log(`built static web to ${out}`);
