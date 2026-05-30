from pathlib import Path

import yaml


def _workflow(name: str) -> dict:
    return yaml.load(Path(".github/workflows", name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_manual_job_dispatch_workflow_uses_v04_job_message_contract():
    workflow = _workflow("manual-job-dispatch.yml")
    dispatch = workflow["on"]["workflow_dispatch"]
    inputs = dispatch["inputs"]
    job = workflow["jobs"]["dispatch"]
    script = job["steps"][1]["run"]

    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["steps"][0]["uses"] == "aws-actions/configure-aws-credentials@v4"
    assert "DIOPSIDE_GITHUB_ACTIONS_ROLE_ARN" in str(job["steps"][0]["with"])
    assert "aws_access_key_id" not in Path(".github/workflows/manual-job-dispatch.yml").read_text(encoding="utf-8")

    assert inputs["job_type"]["type"] == "choice"
    assert set(inputs["job_type"]["options"]) == {
        "metadata_sync",
        "live_status_scan",
        "chat_collect",
        "chat_normalize",
        "rebuild_artifacts",
        "file_output",
        "archive_finalize",
        "notification_plan",
        "static_export",
        "retry_job",
        "cancel_job",
        "quota_rollup",
        "cleanup",
    }
    assert inputs["idempotency_key"]["required"] == "true"
    assert inputs["payload_json"]["default"] == "{}"
    assert "jq -e ." in script
    for field in ["job_id", "job_type", "idempotency_key", "requested_by", "attempt", "trace_id", "payload"]:
        assert field in script
    assert "--arg requested_by \"github_actions\"" in script
    assert "aws sqs send-message" in script
    assert "--message-body \"${MESSAGE_BODY}\"" in script
    assert "input:" not in script


def test_manual_job_dispatch_routes_job_types_to_expected_queue_secrets():
    script = _workflow("manual-job-dispatch.yml")["jobs"]["dispatch"]["steps"][1]["run"]
    env = _workflow("manual-job-dispatch.yml")["jobs"]["dispatch"]["steps"][1]["env"]

    assert env["METADATA_QUEUE_URL"] == "${{ secrets.DIOPSIDE_METADATA_QUEUE_URL }}"
    assert env["CHAT_QUEUE_URL"] == "${{ secrets.DIOPSIDE_CHAT_QUEUE_URL }}"
    assert env["NORMALIZE_QUEUE_URL"] == "${{ secrets.DIOPSIDE_NORMALIZE_QUEUE_URL }}"
    assert env["AGGREGATE_QUEUE_URL"] == "${{ secrets.DIOPSIDE_AGGREGATE_QUEUE_URL }}"
    assert env["STATIC_EXPORT_QUEUE_URL"] == "${{ secrets.DIOPSIDE_STATIC_EXPORT_QUEUE_URL }}"
    assert "metadata_sync|live_status_scan|retry_job|cancel_job)" in script
    assert "chat_collect)" in script
    assert "chat_normalize)" in script
    assert "rebuild_artifacts|file_output|archive_finalize|notification_plan|quota_rollup|cleanup)" in script
    assert "static_export)" in script
