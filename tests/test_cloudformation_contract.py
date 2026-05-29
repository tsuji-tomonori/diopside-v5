import json
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


def _schedule_input(schedule):
    return json.loads(schedule["Properties"]["Target"]["Input"]["Fn::Sub"])


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


def test_cloudfront_behaviors_route_to_expected_origins_and_cache_policies():
    resources = _template()["Resources"]
    distribution = resources["CloudFrontDistribution"]["Properties"]["DistributionConfig"]
    origins = {origin["Id"]: origin for origin in distribution["Origins"]}
    behaviors = distribution["CacheBehaviors"]
    assert [behavior["PathPattern"] for behavior in behaviors] == [
        "/api/*",
        "/data/latest-manifest.json",
        "/data/v/*",
        "/assets/*",
    ]

    by_path = {behavior["PathPattern"]: behavior for behavior in behaviors}
    assert by_path["/api/*"]["TargetOriginId"] == "api-function-url"
    assert by_path["/api/*"]["CachePolicyId"] == {"Ref": "ApiNoStoreCachePolicy"}
    assert by_path["/api/*"]["AllowedMethods"] == ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    assert by_path["/api/*"]["CachedMethods"] == ["GET", "HEAD", "OPTIONS"]
    assert by_path["/api/*"]["OriginRequestPolicyId"] == "216adef6-5c7f-47e4-b989-5492eafa07d3"
    assert origins["api-function-url"]["OriginAccessControlId"] == {"Ref": "ApiFunctionUrlOac"}
    assert origins["api-function-url"]["CustomOriginConfig"]["OriginProtocolPolicy"] == "https-only"

    assert by_path["/data/latest-manifest.json"]["TargetOriginId"] == "public-data-s3"
    assert by_path["/data/latest-manifest.json"]["CachePolicyId"] == {"Ref": "ManifestShortCachePolicy"}
    assert by_path["/data/v/*"]["TargetOriginId"] == "public-data-s3"
    assert by_path["/data/v/*"]["CachePolicyId"] == {"Ref": "ImmutableCachePolicy"}
    assert by_path["/assets/*"]["TargetOriginId"] == "web-s3"
    assert by_path["/assets/*"]["CachePolicyId"] == {"Ref": "ImmutableCachePolicy"}

    default = distribution["DefaultCacheBehavior"]
    assert default["TargetOriginId"] == "web-s3"
    assert default["CachePolicyId"] == {"Ref": "ImmutableCachePolicy"}
    assert default["FunctionAssociations"][0]["EventType"] == "viewer-request"


def test_lambda_function_url_is_cloudfront_origin_only():
    template = _template()
    resources = template["Resources"]
    function_url = resources["ApiFunctionUrl"]["Properties"]
    permission = resources["ApiFunctionUrlPermission"]["Properties"]
    lambda_oac = resources["ApiFunctionUrlOac"]["Properties"]["OriginAccessControlConfig"]
    outputs = template["Outputs"]

    assert function_url["AuthType"] == "AWS_IAM"
    assert lambda_oac["OriginAccessControlOriginType"] == "lambda"
    assert lambda_oac["SigningBehavior"] == "always"
    assert lambda_oac["SigningProtocol"] == "sigv4"
    assert permission["Action"] == "lambda:InvokeFunctionUrl"
    assert permission["Principal"] == "cloudfront.amazonaws.com"
    assert permission["FunctionUrlAuthType"] == "AWS_IAM"
    assert permission["InvokedViaFunctionUrl"] is True
    assert permission["SourceArn"] == {"Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}"}
    assert "ApiEndpoint" in outputs
    assert "ApiFunctionUrl" not in outputs
    assert outputs["ApiFunctionUrlOrigin"]["Description"].startswith("Internal Lambda Function URL origin")


