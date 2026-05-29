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


def _template():
    return yaml.load(Path("infra/cloudformation/diopside.yaml").read_text(encoding="utf-8"), Loader=CfnLoader)


def test_cloudfront_oac_and_outputs_are_defined():
    template = Path("infra/cloudformation/diopside.yaml").read_text(encoding="utf-8")
    for token in [
        "AWS::CloudFront::Distribution",
        "AWS::CloudFront::OriginAccessControl",
        "PathPattern: /api/*",
        "PathPattern: /data/latest-manifest.json",
        "PathPattern: /data/v/*",
        "PathPattern: /assets/*",
        "WebBucketPolicy",
        "PublicDataBucketPolicy",
        "CloudFrontDomainName",
        "ApiEndpoint",
        "MetadataQueueUrl",
        "StaticExportQueueUrl",
    ]:
        assert token in template


def test_worker_function_and_sqs_mappings_are_defined():
    template = Path("infra/cloudformation/diopside.yaml").read_text(encoding="utf-8")
    for token in [
        "WorkerFunction",
        "static_exporter.pipeline.lambda_handler",
        "MetadataQueueMapping",
        "ChatQueueMapping",
        "NormalizeQueueMapping",
        "AggregateQueueMapping",
        "StaticExportQueueMapping",
    ]:
        assert token in template


def test_cloudformation_template_parses_and_worker_can_consume_queues():
    template = _template()
    resources = template["Resources"]
    policy = resources["StaticExporterRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"][0]
    for action in ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:SendMessage"]:
        assert action in policy["Action"]
    env = resources["WorkerFunction"]["Properties"]["Environment"]["Variables"]
    for name in [
        "DIOPSIDE_METADATA_QUEUE_URL",
        "DIOPSIDE_CHAT_QUEUE_URL",
        "DIOPSIDE_NORMALIZE_QUEUE_URL",
        "DIOPSIDE_AGGREGATE_QUEUE_URL",
        "DIOPSIDE_STATIC_EXPORT_QUEUE_URL",
        "DIOPSIDE_YOUTUBE_API_KEY",
    ]:
        assert name in env
    assert "YouTubeApiKey" in template["Parameters"]
    assert template["Parameters"]["YouTubeApiKey"]["NoEcho"] is True
