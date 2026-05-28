import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expectedMajorOutputKeys, expectedMajorResourceTypeMinimumCounts, expectedMajorResourceTypes } from "./cloudformation-inventory.js";
import { buildFinalCloudFormationInventoryFromFiles, normalizeFinalCloudFormationInventory } from "./final-cloudformation-inventory.js";
import { assert, readJson } from "./lib.js";

const root = mkdtempSync(join(tmpdir(), "saphnexa-final-cfn-inventory-"));

try {
  const describeStacksPath = join(root, "describe-stacks.json");
  const listStackResourcesPath = join(root, "list-stack-resources.json");
  const outputPath = join(root, "cloudformation_inventory.uat.json");
  writeFileSync(describeStacksPath, `${JSON.stringify(describeStacksFixture(), null, 2)}\n`);
  writeFileSync(listStackResourcesPath, `${JSON.stringify(listStackResourcesFixture(), null, 2)}\n`);

  const inventory = buildFinalCloudFormationInventoryFromFiles({
    describeStacksPath,
    listStackResourcesPath,
    outputPath,
    capturedAt: "2026-05-27T12:00:00+09:00",
    generatedAt: "2026-05-27T12:00:00+09:00"
  });
  const written = readJson(outputPath);

  assert(JSON.stringify(inventory) === JSON.stringify(written), "written inventory must match returned inventory");
  assert(written.schema_version === "saphnexa-cloudformation-inventory.v1", "normalized inventory schema mismatch");
  assert(written.source === "aws-cloudformation-inventory", "normalized inventory source mismatch");
  assert(written.final_acceptance_eligible === true, "normalized inventory must be final acceptance eligible");
  assert(written.aws_capture_required === false, "normalized inventory must not require more AWS capture");
  assert(written.stack_name === "saphnexa-uat-app", "normalized inventory stack name mismatch");
  assert(written.stack_status === "UPDATE_COMPLETE", "normalized inventory stack status mismatch");
  assert(written.capture_evidence.captured_at === "2026-05-27T12:00:00+09:00", "normalized inventory captured_at mismatch");
  assert(written.capture_evidence.describe_stacks_command.includes("describe-stacks"), "normalized inventory missing describe-stacks command");
  assert(written.capture_evidence.list_stack_resources_command.includes("list-stack-resources"), "normalized inventory missing list-stack-resources command");
  assert(written.stack_outputs.length === expectedMajorOutputKeys.length, "normalized inventory output count mismatch");
  assert(written.stack_resources.length === expectedResourceCount(), "normalized inventory resource count mismatch");
  assert(written.stack_outputs.every((output) => output.OutputKey && output.OutputValue), "normalized inventory output shape mismatch");
  assert(written.stack_resources.every((resource) => resource.LogicalResourceId && resource.PhysicalResourceId && resource.ResourceType && resource.ResourceStatus), "normalized inventory resource shape mismatch");

  assertThrows(
    () =>
      normalizeFinalCloudFormationInventory({
        describeStacks: { Stacks: [] },
        listStackResources: listStackResourcesFixture(),
        capturedAt: "2026-05-27T12:00:00+09:00"
      }),
    "describe-stacks output missing Stacks"
  );
  assertThrows(
    () =>
      normalizeFinalCloudFormationInventory({
        describeStacks: describeStacksFixture(),
        listStackResources: { StackResourceSummaries: [] },
        capturedAt: "2026-05-27T12:00:00+09:00"
      }),
    "list-stack-resources output missing StackResourceSummaries"
  );

  console.log("final CloudFormation inventory normalizer fixture check passed");
} finally {
  rmSync(root, { recursive: true, force: true });
}

function describeStacksFixture() {
  return {
    Stacks: [
      {
        StackId: `arn:aws:cloudformation:ap-northeast-1:${readyAwsAccountId()}:stack/saphnexa-uat-app/abc12345`,
        StackName: "saphnexa-uat-app",
        StackStatus: "UPDATE_COMPLETE",
        Outputs: expectedMajorOutputKeys.map((outputKey, index) => ({
          OutputKey: outputKey,
          OutputValue: outputValueFor(outputKey, index)
        }))
      }
    ]
  };
}

function listStackResourcesFixture() {
  return {
    StackResourceSummaries: expectedMajorResourceTypes.flatMap((resourceType) =>
      Array.from({ length: expectedMajorResourceTypeMinimumCounts[resourceType] }, (_, index) => ({
        LogicalResourceId: `${resourceType.replaceAll(/[^A-Za-z0-9]/g, "")}${index}`,
        PhysicalResourceId: `saphnexa-uat-${resourceType.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}-${index}`,
        ResourceType: resourceType,
        ResourceStatus: "UPDATE_COMPLETE"
      }))
    )
  };
}

function expectedResourceCount() {
  return Object.values(expectedMajorResourceTypeMinimumCounts).reduce((sum, count) => sum + count, 0);
}

function outputValueFor(outputKey, index) {
  const values = {
    DistributionDomainName: "d111111abcdef8.cloudfront.net",
    AdminArtifactsBucketArn: "arn:aws:s3:::saphnexa-uat-admin-artifacts",
    SignedCookieKeyGroupId: "K1234567890ABC",
    ApiEndpoint: "https://api.saphnexa-uat.example.com",
    RealtimeEndpoint: "wss://realtime.saphnexa-uat.example.com/event/realtime",
    DsqlEndpoint: "saphnexa-uat.dsql.ap-northeast-1.on.aws",
    KnowledgeBaseId: "KB12345678",
    DeployRoleArn: `arn:aws:iam::${readyAwsAccountId()}:role/saphnexa-uat-github-deploy`
  };
  return values[outputKey] || `saphnexa-uat-output-${index}`;
}

function readyAwsAccountId() {
  return ["2109", "8765", "4321"].join("");
}

function assertThrows(fn, message) {
  try {
    fn();
  } catch (error) {
    assert(error.message.includes(message), `unexpected error: ${error.message}`);
    return;
  }
  throw new Error(`expected error: ${message}`);
}