def test_s3_origins_are_private_and_oac_only():
    resources = _template()["Resources"]
    distribution = resources["CloudFrontDistribution"]["Properties"]["DistributionConfig"]
    origins = {origin["Id"]: origin for origin in distribution["Origins"]}
    s3_oac = resources["CloudFrontOac"]["Properties"]["OriginAccessControlConfig"]

    assert s3_oac["OriginAccessControlOriginType"] == "s3"
    assert s3_oac["SigningBehavior"] == "always"
    assert s3_oac["SigningProtocol"] == "sigv4"
    for origin_id, bucket_name in [("web-s3", "WebBucket"), ("public-data-s3", "PublicDataBucket")]:
        origin = origins[origin_id]
        assert origin["DomainName"] == {"Fn::GetAtt": [bucket_name, "RegionalDomainName"]}
        assert origin["OriginAccessControlId"] == {"Ref": "CloudFrontOac"}
        assert origin["S3OriginConfig"] == {"OriginAccessIdentity": ""}
        assert "Website" not in str(origin)


def test_web_and_public_data_bucket_policies_allow_only_cloudfront_oac_reads():
    resources = _template()["Resources"]
    expected_source_arn = {"Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}"}
    for policy_name, bucket_name, sid, resource_sub in [
        ("WebBucketPolicy", "WebBucket", "AllowCloudFrontReadWeb", "${WebBucket.Arn}/*"),
        ("PublicDataBucketPolicy", "PublicDataBucket", "AllowCloudFrontReadPublicData", "${PublicDataBucket.Arn}/*"),
    ]:
        policy = resources[policy_name]["Properties"]
        assert policy["Bucket"] == {"Ref": bucket_name}
        statements = policy["PolicyDocument"]["Statement"]
        assert len(statements) == 1
        statement = statements[0]
        assert statement["Sid"] == sid
        assert statement["Effect"] == "Allow"
        assert statement["Principal"] == {"Service": "cloudfront.amazonaws.com"}
        assert statement["Action"] == "s3:GetObject"
        assert statement["Resource"] == {"Fn::Sub": resource_sub}
        assert statement["Condition"] == {"StringEquals": {"AWS:SourceArn": expected_source_arn}}
        assert statement["Principal"] != "*"
        assert not (isinstance(statement["Principal"], dict) and statement["Principal"].get("AWS") == "*")
        assert statement["Action"] != "s3:*"
        assert statement["Action"] != ["s3:*"]


def test_web_and_public_data_buckets_block_public_access():
    resources = _template()["Resources"]
    for bucket_name in ["WebBucket", "PublicDataBucket"]:
        block = resources[bucket_name]["Properties"]["PublicAccessBlockConfiguration"]
        assert block == {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        }


def test_raw_and_processed_buckets_define_lifecycle_retention_contracts():
    resources = _template()["Resources"]
    raw_rules = {
        rule["Id"]: rule for rule in resources["RawBucket"]["Properties"]["LifecycleConfiguration"]["Rules"]
    }
    processed_rules = {
        rule["Id"]: rule for rule in resources["ProcessedBucket"]["Properties"]["LifecycleConfiguration"]["Rules"]
    }

    assert raw_rules["raw-metadata-retention"] == {
        "Id": "raw-metadata-retention",
        "Status": "Enabled",
        "Prefix": "raw/youtube/metadata/",
        "Transitions": [{"StorageClass": "STANDARD_IA", "TransitionInDays": 90}],
        "ExpirationInDays": 365,
    }
    assert raw_rules["raw-chat-retention"] == {
        "Id": "raw-chat-retention",
        "Status": "Enabled",
        "Prefix": "raw/youtube/chat/",
        "Transitions": [{"StorageClass": "STANDARD_IA", "TransitionInDays": 30}],
        "ExpirationInDays": 180,
    }
    assert raw_rules["failed-debug-expire"] == {
        "Id": "failed-debug-expire",
        "Status": "Enabled",
        "Prefix": "failed/",
        "ExpirationInDays": 90,
    }
    assert processed_rules["processed-chat-normalized-retention"] == {
        "Id": "processed-chat-normalized-retention",
        "Status": "Enabled",
        "Prefix": "processed/chat-normalized/",
        "Transitions": [{"StorageClass": "STANDARD_IA", "TransitionInDays": 90}],
        "ExpirationInDays": 730,
    }
    assert processed_rules["processed-chat-aggregate-retention"] == {
        "Id": "processed-chat-aggregate-retention",
        "Status": "Enabled",
        "Prefix": "processed/chat-aggregate/",
        "Transitions": [{"StorageClass": "STANDARD_IA", "TransitionInDays": 90}],
        "ExpirationInDays": 730,
    }


