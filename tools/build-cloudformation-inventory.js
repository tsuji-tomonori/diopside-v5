import { buildCloudFormationInventoryDraft, cloudFormationInventoryPath } from "./cloudformation-inventory.js";

buildCloudFormationInventoryDraft();
console.log(`CloudFormation inventory draft generated: ${cloudFormationInventoryPath}`);
