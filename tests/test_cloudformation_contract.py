from pathlib import Path


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
