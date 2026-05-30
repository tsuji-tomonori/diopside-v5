from pathlib import Path

from static_exporter import pipeline


BATCH_IDS = [f"BATCH-{index:03d}" for index in range(1, 21)]

EXPECTED_QUEUE_ENVS = {
    "metadata_sync": "DIOPSIDE_METADATA_QUEUE_URL",
    "live_status_scan": "DIOPSIDE_METADATA_QUEUE_URL",
    "chat_collect": "DIOPSIDE_CHAT_QUEUE_URL",
    "chat_normalize": "DIOPSIDE_NORMALIZE_QUEUE_URL",
    "rebuild_artifacts": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "archive_finalize": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "static_export": "DIOPSIDE_STATIC_EXPORT_QUEUE_URL",
    "retry_job": "DIOPSIDE_METADATA_QUEUE_URL",
    "cancel_job": "DIOPSIDE_METADATA_QUEUE_URL",
    "quota_rollup": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "cleanup": "DIOPSIDE_AGGREGATE_QUEUE_URL",
}


def test_worker_batch_audit_covers_all_v04_batch_ids_and_current_jobs():
    audit = Path("docs/design/worker-batch-coverage-audit.md").read_text(encoding="utf-8")

    for batch_id in BATCH_IDS:
        assert batch_id in audit
    for job_type in EXPECTED_QUEUE_ENVS:
        assert f"`{job_type}`" in audit

    assert "BATCH-006" in audit and "未対応" in audit
    assert "BATCH-017" in audit and "未対応" in audit
    assert "部分実装" in audit
    assert "差分あり" in audit


def test_pipeline_job_queue_mapping_covers_schedulable_and_retryable_jobs():
    assert pipeline.JOB_QUEUE_ENVS == EXPECTED_QUEUE_ENVS

    for job_type, queue_env in EXPECTED_QUEUE_ENVS.items():
        assert pipeline._queue_env_for_job_type(job_type) == queue_env


def test_pipeline_dispatcher_declares_current_handler_jobs():
    assert pipeline.PIPELINE_JOB_HANDLERS == {
        "metadata_sync": "metadata_sync",
        "live_status_scan": "live_status_scan",
        "chat_collect": "chat_collect",
        "chat_normalize": "chat_normalize",
        "rebuild_artifacts": "rebuild_artifacts",
        "archive_finalize": "archive_finalize",
        "retry_job": "retry_job",
        "cancel_job": "cancel_job",
        "quota_rollup": "quota_rollup",
        "cleanup": "cleanup",
    }

    assert "static_export" not in pipeline.PIPELINE_JOB_HANDLERS
    assert "static_export" in pipeline.JOB_QUEUE_ENVS
