import { assert, listFiles, readText } from "./lib.js";

const files = listFiles(["apps", "packages", "infra", "docs", "tests", "tools"], (path) => /\.(js|ts|tsx|json|md|yml|yaml|sql)$/.test(path));
const forbiddenPatterns = [
  /AWS_SECRET_ACCESS_KEY\s*=/,
  /AWS_ACCESS_KEY_ID\s*=/,
  /SECRET_KEY\s*=/,
  /REFRESH_TOKEN\s*=/,
  /-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /sk-[A-Za-z0-9_-]{20,}/,
  /AKIA[0-9A-Z]{16}/
];

for (const file of files) {
  const body = readText(file);
  for (const pattern of forbiddenPatterns) {
    assert(!pattern.test(body), `${file} contains forbidden secret-like pattern ${pattern}`);
  }
}

const baseline = readText("infra/aspects/security-baseline.js");
for (const rule of ["S3 Block Public Access", "SSE-KMS", "CloudFront must attach WAF", "IAM wildcard actions"]) {
  assert(baseline.includes(rule), `security baseline missing ${rule}`);
}

console.log(`security scan passed (${files.length} files)`);
