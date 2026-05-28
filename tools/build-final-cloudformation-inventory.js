import {
  buildFinalCloudFormationInventoryFromFiles,
  defaultRegion,
  defaultStackName,
  finalCloudFormationInventoryPath,
  rawDescribeStacksPath,
  rawListStackResourcesPath
} from "./final-cloudformation-inventory.js";

const options = parseArgs(process.argv.slice(2));
const inventory = buildFinalCloudFormationInventoryFromFiles({
  describeStacksPath: options.describeStacksPath || rawDescribeStacksPath,
  listStackResourcesPath: options.listStackResourcesPath || rawListStackResourcesPath,
  outputPath: options.outputPath || finalCloudFormationInventoryPath,
  capturedAt: options.capturedAt || process.env.CFN_CAPTURED_AT || new Date().toISOString(),
  stackName: options.stackName || defaultStackName,
  region: options.region || defaultRegion
});

console.log(`final CloudFormation inventory generated: ${options.outputPath || finalCloudFormationInventoryPath}`);
console.log(`stack: ${inventory.stack_name} (${inventory.stack_status})`);

function parseArgs(args) {
  const options = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    const value = args[index + 1];
    if (!arg.startsWith("--")) throw new Error(`unexpected argument: ${arg}`);
    if (!value || value.startsWith("--")) throw new Error(`missing value for ${arg}`);
    index += 1;
    if (arg === "--describe-stacks") options.describeStacksPath = value;
    else if (arg === "--list-stack-resources") options.listStackResourcesPath = value;
    else if (arg === "--output") options.outputPath = value;
    else if (arg === "--captured-at") options.capturedAt = value;
    else if (arg === "--stack-name") options.stackName = value;
    else if (arg === "--region") options.region = value;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return options;
}
