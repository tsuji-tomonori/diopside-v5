import { buildFinalEvidenceCandidateStatus, finalCandidateStatusPath } from "./final-evidence-candidate.js";
import { isCurrentJstTimestamp } from "./lib.js";

const status = buildFinalEvidenceCandidateStatus();
if (!isCurrentJstTimestamp(status.generated_at)) {
  console.log(`final evidence candidate generated_at is stale: ${status.generated_at}`);
  process.exitCode = 1;
}
if (status.ready) {
  console.log(`final evidence candidate check passed: ${finalCandidateStatusPath}`);
} else {
  console.log(`final evidence candidate not ready: ${finalCandidateStatusPath}`);
  if (status.errors.length > 0) {
    for (const error of status.errors) console.log(`- ${error}`);
    process.exitCode = 1;
  }
}
