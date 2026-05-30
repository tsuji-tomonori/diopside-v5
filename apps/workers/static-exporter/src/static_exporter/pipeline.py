from __future__ import annotations

import json
import os
import pathlib
import hashlib
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from diopside_core import (
    DynamoRepository,
    MemoryRepository,
    YouTubeClient,
    build_job_message,
    build_timestamp_candidates,
    extract_initial_data_from_watch_html,
    extract_replay_actions_from_initial_data,
    extract_replay_continuations_from_initial_data,
    fetch_public_replay_actions,
    fetch_public_replay_continuation,
    generate_chapters_suggestion_markdown,
    normalize_live_chat_items,
    normalize_channel_resource,
    normalize_replay_actions,
    normalize_video_resource,
    now_iso,
    summarize_chat_messages,
)

PIPELINE_JOB_HANDLERS = {
    "metadata_sync": "metadata_sync",
    "live_status_scan": "live_status_scan",
    "chat_collect": "chat_collect",
    "chat_normalize": "chat_normalize",
    "rebuild_artifacts": "rebuild_artifacts",
    "file_output": "file_output",
    "archive_finalize": "archive_finalize",
    "notification_plan": "notification_plan",
    "retry_job": "retry_job",
    "cancel_job": "cancel_job",
    "quota_rollup": "quota_rollup",
    "cleanup": "cleanup",
}