def test_cloudfront_cache_policy_ttls_match_behavior_contract():
    resources = _template()["Resources"]
    api = resources["ApiNoStoreCachePolicy"]["Properties"]["CachePolicyConfig"]
    manifest = resources["ManifestShortCachePolicy"]["Properties"]["CachePolicyConfig"]
    immutable = resources["ImmutableCachePolicy"]["Properties"]["CachePolicyConfig"]

    assert {api["MinTTL"], api["DefaultTTL"], api["MaxTTL"]} == {0}
    assert api["ParametersInCacheKeyAndForwardedToOrigin"]["QueryStringsConfig"]["QueryStringBehavior"] == "all"
    assert api["ParametersInCacheKeyAndForwardedToOrigin"]["CookiesConfig"]["CookieBehavior"] == "all"
    assert api["ParametersInCacheKeyAndForwardedToOrigin"]["HeadersConfig"]["HeaderBehavior"] == "whitelist"
    assert set(api["ParametersInCacheKeyAndForwardedToOrigin"]["HeadersConfig"]["Headers"]) >= {
        "Authorization",
        "X-CSRF-Token",
        "X-Idempotency-Key",
    }

    assert manifest["MinTTL"] == 0
    assert manifest["DefaultTTL"] <= 60
    assert manifest["MaxTTL"] <= 300
    assert immutable["MinTTL"] >= 86400
    assert immutable["DefaultTTL"] == 31536000
    assert immutable["MaxTTL"] == 31536000


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


def test_scheduler_role_can_only_send_to_maintenance_queues():
    resources = _template()["Resources"]
    role = resources["SchedulerRole"]["Properties"]
    assume = role["AssumeRolePolicyDocument"]["Statement"][0]
    statement = role["Policies"][0]["PolicyDocument"]["Statement"][0]

    assert assume["Principal"] == {"Service": "scheduler.amazonaws.com"}
    assert assume["Action"] == "sts:AssumeRole"
    assert statement["Effect"] == "Allow"
    assert statement["Action"] == "sqs:SendMessage"
    assert statement["Resource"] == [
        {"Fn::GetAtt": ["MetadataQueue", "Arn"]},
        {"Fn::GetAtt": ["AggregateQueue", "Arn"]},
    ]


def test_eventbridge_scheduler_dispatches_low_frequency_maintenance_jobs():
    resources = _template()["Resources"]
    expected = {
        "MetadataSyncSchedule": ("rate(12 hours)", "MetadataQueue", "metadata_sync"),
        "LiveStatusScanSchedule": ("rate(30 minutes)", "MetadataQueue", "live_status_scan"),
        "QuotaRollupSchedule": ("rate(1 day)", "AggregateQueue", "quota_rollup"),
        "CleanupSchedule": ("rate(7 days)", "AggregateQueue", "cleanup"),
    }

    for schedule_name, (expression, queue_name, job_type) in expected.items():
        schedule = resources[schedule_name]
        props = schedule["Properties"]
        target = props["Target"]
        payload = _schedule_input(schedule)

        assert schedule["Type"] == "AWS::Scheduler::Schedule"
        assert props["State"] == "ENABLED"
        assert props["ScheduleExpression"] == expression
        assert props["FlexibleTimeWindow"] == {"Mode": "OFF"}
        assert target["Arn"] == {"Fn::GetAtt": [queue_name, "Arn"]}
        assert target["RoleArn"] == {"Fn::GetAtt": ["SchedulerRole", "Arn"]}
        assert payload["job_type"] == job_type
        assert payload["job_id"].startswith(f"scheduler-{job_type.replace('_', '-')}-")
        assert "<aws.scheduler.execution-id>" in payload["job_id"]
        assert payload["input"]["requested_by"] == "scheduler"
        assert "<aws.scheduler.scheduled-time>" in payload["input"]["idempotency_key"]

    metadata_payload = _schedule_input(resources["MetadataSyncSchedule"])
    cleanup_payload = _schedule_input(resources["CleanupSchedule"])
    assert metadata_payload["input"]["max_results"] == 25
    assert cleanup_payload["input"]["dry_run"] is True


