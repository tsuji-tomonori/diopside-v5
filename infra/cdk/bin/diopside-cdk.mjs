#!/usr/bin/env node
import path from "node:path";
import { fileURLToPath } from "node:url";

import * as cdk from "aws-cdk-lib";
import * as cfnInclude from "aws-cdk-lib/cloudformation-include";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "../../..");
const outdir = process.env.CDK_OUTDIR || path.join(repoRoot, "build/cdk.out");

export class DiopsideStack extends cdk.Stack {
  constructor(scope, id, props = {}) {
    super(scope, id, props);

    new cfnInclude.CfnInclude(this, "CloudFormationParityTemplate", {
      templateFile: path.join(repoRoot, "infra/cloudformation/diopside.yaml"),
    });
  }
}

const app = new cdk.App({ outdir });
new DiopsideStack(app, "DiopsideStack");
app.synth();