JOB_QUEUE_ENVS = {
    "metadata_sync": "DIOPSIDE_METADATA_QUEUE_URL",
    "live_status_scan": "DIOPSIDE_METADATA_QUEUE_URL",
    "chat_collect": "DIOPSIDE_CHAT_QUEUE_URL",
    "chat_normalize": "DIOPSIDE_NORMALIZE_QUEUE_URL",
    "rebuild_artifacts": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "file_output": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "archive_finalize": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "notification_plan": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "static_export": "DIOPSIDE_STATIC_EXPORT_QUEUE_URL",
    "retry_job": "DIOPSIDE_METADATA_QUEUE_URL",
    "cancel_job": "DIOPSIDE_METADATA_QUEUE_URL",
    "quota_rollup": "DIOPSIDE_AGGREGATE_QUEUE_URL",
    "cleanup": "DIOPSIDE_AGGREGATE_QUEUE_URL",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    repo = _repository()
    records = event.get("Records")
    if records:
        results = []
        for record in records:
            body = json.loads(record.get("body", "{}"))
            results.append(dispatch_job(repo, body))
        return {"status": "succeeded", "items": results}
    return dispatch_job(repo, event)


def dispatch_job(repo: Any, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    job_type = payload.get("job_type")
    job_id = payload.get("job_id", "manual")
    message_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload.get("input", payload)
    trace_id = payload.get("trace_id") or message_payload.get("trace_id") or f"trc_{uuid.uuid4().hex}"
    params = {**message_payload, "job_id": job_id}
    repo.append_job_event(job_id, "started", {"job_type": job_type})
    try:
        if job_type == "metadata_sync":
            result = metadata_sync(repo, params)
        elif job_type == "live_status_scan":
            result = live_status_scan(repo, params)
        elif job_type == "chat_collect":
            result = chat_collect(repo, params)
        elif job_type == "chat_normalize":
            result = chat_normalize(repo, params)
        elif job_type == "rebuild_artifacts":
            result = rebuild_artifacts(repo, params)
        elif job_type == "file_output":
            result = file_output(repo, params)
        elif job_type == "archive_finalize":
            result = archive_finalize(repo, params)
        elif job_type == "notification_plan":
            result = notification_plan(repo, params)
        elif job_type == "retry_job":
            result = retry_job(repo, params)
        elif job_type == "cancel_job":
            result = cancel_job(repo, params)
        elif job_type == "quota_rollup":
            result = quota_rollup(repo, params)
        elif job_type == "cleanup":
            result = cleanup(repo, params)
        else:
            raise ValueError(f"unsupported job_type: {job_type}")
        repo.append_job_event(job_id, "completed", result)
        response = {"job_id": job_id, "job_type": job_type, "status": "succeeded", **result}
        _log_worker_job(started, trace_id, job_id, job_type, params, result=response)
        return response
    except Exception as exc:
        debug_key = f"failed/jobs/job_id={job_id}/{now_iso()}.json"
        debug_uri = _write_blob(debug_key, json.dumps({"type": type(exc).__name__, "message": str(exc), "payload": payload}, ensure_ascii=False, indent=2).encode("utf-8"), "application/json")
        repo.append_job_event(job_id, "failed", {"type": type(exc).__name__, "message": str(exc), "debug_uri": debug_uri})
        _log_worker_job(
            started,
            trace_id,
            job_id,
            job_type,
            params,
            error={"type": type(exc).__name__, "message": str(exc), "debug_uri": debug_uri},
        )
        raise


def metadata_sync(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    channel_id = params.get("channel_id", "manual")
    uploads_playlist_id = params.get("uploads_playlist_id")
    job_id = params.get("job_id")
    playlist_page_token = params.get("page_token")
    playlist_next_page_token = None
    raw_channel_uri = None
    raw_playlist_uri = None
    raw_videos_uri = None
    enqueued_next_page = None
    if params.get("video_resources"):
        resources = params["video_resources"]
    else:
        client = params.get("youtube_client") or YouTubeClient()
        channel = _channel_config(repo, params)
        channel_id = channel["channel_id"]
        uploads_playlist_id = channel.get("uploads_playlist_id")
        if channel_id and hasattr(client, "channels"):
            channel_response = client.channels([channel_id])
            raw_channel_uri = _write_json_blob(
                f"raw/youtube/metadata/channel_id={channel_id}/channels/{now_iso()}.json",
                channel_response,
            )
            channel_items = channel_response.get("items", [])
            if channel_items:
                normalized_channel = normalize_channel_resource(channel_items[0])
                repo.put_channel(
                    {
                        **channel,
                        **normalized_channel,
                        "uploads_playlist_id": normalized_channel.get("uploads_playlist_id") or uploads_playlist_id,
                        "raw_metadata_uri": raw_channel_uri,
                    }
                )
                uploads_playlist_id = normalized_channel.get("uploads_playlist_id") or uploads_playlist_id
            repo.record_quota_usage("channels.list", 1, {}, channel_id=channel_id, video_count=0, job_id=job_id)
        playlist_page_token = playlist_page_token if playlist_page_token is not None else _metadata_cursor(repo, channel_id).get("next_page_token")
        playlist = client.playlist_items(uploads_playlist_id, playlist_page_token, int(params.get("max_results", 50)))
        raw_playlist_uri = _write_json_blob(
            f"raw/youtube/metadata/channel_id={channel_id}/playlistItems/{now_iso()}.json",
            playlist,
        )
        video_ids = [item["contentDetails"]["videoId"] for item in playlist.get("items", [])]
        repo.record_quota_usage(
            "playlistItems.list",
            1,
            {"page_token": playlist_page_token},
            channel_id=channel_id,
            video_count=len(video_ids),
            job_id=job_id,
        )
        videos_response = client.videos(video_ids) if video_ids else {"items": []}
        raw_videos_uri = _write_json_blob(
            f"raw/youtube/metadata/channel_id={channel_id}/videos/{now_iso()}.json",
            videos_response,
        )
        resources = videos_response.get("items", [])
        playlist_next_page_token = playlist.get("nextPageToken")
        if video_ids:
            repo.record_quota_usage("videos.list", 1, {}, channel_id=channel_id, video_count=len(video_ids), job_id=job_id)
        if playlist_next_page_token:
            enqueued_next_page = _enqueue_job(
                "DIOPSIDE_METADATA_QUEUE_URL",
                build_job_message(
                    "metadata_sync",
                    f"manual-metadata-{channel_id}",
                    {
                        "channel_id": channel_id,
                        "uploads_playlist_id": uploads_playlist_id,
                        "page_token": playlist_next_page_token,
                        "max_results": int(params.get("max_results", 50)),
                    },
                    requested_by="worker",
                    trace_id=params.get("trace_id"),
                ),
            )
    saved = []
    for resource in resources:
        resource_raw_uri = raw_videos_uri
        if not resource_raw_uri and params.get("video_resources"):
            resource_raw_uri = _write_json_blob(
                f"raw/youtube/metadata/video_id={resource['id']}/{now_iso()}.json",
                resource,
            )
        video = {**normalize_video_resource(resource), **({"raw_metadata_uri": resource_raw_uri} if resource_raw_uri else {})}
        repo.put_video(video)
        channel_id = video.get("channel_id") or channel_id
        saved.append(video["video_id"])
    repo.put_channel_sync_cursor(
        channel_id,
        {
            "uploads_playlist_id": uploads_playlist_id,
            "page_token": playlist_page_token,
            "next_page_token": playlist_next_page_token,
            "last_seen_video_id": saved[0] if saved else None,
            "last_video_ids": saved,
            "raw_playlist_uri": raw_playlist_uri,
            "raw_videos_uri": raw_videos_uri,
            "saved_count": len(saved),
            "job_id": job_id,
        },
    )
    return {
        "channel_id": channel_id,
        "saved_video_ids": saved,
        "saved_count": len(saved),
        "page_token": playlist_page_token,
        "next_page_token": playlist_next_page_token,
        "raw_playlist_uri": raw_playlist_uri,
        "raw_videos_uri": raw_videos_uri,
        "raw_channel_uri": raw_channel_uri,
        "enqueued_next_page": bool(enqueued_next_page),
    }


def live_status_scan(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    job_id = params.get("job_id")
    client = params.get("youtube_client")
    videos = repo.list_videos(10000)
    candidates = [video for video in videos if video.get("video_id") and not video.get("actual_end_time")]
    if candidates and (client or not params.get("skip_youtube_refresh")):
        client = client or YouTubeClient()
        refreshed_items = []
        for chunk in _chunks([video["video_id"] for video in candidates], 50):
            refreshed = client.videos(chunk)
            refreshed_items.extend(refreshed.get("items", []))
            repo.record_quota_usage(
                "videos.list",
                1,
                {"source": "live_status_scan"},
                channel_id=params.get("channel_id") or _single_value(video.get("channel_id") for video in candidates),
                video_count=len(chunk),
                job_id=job_id,
            )
        by_id = {item["id"]: normalize_video_resource(item) for item in refreshed_items}
        videos = [{**video, **by_id.get(video["video_id"], {}), "_previous_live_state": video.get("live_state")} for video in videos]
    updated = []
    enqueued = []
    notification_plan_video_ids = []
    for video in videos:
        before = video.pop("_previous_live_state", video.get("live_state"))
        if video.get("actual_end_time"):
            video["live_state"] = "archived"
        elif video.get("live_chat_id"):
            video["live_state"] = "live"
        elif video.get("scheduled_start_time"):
            video["live_state"] = "upcoming"
        else:
            video["live_state"] = "archived"
        repo.put_video(video)
        if before != video["live_state"]:
            updated.append({"video_id": video["video_id"], "from": before, "to": video["live_state"]})
            repo.append_video_state_event(
                video["video_id"],
                video["live_state"],
                from_state=before,
                source_job_id=job_id,
                payload={
                    "requested_by": params.get("requested_by", "live_status_scan"),
                    "scheduled_start_time": video.get("scheduled_start_time"),
                    "actual_start_time": video.get("actual_start_time"),
                    "actual_end_time": video.get("actual_end_time"),
                },
        )
        if video["live_state"] == "live" and video.get("live_chat_id"):
            enqueued.append(
                _enqueue_job(
                    "DIOPSIDE_CHAT_QUEUE_URL",
                    build_job_message(
                        "chat_collect",
                        f"manual-live-{video['video_id']}",
                        {"video_id": video["video_id"], "mode": "live", "live_chat_id": video["live_chat_id"]},
                        requested_by="worker",
                        trace_id=params.get("trace_id"),
                    ),
                )
            )
        if video["live_state"] == "upcoming" and video.get("scheduled_start_time"):
            notification_plan_video_ids.append(video["video_id"])
            enqueued.append(
                _enqueue_job(
                    "DIOPSIDE_AGGREGATE_QUEUE_URL",
                    build_job_message(
                        "notification_plan",
                        f"manual-notification-plan-{video['video_id']}",
                        {"video_id": video["video_id"], "scheduled_start_time": video["scheduled_start_time"], "requested_by": "live_status_scan"},
                        requested_by="worker",
                        trace_id=params.get("trace_id"),
                    ),
                )
            )
        if before in {"upcoming", "live"} and video["live_state"] == "archived":
            enqueued.append(
                _enqueue_job(
                    "DIOPSIDE_AGGREGATE_QUEUE_URL",
                    build_job_message(
                        "archive_finalize",
                        f"manual-archive-finalize-{video['video_id']}",
                        {"video_id": video["video_id"], "requested_by": "live_status_scan"},
                        requested_by="worker",
                        trace_id=params.get("trace_id"),
                    ),
                )
            )
    return {
        "updated": updated,
        "enqueue_chat_collect": [item["video_id"] for item in updated if item["to"] == "live"],
        "enqueue_archive_finalize": [item["video_id"] for item in updated if item["to"] == "archived"],
        "enqueue_notification_plan": notification_plan_video_ids,
        "enqueued": [item for item in enqueued if item],
    }


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _single_value(values: Any) -> str | None:
    present = {value for value in values if value}
    return next(iter(present)) if len(present) == 1 else None


def chat_collect(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    mode = params.get("mode", "auto")
    video = repo.get_video(video_id) or {"video_id": video_id}
    parser_stats = None
    if params.get("replay_actions") or mode == "replay":
        replay_continuations = params.get("replay_continuations", [])
        if params.get("replay_actions"):
            actions = params["replay_actions"]
        elif params.get("replay_continuation"):
            continuation = params["replay_continuation"]
            continuation_token = continuation["token"] if isinstance(continuation, dict) else str(continuation)
            if params.get("replay_continuation_response"):
                continuation_response = params["replay_continuation_response"]
            else:
                replay_client = params.get("replay_client")
                continuation_response = replay_client.replay_continuation(continuation_token) if replay_client else fetch_public_replay_continuation(continuation_token)
            actions = extract_replay_actions_from_initial_data(continuation_response)
            replay_continuations = extract_replay_continuations_from_initial_data(continuation_response)
        elif params.get("replay_initial_data"):
            initial_data = params["replay_initial_data"]
            actions = extract_replay_actions_from_initial_data(initial_data)
            replay_continuations = extract_replay_continuations_from_initial_data(initial_data)
        elif params.get("replay_html"):
            initial_data = extract_initial_data_from_watch_html(params["replay_html"])
            actions = extract_replay_actions_from_initial_data(initial_data)
            replay_continuations = extract_replay_continuations_from_initial_data(initial_data)
        else:
            actions = fetch_public_replay_actions(video_id)
        messages = normalize_replay_actions(actions, video_id)
        source = "replay"
        parser_stats = _chat_parser_stats(actions, messages, replay_continuations)
        next_poll = {
            "action": "continuation_available" if replay_continuations else "stop",
            "continuation_count": len(replay_continuations),
            "continuations": replay_continuations[:5],
            "action_count": len(actions),
            "unknown_count": parser_stats["unknown_count"],
            "stop_reason": None if replay_continuations else "no_continuation",
        }
        for continuation in replay_continuations[:5]:
            _enqueue_job(
                "DIOPSIDE_CHAT_QUEUE_URL",
                build_job_message(
                    "chat_collect",
                    f"manual-replay-{video_id}-{continuation['token']}",
                    {"video_id": video_id, "mode": "replay", "replay_continuation": continuation},
                    requested_by="worker",
                    trace_id=params.get("trace_id"),
                ),
                delay_seconds=max(0, int(continuation.get("timeout_ms") or 0) // 1000),
            )
    else:
        response = params.get("live_chat_response")
        if response is None:
            client = params.get("youtube_client") or YouTubeClient()
            response = client.live_chat_messages(video.get("live_chat_id") or params["live_chat_id"], params.get("page_token"))
            repo.record_quota_usage(
                "liveChatMessages.list",
                1,
                {"page_token": params.get("page_token")},
                channel_id=video.get("channel_id") or params.get("channel_id"),
                video_count=1,
                job_id=params.get("job_id"),
            )
        messages = normalize_live_chat_items(response.get("items", []), video_id)
        source = "live"
        delay_seconds = max(1, int(response.get("pollingIntervalMillis", 10000)) // 1000)
        requeue_delay_seconds = min(delay_seconds, 900)
        rate_limited = _live_chat_rate_limited(response)
        offline_at = response.get("offlineAt")
        next_page_token = response.get("nextPageToken")
        if rate_limited:
            action = "retry_later"
            stop_reason = "rate_limit_exceeded"
        elif offline_at:
            action = "stop"
            stop_reason = "offline"
        elif next_page_token:
            action = "requeue"
            stop_reason = None
        else:
            action = "stop"
            stop_reason = "no_next_page_token"
        next_poll = {
            "action": action,
            "next_page_token": next_page_token,
            "delay_seconds": delay_seconds,
            "requeue_delay_seconds": requeue_delay_seconds if action == "requeue" else None,
            "offline_at": offline_at,
            "rate_limited": rate_limited,
            "stop_reason": stop_reason,
        }
        if action == "requeue":
            _enqueue_job(
                "DIOPSIDE_CHAT_QUEUE_URL",
                build_job_message(
                    "chat_collect",
                    f"manual-live-{video_id}",
                    {"video_id": video_id, "mode": "live", "live_chat_id": video.get("live_chat_id") or params.get("live_chat_id"), "page_token": next_page_token},
                    requested_by="worker",
                    trace_id=params.get("trace_id"),
                ),
                delay_seconds=requeue_delay_seconds,
            )
    raw_key = f"raw/youtube/chat/video_id={video_id}/source={source}/{now_iso()}.jsonl"
    body = ("\n".join(json.dumps(message, ensure_ascii=False) for message in messages) + ("\n" if messages else "")).encode("utf-8")
    raw_uri = _write_blob(raw_key, body, "application/x-ndjson")
    offsets = [int(message.get("video_offset_time_msec") or 0) for message in messages]
    repo.put_chat_page_manifest(
        video_id,
        {
            "source": source,
            "raw_s3_uri": raw_uri,
            "item_count": len(messages),
            "checksum": hashlib.sha256(body).hexdigest(),
            "first_offset_msec": min(offsets) if offsets else None,
            "last_offset_msec": max(offsets) if offsets else None,
            "next_poll": next_poll,
            "job_id": params.get("job_id") or f"chat_collect#{video_id}",
            "polling_interval_ms": int(next_poll["delay_seconds"] * 1000) if next_poll.get("delay_seconds") is not None else None,
            **({"parser_stats": parser_stats} if parser_stats else {}),
        },
    )
    return {"video_id": video_id, "source": source, "message_count": len(messages), "next_poll": next_poll, **({"parser_stats": parser_stats} if parser_stats else {})}


def chat_normalize(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    chunks = repo.list_chat_chunks(video_id)
    aggregator = ChatAggregateAccumulator()
    normalized_body = bytearray()
    seen_message_ids: set[str] = set()
    for chunk in chunks:
        for message in _iter_jsonl(chunk["s3_uri"]):
            message_id = str(message.get("message_id") or "")
            if message_id:
                if message_id in seen_message_ids:
                    continue
                seen_message_ids.add(message_id)
            aggregator.add(message)
            normalized_body.extend(json.dumps(message, ensure_ascii=False).encode("utf-8"))
            normalized_body.extend(b"\n")
    summary = aggregator.summary()
    repo.put_chat_aggregate(video_id, summary)
    normalized_key = f"processed/chat-normalized/video_id={video_id}/part-000.jsonl"
    aggregate_key = f"processed/chat-aggregate/video_id={video_id}/summary.json"
    _write_blob(normalized_key, bytes(normalized_body), "application/x-ndjson", bucket_env="DIOPSIDE_PROCESSED_BUCKET")
    _write_blob(aggregate_key, json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", bucket_env="DIOPSIDE_PROCESSED_BUCKET")
    repo.put_chat_manifest(
        video_id,
        {
            "normalized_s3_uri": f"s3://{os.environ.get('DIOPSIDE_PROCESSED_BUCKET', 'processed')}/{normalized_key}",
            "message_count": summary["message_count"],
        },
    )
    return {"video_id": video_id, "message_count": summary["message_count"], "top_term_count": len(summary["top_terms"])}


class ChatAggregateAccumulator:
    def __init__(self, bucket_sec: int = 60) -> None:
        self.bucket_sec = bucket_sec
        self.message_count = 0
        self.authors: set[str] = set()
        self.paid_message_count = 0
        self.emoji_count = 0
        self.terms: Counter[str] = Counter()
        self.timeline: Counter[int] = Counter()
        self.term_timeline: dict[str, Counter[int]] = {}

    def add(self, message: dict[str, Any]) -> None:
        self.message_count += 1
        author = message.get("author_external_channel_id") or message.get("author_name")
        if author:
            self.authors.add(author)
        if message.get("message_type") == "paid":
            self.paid_message_count += 1
        self.emoji_count += sum(1 for run in message.get("message_runs", []) if run.get("type") == "emoji")
        offset = int(message.get("video_offset_time_msec") or 0) // 1000
        bucket_offset = (offset // self.bucket_sec) * self.bucket_sec
        self.timeline[bucket_offset] += 1
        for term in _chat_terms(message.get("message_text", "")):
            self.terms[term] += 1
            self.term_timeline.setdefault(term, Counter())[bucket_offset] += 1

    def summary(self) -> dict[str, Any]:
        return {
            "message_count": self.message_count,
            "unique_author_count": len(self.authors),
            "paid_message_count": self.paid_message_count,
            "emoji_count": self.emoji_count,
            "timeline_buckets": [{"offset_sec": offset, "message_count": count} for offset, count in sorted(self.timeline.items())],
            "top_terms": [{"term": term, "score": count} for term, count in self.terms.most_common(40)],
            "term_timeline": {
                term: [{"offset_sec": offset, "count": count} for offset, count in sorted(bucket_counts.items())]
                for term, bucket_counts in sorted(self.term_timeline.items())
            },
        }


def retry_job(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    target_job_id = params["target_job_id"]
    target = repo.get_job(target_job_id)
    if not target:
        raise ValueError(f"target job does not exist: {target_job_id}")
    state = target.get("derived_state")
    if state not in {"failed", "retryable"}:
        raise ValueError(f"target job is not retryable: {state}")
    repo.append_job_event(target_job_id, "retry_requested", {"reason": params.get("reason")})
    queue_env = _queue_env_for_job_type(target["job_type"])
    enqueued = _enqueue_job(
        queue_env,
        build_job_message(
            target["job_type"],
            target_job_id,
            {**target.get("payload", {}), "retry_of": target_job_id},
            idempotency_key=target.get("idempotency_key") or target.get("dedupe_key"),
            requested_by="worker",
            attempt=int(target.get("attempt", 0)) + 1,
            trace_id=params.get("trace_id"),
        ),
    )
    return {"target_job_id": target_job_id, "target_job_type": target["job_type"], "enqueued": bool(enqueued)}


def cancel_job(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    target_job_id = params["target_job_id"]
    target = repo.get_job(target_job_id)
    if not target:
        raise ValueError(f"target job does not exist: {target_job_id}")
    state = target.get("derived_state")
    if state in {"succeeded", "failed", "cancelled"}:
        raise ValueError(f"target job is already terminal: {state}")
    repo.append_job_event(target_job_id, "cancelled", {"reason": params.get("reason")})
    return {"target_job_id": target_job_id, "cancelled": True}


def quota_rollup(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    usage = repo.list_quota_usage(int(params.get("limit", 10000)))
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    total_units = 0
    threshold_units = int(params.get("warning_threshold_units") or 9000)
    for item in usage:
        method = item.get("method") or "unknown"
        units = int(item.get("units") or 0)
        quota_date = _quota_date(item, params.get("quota_date"))
        key = (quota_date, method)
        group = grouped.setdefault(
            key,
            {
                "quota_date": quota_date,
                "method": method,
                "call_count": 0,
                "units_used": 0,
                "video_count": 0,
                "channel_ids": set(),
                "job_ids": set(),
            },
        )
        group["call_count"] += 1
        group["units_used"] += units
        group["video_count"] += int(item.get("video_count") or 0)
        if item.get("channel_id"):
            group["channel_ids"].add(item["channel_id"])
        if item.get("job_id"):
            group["job_ids"].add(item["job_id"])
        total_units += units
    rolled_up_at = now_iso()
    warning_emitted = bool(total_units >= threshold_units) if threshold_units > 0 else False
    warning_already_emitted = False
    for (quota_date, method) in grouped:
        existing = repo.get_item(f"QUOTA#{quota_date}", f"METHOD#{method}")
        warning_already_emitted = warning_already_emitted or bool(existing and existing.get("warning_emitted"))
    summaries = []
    by_method: dict[str, int] = {}
    for _, group in sorted(grouped.items()):
        call_count = group["call_count"]
        units_used = group["units_used"]
        unit_per_call = units_used // call_count if call_count and units_used % call_count == 0 else units_used / call_count
        item = repo.put_item(
            {
                "item_type": "QuotaUsage",
                "pk": f"QUOTA#{group['quota_date']}",
                "sk": f"METHOD#{group['method']}",
                "record_type": "daily_method_summary",
                "quota_date": group["quota_date"],
                "method": group["method"],
                "call_count": call_count,
                "units_used": units_used,
                "unit_per_call": unit_per_call,
                "video_count": group["video_count"],
                "channel_ids": sorted(group["channel_ids"]),
                "job_ids": sorted(group["job_ids"]),
                "source_record_count": call_count,
                "warning_emitted": warning_emitted,
                "warning_threshold_units": threshold_units,
                "warning_total_units": total_units,
                "updated_at": rolled_up_at,
                "gsi3pk": "QUOTA#ROLLUP",
                "gsi3sk": f"{group['quota_date']}#{group['method']}",
            }
        )
        summaries.append(item)
        by_method[item["method"]] = by_method.get(item["method"], 0) + item["units_used"]
    warning_event = None
    if warning_emitted and not warning_already_emitted and params.get("job_id"):
        warning_event = repo.append_job_event(
            params["job_id"],
            "quota_threshold_warning",
            {
                "quota_dates": sorted({group["quota_date"] for group in grouped.values()}),
                "total_units": total_units,
                "threshold_units": threshold_units,
                "by_method": by_method,
            },
        )
    return {
        "requested_by": params.get("requested_by", "scheduler"),
        "item_count": len(usage),
        "total_units": total_units,
        "by_method": by_method,
        "summary_count": len(summaries),
        "warning_emitted": warning_emitted,
        "warning_threshold_units": threshold_units,
        "warning_event_id": warning_event.get("sk") if warning_event else None,
        "summaries": summaries,
    }


def cleanup(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested_by": params.get("requested_by", "scheduler"),
        "dry_run": True,
        "deleted_count": 0,
        "policy_version": params.get("policy_version", "v1"),
    }


def archive_finalize(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    job_id = params.get("job_id")
    video = repo.get_video(video_id)
    if not video:
        raise ValueError(f"video does not exist: {video_id}")
    before_state = video.get("live_state")
    refreshed = False
    if not params.get("skip_youtube_refresh"):
        client = params.get("youtube_client") or YouTubeClient()
        response = client.videos([video_id])
        repo.record_quota_usage(
            "videos.list",
            1,
            {"source": "archive_finalize"},
            channel_id=video.get("channel_id") or params.get("channel_id"),
            video_count=1,
            job_id=job_id,
        )
        if response.get("items"):
            video = {**video, **normalize_video_resource(response["items"][0])}
            refreshed = True
    finalized_at = now_iso()
    repo.put_video({**video, "video_id": video_id, "live_state": "archived", "archive_finalized_at": finalized_at})
    repo.append_video_state_event(
        video_id,
        "archived",
        from_state=before_state,
        source_job_id=job_id,
        occurred_at=finalized_at,
        event_name="video.archive_finalized",
        payload={"requested_by": params.get("requested_by", "archive_finalize"), "refreshed": refreshed},
    )
    archive_plan = _put_notification_plan(repo, video_id, "archive_available", params.get("due_at") or finalized_at, source_job_id=job_id)
    replay_enqueued = _enqueue_job(
        "DIOPSIDE_CHAT_QUEUE_URL",
        build_job_message(
            "chat_collect",
            f"manual-replay-{video_id}",
            {"video_id": video_id, "mode": "replay", "requested_by": "archive_finalize"},
            requested_by="worker",
            trace_id=params.get("trace_id"),
        ),
    )
    export_enqueued = _enqueue_job(
        "DIOPSIDE_STATIC_EXPORT_QUEUE_URL",
        build_job_message(
            "static_export",
            f"manual-static-export-{video_id}",
            {"scope": "video", "video_id": video_id, "requested_by": "archive_finalize"},
            requested_by="worker",
            trace_id=params.get("trace_id"),
        ),
    )
    return {
        "video_id": video_id,
        "refreshed": refreshed,
        "archive_finalized_at": finalized_at,
        "notification_plan": archive_plan,
        "replay_enqueued": bool(replay_enqueued),
        "static_export_enqueued": bool(export_enqueued),
    }


def notification_plan(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    video = repo.get_video(video_id) or {"video_id": video_id}
    scheduled_start_time = params.get("scheduled_start_time") or video.get("scheduled_start_time")
    notification_types = params.get("notification_types")
    if notification_types is None:
        notification_types = ["before_30min", "at_start"] if scheduled_start_time else ["archive_available"]
    plans = []
    for notification_type in notification_types:
        due_at = params.get("due_at") or _notification_due_at(notification_type, scheduled_start_time)
        plans.append(_put_notification_plan(repo, video_id, notification_type, due_at, source_job_id=params.get("job_id")))
    return {"video_id": video_id, "planned_count": len(plans), "items": plans}


def rebuild_artifacts(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    video = repo.get_video(video_id) or {"description": ""}
    aggregate = repo.get_chat_aggregate(video_id) or summarize_chat_messages([])
    timestamps = build_timestamp_candidates(aggregate, video.get("description", ""))
    chapters = generate_chapters_suggestion_markdown(video_id, timestamps).encode("utf-8")
    repo.put_video({**video, "video_id": video_id, "timestamps": timestamps})
    timestamp_key = f"processed/timestamps/video_id={video_id}/timestamp_candidates.json"
    chapters_key = f"processed/timestamps/video_id={video_id}/chapters_suggestion.md"
    timestamp_body = json.dumps({"video_id": video_id, "items": timestamps}, ensure_ascii=False, indent=2).encode("utf-8")
    _write_blob(timestamp_key, timestamp_body, "application/json", bucket_env="DIOPSIDE_PROCESSED_BUCKET")
    chapters_uri = _write_blob(chapters_key, chapters, "text/markdown; charset=utf-8", bucket_env="DIOPSIDE_PROCESSED_BUCKET")
    repo.put_artifact(video_id, {"artifact_type": "timestamp", "public_url_path": f"/data/latest-video/{video_id}", "content_type": "application/json"})
    repo.put_artifact(video_id, {"artifact_type": "timestamp_chapters", "public_url_path": f"/data/artifacts/timestamps/{video_id}.md", "s3_uri": chapters_uri, "content_type": "text/markdown; charset=utf-8", "byte_size": len(chapters)})
    if aggregate.get("top_terms"):
        repo.put_artifact(video_id, {"artifact_type": "wordcloud", "public_url_path": f"/data/artifacts/wordcloud/{video_id}.png", "content_type": "image/png"})
    return {"video_id": video_id, "timestamp_count": len(timestamps), "chapters_suggestion_uri": chapters_uri, "wordcloud_available": bool(aggregate.get("top_terms"))}


def file_output(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    artifact_type = params["artifact_type"]
    artifact_version = params.get("artifact_version", "v1")
    key = _validate_artifact_key(params["key"])
    content_type = params.get("content_type", "application/octet-stream")
    visibility = params.get("visibility", "private")
    if visibility not in {"public", "private"}:
        raise ValueError("visibility must be public or private")

    body = _artifact_body(params)
    content_hash = hashlib.sha256(body).hexdigest()
    bucket_env = params.get("bucket_env") or ("DIOPSIDE_PUBLIC_DATA_BUCKET" if visibility == "public" else "DIOPSIDE_PROCESSED_BUCKET")
    uri = _write_blob(key, body, content_type, bucket_env=bucket_env)
    generated_at = now_iso()
    artifact = {
        "artifact_type": artifact_type,
        "artifact_version": artifact_version,
        "content_type": content_type,
        "content_hash": f"sha256:{content_hash}",
        "byte_size": len(body),
        "generated_at": generated_at,
    }
    if params.get("job_id"):
        artifact["source_job_id"] = params["job_id"]
    if visibility == "public":
        artifact["public_url_path"] = params.get("public_url_path") or f"/{key.lstrip('/')}"
        if uri.startswith("s3://"):
            artifact["s3_uri"] = uri
    else:
        artifact["s3_uri"] = uri
    stored = repo.put_artifact(video_id, artifact)
    return {
        "video_id": video_id,
        "artifact_type": artifact_type,
        "artifact_version": artifact_version,
        "content_hash": artifact["content_hash"],
        "byte_size": len(body),
        "uri": uri,
        "public_url_path": artifact.get("public_url_path"),
        "artifact_id": f"{video_id}:{artifact_type}",
        "stored": bool(stored),
    }


def _put_notification_plan(repo: Any, video_id: str, notification_type: str, due_at: str, source_job_id: str | None = None) -> dict[str, Any]:
    stamp = now_iso()
    existing = repo.get_item(f"VID#{video_id}", f"NOTIFY#{notification_type}") or {}
    item = {
        **existing,
        "item_type": "NotificationPlan",
        "pk": f"VID#{video_id}",
        "sk": f"NOTIFY#{notification_type}",
        "video_id": video_id,
        "notification_type": notification_type,
        "due_at": due_at,
        "delivery_state": existing.get("delivery_state", "planned"),
        "target": existing.get("target", "none"),
        "message_template_id": existing.get("message_template_id") or notification_type,
        "updated_at": stamp,
        "gsi3pk": "NOTIFY#DUE",
        "gsi3sk": f"DUE#{due_at}#{video_id}#{notification_type}",
    }
    if not item.get("created_at"):
        item["created_at"] = stamp
    if source_job_id:
        item["source_job_id"] = source_job_id
    return repo.put_item(item)


def _notification_due_at(notification_type: str, scheduled_start_time: str | None) -> str:
    if notification_type == "archive_available":
        return now_iso()
    if not scheduled_start_time:
        raise ValueError(f"scheduled_start_time is required for notification_type: {notification_type}")
    start = _parse_iso(scheduled_start_time)
    if notification_type == "before_30min":
        return _format_iso(start - timedelta(minutes=30))
    if notification_type == "at_start":
        return _format_iso(start)
    raise ValueError(f"unsupported notification_type: {notification_type}")


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quota_date(item: dict[str, Any], override: str | None = None) -> str:
    if override:
        return override.replace("-", "")
    if item.get("quota_date"):
        return str(item["quota_date"]).replace("-", "")
    if item.get("pk", "").startswith("QUOTA#"):
        return item["pk"].removeprefix("QUOTA#").replace("-", "")
    return str(item.get("created_at") or now_iso())[:10].replace("-", "")


def _log_worker_job(
    started: float,
    trace_id: str,
    job_id: str,
    job_type: str | None,
    params: dict[str, Any],
    *,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    log = {
        "service": "diopside",
        "component": "worker",
        "event": "worker_job",
        "trace_id": trace_id,
        "job_id": job_id,
        "job_type": job_type,
        "video_id": _first_present(result, params, key="video_id"),
        "result": "failed" if error else "succeeded",
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        **({"error": error} if error else {}),
    }
    print(json.dumps({key: value for key, value in log.items() if value is not None}, ensure_ascii=False), flush=True)


def _first_present(*sources: dict[str, Any] | None, key: str) -> Any:
    for source in sources:
        if source and source.get(key) is not None:
            return source[key]
    return None


def _channel_config(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    if params.get("uploads_playlist_id"):
        return {"channel_id": params.get("channel_id", "manual"), "uploads_playlist_id": params["uploads_playlist_id"]}
    config = repo.get_item("CONFIG#app", "CHANNEL#default")
    if not config:
        raise ValueError("uploads_playlist_id is required when default channel is not configured")
    return config


def _metadata_cursor(repo: Any, channel_id: str) -> dict[str, Any]:
    return repo.get_channel_sync_cursor(channel_id) or {}


def _live_chat_rate_limited(response: dict[str, Any]) -> bool:
    errors = response.get("error", {}).get("errors", [])
    return any(error.get("reason") == "rateLimitExceeded" for error in errors)


def _chat_parser_stats(actions: list[dict[str, Any]], messages: list[dict[str, Any]], continuations: list[dict[str, Any]]) -> dict[str, Any]:
    renderer_types: dict[str, int] = {}
    unknown_count = 0
    for message in messages:
        renderer_type = message.get("raw_renderer_type") or "unknown"
        renderer_types[renderer_type] = renderer_types.get(renderer_type, 0) + 1
        if message.get("parse_warning"):
            unknown_count += 1
    return {
        "action_count": len(actions),
        "message_count": len(messages),
        "known_count": len(messages) - unknown_count,
        "unknown_count": unknown_count,
        "renderer_types": renderer_types,
        "continuation_count": len(continuations),
    }


def _repository() -> Any:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        return DynamoRepository(os.environ["DIOPSIDE_TABLE_NAME"])
    return MemoryRepository()


def _write_blob(key: str, body: bytes, content_type: str, bucket_env: str = "DIOPSIDE_RAW_BUCKET") -> str:
    bucket = os.environ.get(bucket_env)
    if bucket:
        import boto3

        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
        return f"s3://{bucket}/{key}"
    local_root = os.environ.get("DIOPSIDE_LOCAL_ARTIFACT_DIR")
    if local_root:
        path = pathlib.Path(local_root) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return str(path)
    return key


def _write_json_blob(key: str, payload: dict[str, Any], bucket_env: str = "DIOPSIDE_RAW_BUCKET") -> str:
    return _write_blob(key, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", bucket_env=bucket_env)


def _artifact_body(params: dict[str, Any]) -> bytes:
    if "body_base64" in params:
        import base64

        return base64.b64decode(params["body_base64"])
    if "json_body" in params:
        return json.dumps(params["json_body"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if "body" in params:
        body = params["body"]
        if isinstance(body, bytes):
            return body
        if isinstance(body, str):
            return body.encode("utf-8")
    raise ValueError("body, body_base64, or json_body is required")


def _validate_artifact_key(key: str) -> str:
    if not key or key.startswith("/") or ".." in pathlib.PurePosixPath(key).parts:
        raise ValueError("artifact key must be a relative path without traversal")
    return key


def _read_jsonl(uri: str) -> list[dict[str, Any]]:
    return list(_iter_jsonl(uri))


def _iter_jsonl(uri: str):
    if uri.startswith("s3://"):
        if "/" not in uri[5:]:
            raise ValueError(f"invalid s3 uri: {uri}")
        bucket, key = uri[5:].split("/", 1)
        import boto3

        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"]
        for raw_line in body.iter_lines():
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if line.strip():
                yield json.loads(line)
        return
    path = pathlib.Path(uri)
    if not path.is_absolute():
        local_root = os.environ.get("DIOPSIDE_LOCAL_ARTIFACT_DIR")
        if local_root:
            path = pathlib.Path(local_root) / uri
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _parse_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _chat_terms(text: str) -> list[str]:
    import re

    stopwords = {"これ", "それ", "あれ", "する", "いる", "ある", "こと", "ため", "さん", "ちゃん", "https", "http", "www"}
    cleaned = re.sub(r"https?://\S+", " ", text)
    cleaned = re.sub(r"[\u3000\s\W_]+", " ", cleaned, flags=re.UNICODE)
    result = []
    for raw in cleaned.split():
        term = raw.strip().lower()
        if len(term) < 2 or term in stopwords:
            continue
        result.append(term)
    return result


def _queue_env_for_job_type(job_type: str) -> str:
    return JOB_QUEUE_ENVS[job_type]


def _enqueue_job(queue_env: str, payload: dict[str, Any], delay_seconds: int = 0) -> str | None:
    queue_url = os.environ.get(queue_env)
    if not queue_url:
        return None
    import boto3

    message = payload
    if "payload" not in message and message.get("job_type") and message.get("job_id"):
        message = build_job_message(
            str(message["job_type"]),
            str(message["job_id"]),
            message.get("input", message),
            idempotency_key=message.get("idempotency_key"),
            requested_by=str(message.get("requested_by") or "worker"),
            attempt=message.get("attempt"),
            trace_id=message.get("trace_id"),
        )
    args: dict[str, Any] = {"QueueUrl": queue_url, "MessageBody": json.dumps(message, ensure_ascii=False)}
    if delay_seconds:
        args["DelaySeconds"] = delay_seconds
    boto3.client("sqs").send_message(**args)
    return queue_url
