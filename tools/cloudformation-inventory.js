import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { synthLocalInventory } from "../infra/bin/app.js";
import { currentJstTimestamp } from "./lib.js";

export const cloudFormationInventoryPath = "dist/acceptance/cloudformation_inventory.draft.json";

export const expectedMajorResourceTypes = [
  "AWS::CloudFront::Distribution",
  "AWS::CloudFront::Function",
  "AWS::CloudFront::OriginAccessControl",
  "AWS::WAFv2::WebACL",
  "AWS::S3::Bucket",
  "AWS::S3::BucketPolicy",
  "AWS::KMS::Key",
  "AWS::Cognito::UserPool",
  "AWS::Cognito::UserPoolClient",
  "AWS::ApiGatewayV2::Api",
  "AWS::Lambda::Function",
  "AWS::AppSync::Api",
  "AWS::SQS::Queue",
  "AWS::Logs::LogGroup",
  "AWS::CloudWatch::Alarm",
  "AWS::Events::EventBus"
];

export const expectedMajorResourceTypeMinimumCounts = {
  "AWS::CloudFront::Distribution": 1,
  "AWS::CloudFront::Function": 2,
  "AWS::CloudFront::OriginAccessControl": 2,
  "AWS::WAFv2::WebACL": 1,
  "AWS::S3::Bucket": 6,
  "AWS::S3::BucketPolicy": 2,
  "AWS::KMS::Key": 1,
  "AWS::Cognito::UserPool": 1,
  "AWS::Cognito::UserPoolClient": 1,
  "AWS::ApiGatewayV2::Api": 2,
  "AWS::Lambda::Function": 11,
  "AWS::AppSync::Api": 1,
  "AWS::SQS::Queue": 8,
  "AWS::Logs::LogGroup": 1,
  "AWS::CloudWatch::Alarm": 14,
  "AWS::Events::EventBus": 1
};

export const expectedMajorOutputKeys = [
  "DistributionDomainName",
  "AdminArtifactsBucketArn",
  "SignedCookieKeyGroupId",
  "ApiEndpoint",
  "RealtimeEndpoint",
  "DsqlEndpoint",
  "KnowledgeBaseId",
  "DeployRoleArn"
];

export function buildCloudFormationInventoryDraft(outputPath = cloudFormationInventoryPath) {
  const localInventory = synthLocalInventory("uat");
  const constructs = Object.entries(localInventory.intent_catalog).map(([name, catalog]) => ({
    name,
    resources: catalog.resources,
    outputs: catalog.outputs,
    resource_count: catalog.resources.length,
    output_count: catalog.outputs.length
  }));

  const body = {
    schema_version: "saphnexa-cloudformation-inventory.v1",
    system: "Saphnexa",
    environment: "uat",
    aws_region: localInventory.region,
    stack_name: "saphnexa-uat-app",
    source: "local-cdk-intent",
    generated_by: "tools/build-cloudformation-inventory.js",
    generated_at: currentJstTimestamp(),
    final_acceptance_eligible: false,
    aws_capture_required: true,
    local_cdk_inventory: {
      construct_count: localInventory.construct_count,
      constructs,
      expected_resource_symbols: constructs.flatMap((item) => item.resources),
      expected_output_symbols: constructs.flatMap((item) => item.outputs),
      checksum: `sha256:${sha256(JSON.stringify(localInventory))}`
    },
    expected_major_resource_types: expectedMajorResourceTypes,
    expected_major_resource_type_minimum_counts: expectedMajorResourceTypeMinimumCounts,
    expected_major_output_keys: expectedMajorOutputKeys,
    final_capture_instructions: {
      describe_stacks_command: "aws cloudformation describe-stacks --stack-name saphnexa-uat-app --region ap-northeast-1 --output json",
      list_stack_resources_command: "aws cloudformation list-stack-resources --stack-name saphnexa-uat-app --region ap-northeast-1 --output json",
      normalized_final_inventory_path: "docs/acceptance/cloudformation/cloudformation_inventory.uat.json",
      required_for_acceptance: [
        "StackId",
        "StackStatus",
        "Outputs",
        "major output keys",
        "StackResourceSummaries",
        "resource type counts",
        "major resource match rate 100%"
      ]
    },
    note: "Draft inventory generated from local CDK intent only. It is not CloudFormation describe-stacks evidence and must not be used as final AC-081 proof."
  };

  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(body, null, 2)}\n`);
  return body;
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}
