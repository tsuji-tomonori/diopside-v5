# Diopside CDK

This CDK app bootstraps the v0.4 IaC migration by synthesizing the current
CloudFormation template through `CfnInclude`.

Run:

```bash
npm run cdk:synth
```

The synthesized template is written to `build/cdk.out/DiopsideStack.template.json`.
The current scope intentionally preserves logical IDs and resource types from
`infra/cloudformation/diopside.yaml`; splitting this into L2 constructs is a
follow-up migration step.
