import json
import os
import subprocess
from pathlib import Path

import yaml


class CfnLoader(yaml.SafeLoader):
    pass


def _unknown_constructor(loader, tag_suffix, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


CfnLoader.add_multi_constructor("!", _unknown_constructor)


def _cloudformation_template():
    return yaml.load(Path("infra/cloudformation/diopside.yaml").read_text(encoding="utf-8"), Loader=CfnLoader)


def _synth_cdk_template(tmp_path):
    outdir = tmp_path / "cdk.out"
    env = os.environ.copy()
    env["CDK_OUTDIR"] = str(outdir)
    subprocess.run(["npm", "run", "cdk:synth"], check=True, env=env)
    return json.loads((outdir / "DiopsideStack.template.json").read_text(encoding="utf-8"))


def _resource_type_map(template):
    return {
        logical_id: resource["Type"]
        for logical_id, resource in template["Resources"].items()
    }


def test_cdk_synth_preserves_cloudformation_resource_logical_ids_and_types(tmp_path):
    source = _cloudformation_template()
    synthesized = _synth_cdk_template(tmp_path)

    assert _resource_type_map(synthesized) == _resource_type_map(source)


def test_cdk_synth_contains_v04_serverless_resource_families(tmp_path):
    synthesized = _synth_cdk_template(tmp_path)
    resource_types = set(_resource_type_map(synthesized).values())

    for resource_type in [
        "AWS::CloudFront::Distribution",
        "AWS::S3::Bucket",
        "AWS::DynamoDB::Table",
        "AWS::SQS::Queue",
        "AWS::Scheduler::Schedule",
        "AWS::Lambda::Function",
        "AWS::IAM::Role",
        "AWS::CloudWatch::Alarm",
    ]:
        assert resource_type in resource_types


def test_package_exposes_cdk_synth_script():
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["cdk:synth"] == "node infra/cdk/bin/diopside-cdk.mjs"
    assert "aws-cdk-lib" in package["devDependencies"]
    assert "constructs" in package["devDependencies"]