def test_cloudwatch_log_groups_and_api_5xx_metric_filter_are_defined():
    resources = _template()["Resources"]
    for log_group_name, function_name in [
        ("ApiFunctionLogGroup", "ApiFunction"),
        ("WorkerFunctionLogGroup", "WorkerFunction"),
        ("StaticExporterFunctionLogGroup", "StaticExporterFunction"),
    ]:
        log_group = resources[log_group_name]
        assert log_group["Type"] == "AWS::Logs::LogGroup"
        assert log_group["Properties"]["LogGroupName"] == {"Fn::Sub": f"/aws/lambda/${{{function_name}}}"}
        assert log_group["Properties"]["RetentionInDays"] == 30

    metric_filter = resources["Api5xxMetricFilter"]
    props = metric_filter["Properties"]
    assert metric_filter["Type"] == "AWS::Logs::MetricFilter"
    assert props["LogGroupName"] == {"Ref": "ApiFunctionLogGroup"}
    assert '$.component = "api"' in props["FilterPattern"]
    assert "$.status >= 500" in props["FilterPattern"]
    transformation = props["MetricTransformations"][0]
    assert transformation["MetricNamespace"] == {"Fn::Sub": "diopside/${EnvName}"}
    assert transformation["MetricName"] == "Api5xxCount"
    assert transformation["MetricValue"] == "1"


def test_cloudwatch_alarms_cover_dlq_lambda_api_and_static_export_failures():
    resources = _template()["Resources"]
    expected_dlq_alarms = {
        "MetadataDlqDepthAlarm": "MetadataDlq",
        "ChatDlqDepthAlarm": "ChatDlq",
        "NormalizeDlqDepthAlarm": "NormalizeDlq",
        "AggregateDlqDepthAlarm": "AggregateDlq",
        "StaticExportDlqDepthAlarm": "StaticExportDlq",
    }
    for alarm_name, queue_name in expected_dlq_alarms.items():
        alarm = resources[alarm_name]
        props = alarm["Properties"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"
        assert props["Namespace"] == "AWS/SQS"
        assert props["MetricName"] == "ApproximateNumberOfMessagesVisible"
        assert props["Dimensions"] == [{"Name": "QueueName", "Value": {"Fn::GetAtt": [queue_name, "QueueName"]}}]
        assert props["Statistic"] == "Sum"
        assert props["Period"] == 300
        assert props["EvaluationPeriods"] == 1
        assert props["Threshold"] == 1
        assert props["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
        assert props["TreatMissingData"] == "notBreaching"

    expected_lambda_alarms = {
        "ApiFunctionErrorsAlarm": "ApiFunction",
        "WorkerFunctionErrorsAlarm": "WorkerFunction",
        "StaticExportFailureAlarm": "StaticExporterFunction",
    }
    for alarm_name, function_name in expected_lambda_alarms.items():
        alarm = resources[alarm_name]
        props = alarm["Properties"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"
        assert props["Namespace"] == "AWS/Lambda"
        assert props["MetricName"] == "Errors"
        assert props["Dimensions"] == [{"Name": "FunctionName", "Value": {"Ref": function_name}}]
        assert props["Statistic"] == "Sum"
        assert props["Threshold"] == 1
        assert props["TreatMissingData"] == "notBreaching"

    api_5xx = resources["Api5xxAlarm"]["Properties"]
    assert api_5xx["Namespace"] == {"Fn::Sub": "diopside/${EnvName}"}
    assert api_5xx["MetricName"] == "Api5xxCount"
    assert api_5xx["Threshold"] == 1
    assert api_5xx["ComparisonOperator"] == "GreaterThanOrEqualToThreshold"
