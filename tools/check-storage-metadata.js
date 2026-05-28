import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert, listFiles, readText } from "./lib.js";

const api = createLocalApi();
const csrf_token = api.request("admin-1", "getMe").body.csrf_token;
const created = api.request("admin-1", "createDocument", {
  csrf_token,
  title: "storage metadata",
  file_name: "storage.pdf",
  metadata: {
    document_id: "doc-storage",
    version: "v1",
    acl_scope: "admin",
    status: "uploaded",
    page: 1,
    section: "1"
  }
});

assert(created.status === 202, "document create must succeed with complete metadata");
assert(created.body.raw_s3_uri.startsWith("s3://saphnexa-local/raw/"), "raw S3 URI must use raw prefix");
const job = api.store.state.ingestion_jobs.find((item) => item.job_id === created.body.job_id);
assert(job.parsed_s3_prefix.startsWith("s3://saphnexa-local/parsed/"), "parsed artifacts must use parsed prefix");

const files = listFiles(["apps", "packages", "infra"], (path) => /\.(js|ts|tsx|json|yml|yaml|sql)$/.test(path));
for (const file of files) {
  assert(!readText(file).toLowerCase().includes("opensearch"), `${file} must not introduce OpenSearch dependency`);
}

console.log("storage metadata check passed");
