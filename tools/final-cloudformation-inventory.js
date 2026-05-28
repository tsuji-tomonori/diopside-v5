import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { readJson } from "./lib.js";

export const finalCloudFormationInventoryPath = "docs/acceptance/cloudformation/cloudformation_inventory.uat.json";
export const rawDescribeStacksPath = "docs/acceptance/cloudformation/raw/describe-stacks.uat.json";
export const rawListStackResourcesPath = "docs/acceptance/cloudformation/raw/list-stack-resources.uat.json";
export const defaultStackName = "saphnexa-uat-app";
export const defaultRegion = "ap-northeast-1";

export function buildFinalCloudFormationInventoryFromFiles(options = {}) {
  const describeStacksPath = options.describeStacksPath || rawDescribeStacksPath;
  const listStackResourcesPath = options.listStackResourcesPath || rawListStackResourcesPath;
  const outputPath = options.outputPath || finalCloudFormationInventoryPath;
  const capturedAt = options.capturedAt || new Date().toISOString();
  const generatedAt = options.generatedAt || capturedAt;
  const stackName = options.stackName || defaultStackName;
  const region = options.region || defaultRegion;
  const inventory = normalizeFinalCloudFormationInventory({
    describeStacks: readJson(describeStacksPath),
    listStackResources: readJson(listStackResourcesPath),
    capturedAt,
    generatedAt,
    stackName,
    region,
    describeStacksCommand: options.describeStacksCommand || describeStacksCommand(stackName, region),
    listStackResourcesCommand: options.listStackResourcesCommand || listStackResourcesCommand(stackName, region)
  });

  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(inventory, null, 2)}\n`);
  return inventory;
}

export function normalizeFinalCloudFormationInventory(options) {
  const stackName = options.stackName || defaultStackName;
  const region = options.region || defaultRegion;
  const stack = selectStack(options.describeStacks, stackName);
  const resources = stackResources(options.listStackResources);
  const outputs = Array.isArray(stack.Outputs) ? stack.Outputs : [];

  assert(stack.StackName === stackName, `describe-stacks output missing stack ${stackName}`);
  assert(typeof stack.StackId === "string" && stack.StackId.length > 0, "describe-stacks output missing StackId");
  assert(typeof stack.StackStatus === "string" && stack.StackStatus.length > 0, "describe-stacks output missing StackStatus");
  assert(resources.length > 0, "list-stack-resources output missing StackResourceSummaries");

  return {
    schema_version: "saphnexa-cloudformation-inventory.v1",
    system: "Saphnexa",
    environment: "uat",
    aws_region: region,
    stack_name: stack.StackName,
    stack_id: stack.StackId,
    stack_status: stack.StackStatus,
    source: "aws-cloudformation-inventory",
    generated_by: "tools/build-final-cloudformation-inventory.js",
    generated_at: options.generatedAt || options.capturedAt,
    final_acceptance_eligible: true,
    aws_capture_required: false,
    capture_evidence: {
      captured_at: options.capturedAt,
      describe_stacks_command: options.describeStacksCommand || describeStacksCommand(stackName, region),
      list_stack_resources_command: options.listStackResourcesCommand || listStackResourcesCommand(stackName, region)
    },
    stack_outputs: outputs.map((output) => ({
      OutputKey: output.OutputKey,
      OutputValue: output.OutputValue
    })),
    stack_resources: resources.map((resource) => ({
      LogicalResourceId: resource.LogicalResourceId,
      PhysicalResourceId: resource.PhysicalResourceId,
      ResourceType: resource.ResourceType,
      ResourceStatus: resource.ResourceStatus
    }))
  };
}

export function describeStacksCommand(stackName = defaultStackName, region = defaultRegion) {
  return `aws cloudformation describe-stacks --stack-name ${stackName} --region ${region} --output json`;
}

export function listStackResourcesCommand(stackName = defaultStackName, region = defaultRegion) {
  return `aws cloudformation list-stack-resources --stack-name ${stackName} --region ${region} --output json`;
}

function selectStack(describeStacks, stackName) {
  const stacks = describeStacks?.Stacks;
  assert(Array.isArray(stacks) && stacks.length > 0, "describe-stacks output missing Stacks");
  const exact = stacks.find((stack) => stack.StackName === stackName);
  const stack = exact || (stacks.length === 1 ? stacks[0] : null);
  assert(Boolean(stack), `describe-stacks output missing stack ${stackName}`);
  return stack;
}

function stackResources(listStackResources) {
  const resources = listStackResources?.StackResourceSummaries;
  assert(Array.isArray(resources), "list-stack-resources output missing StackResourceSummaries");
  return resources;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
