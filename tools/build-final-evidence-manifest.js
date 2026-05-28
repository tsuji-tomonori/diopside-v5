import {
  buildFinalEvidenceManifestFromFile,
  finalEvidenceManifestInputPath,
  finalEvidenceManifestPath,
  finalManifestCloudFormationInventoryPath
} from "./final-evidence-manifest.js";

const options = parseArgs(process.argv.slice(2));
const outputPath = options.outputPath || finalEvidenceManifestPath;
const manifest = buildFinalEvidenceManifestFromFile({
  inputPath: options.inputPath || finalEvidenceManifestInputPath,
  cloudFormationInventoryPath: options.cloudFormationInventoryPath || finalManifestCloudFormationInventoryPath,
  outputPath
});

console.log(`final evidence manifest generated: ${outputPath}`);
console.log(`git_tag: ${manifest.git_tag}`);

function parseArgs(args) {
  const options = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    const value = args[index + 1];
    if (!arg.startsWith("--")) throw new Error(`unexpected argument: ${arg}`);
    if (!value || value.startsWith("--")) throw new Error(`missing value for ${arg}`);
    index += 1;
    if (arg === "--input") options.inputPath = value;
    else if (arg === "--cloudformation-inventory") options.cloudFormationInventoryPath = value;
    else if (arg === "--output") options.outputPath = value;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return options;
}
