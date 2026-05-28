import { buildFinalAcceptanceChecklistFromFile, finalChecklistPath, finalChecklistSignoffInputPath } from "./final-acceptance-checklist.js";

const options = parseArgs(process.argv.slice(2));
const outputPath = options.outputPath || finalChecklistPath;
const rows = buildFinalAcceptanceChecklistFromFile({
  inputPath: options.inputPath || finalChecklistSignoffInputPath,
  outputPath
});

console.log(`final acceptance checklist generated: ${outputPath}`);
console.log(`rows: ${rows.length}`);

function parseArgs(args) {
  const options = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    const value = args[index + 1];
    if (!arg.startsWith("--")) throw new Error(`unexpected argument: ${arg}`);
    if (!value || value.startsWith("--")) throw new Error(`missing value for ${arg}`);
    index += 1;
    if (arg === "--input") options.inputPath = value;
    else if (arg === "--output") options.outputPath = value;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return options;
}
