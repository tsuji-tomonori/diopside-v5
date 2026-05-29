from __future__ import annotations

import json
import os
import pathlib
import hashlib
from typing import Any

from diopside_core import (
    DynamoRepository,
    MemoryRepository,
    YouTubeClient,
    build_timestamp_candidates,
    extract_initial_data_from_watch_html,
    extract_replay_actions_from_initial_data,
    fetch_public_replay_actions,
    normalize_live_chat_items,
    normalize_replay_actions,
    normalize_video_resource,
    now_iso,
    summarize_chat_messages,
)


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
    job_type = payload.get("job_type")
    job_id = payload.get("job_id", "manual")
    repo.append_job_event(job_id, "started", {"job_type": job_type})
    try:
        if job_type == "metadata_sync":
            result = metadata_sync(repo, payload.get("input", payload))
        elif job_type == "live_status_scan":
            result = live_status_scan(repo, payload.get("input", payload))
        elif job_type == "chat_collect":
            result = chat_collect(repo, payload.get("input", payload))
        elif job_type == "chat_normalize":
            result = chat_normalize(repo, payload.get("input", payload))
        elif job_type == "rebuild_artifacts":
            result = rebuild_artifacts(repo, payload.get("input", payload))
        elif job_type == "retry_job":
            result = retry_job(repo, payload.get("input", payload))
        elif job_type == "cancel_job":
            result = cancel_job(repo, payload.get("input", payload))
        else:
            raise ValueError(f"unsupported job_type: {job_type}")
        repo.append_job_event(job_id, "completed", result)
        return {"job_id": job_id, "job_type": job_type, "status": "succeeded", **result}
    except Exception as exc:
        debug_key = f"failed/jobs/job_id={job_id}/{now_iso()}.json"
        debug_uri = _write_blob(debug_key, json.dumps({"type": type(exc).__name__, "message": str(exc), "payload": payload}, ensure_ascii=False, indent=2).encode("utf-8"), "application/json")
        repo.append_job_event(job_id, "failed", {"type": type(exc).__name__, "message": str(exc), "debug_uri": debug_uri})
        raise


def metadata_sync(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    channel_id = params.get("channel_id", "manual")
    playlist_page_token = params.get("page_token")
    playlist_next_page_token = None
    raw_playlist_uri = None
    raw_videos_uri = None
    enqueued_next_page = None
    if params.get("video_resources"):
        resources = params["video_resources"]
    else:
        client = params.get("youtube_client") or YouTubeClient()
        channel = _channel_config(repo, params)
        channel_id = channel["channel_id"]
        playlist_page_token = playlist_page_token if playlist_page_token is not None else _metadata_cursor(repo, channel_id).get("next_page_token")
        playlist = client.playlist_items(channel["uploads_playlist_id"], playlist_page_token, int(params.get("max_results", 50)))
        raw_playlist_uri = _write_json_blob(
            f"raw/youtube/metadata/channel_id={channel_id}/playlistItems/{now_iso()}.json",
            playlist,
        )
        repo.record_quota_usage("playlistItems.list", 1, {"channel_id": channel_id, "page_token": playlist_page_token})
        video_ids = [item["contentDetails"]["videoId"] for item in playlist.get("items", [])]
        videos_response = client.videos(video_ids) if video_ids else {"items": []}
        raw_videos_uri = _write_json_blob(
            f"raw/youtube/metadata/channel_id={channel_id}/videos/{now_iso()}.json",
            videos_response,
        )
        resources = videos_response.get("items", [])
        playlist_next_page_token = playlist.get("nextPageToken")
        if video_ids:
            repo.record_quota_usage("videos.list", 1, {"video_count": len(video_ids), "channel_id": channel_id})
        if playlist_next_page_token:
            enqueued_next_page = _enqueue_job(
                "DIOPSIDE_METADATA_QUEUE_URL",
                {
                    "job_type": "metadata_sync",
                    "job_id": f"manual-metadata-{channel_id}",
                    "input": {
                        "channel_id": channel_id,
                        "uploads_playlist_id": channel["uploads_playlist_id"],
                        "page_token": playlist_next_page_token,
                        "max_results": int(params.get("max_results", 50)),
                    },
                },
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
    repo.put_item(
        {
            "item_type": "ChannelCursor",
            "pk": f"CHANNEL#{channel_id}",
            "sk": "CURSOR#metadata",
            "channel_id": channel_id,
            "cursor_name": "metadata",
            "page_token": playlist_page_token,
            "next_page_token": playlist_next_page_token,
            "last_video_id": saved[0] if saved else None,
            "last_video_ids": saved,
            "raw_playlist_uri": raw_playlist_uri,
            "raw_videos_uri": raw_videos_uri,
            "saved_count": len(saved),
            "updated_at": now_iso(),
        }
    )
    return {
        "channel_id": channel_id,
        "saved_video_ids": saved,
        "saved_count": len(saved),
        "page_token": playlist_page_token,
        "next_page_token": playlist_next_page_token,
        "raw_playlist_uri": raw_playlist_uri,
        "raw_videos_uri": raw_videos_uri,
        "enqueued_next_page": bool(enqueued_next_page),
    }


def live_status_scan(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    updated = []
    enqueued = []
    for video in repo.list_videos(10000):
        before = video.get("live_state")
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
        if video["live_state"] == "live" and video.get("live_chat_id"):
            enqueued.append(_enqueue_job("DIOPSIDE_CHAT_QUEUE_URL", {"job_type": "chat_collect", "job_id": f"manual-live-{video['video_id']}", "input": {"video_id": video["video_id"], "mode": "live", "live_chat_id": video["live_chat_id"]}}))
    return {"updated": updated, "enqueue_chat_collect": [item["video_id"] for item in updated if item["to"] == "live"], "enqueued": [item for item in enqueued if item]}


def chat_collect(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    mode = params.get("mode", "auto")
    video = repo.get_video(video_id) or {"video_id": video_id}
    if params.get("replay_actions") or mode == "replay":
        if params.get("replay_actions"):
            actions = params["replay_actions"]
        elif params.get("replay_initial_data"):
            actions = extract_replay_actions_from_initial_data(params["replay_initial_data"])
        elif params.get("replay_html"):
            actions = extract_replay_actions_from_initial_data(extract_initial_data_from_watch_html(params["replay_html"]))
        else:
            actions = fetch_public_replay_actions(video_id)
        messages = normalize_replay_actions(actions, video_id)
        source = "replay"
        next_poll = None
    else:
        client = params.get("youtube_client") or YouTubeClient()
        response = params.get("live_chat_response") or client.live_chat_messages(video.get("live_chat_id") or params["live_chat_id"], params.get("page_token"))
        messages = normalize_live_chat_items(response.get("items", []), video_id)
        source = "live"
        delay_seconds = int(response.get("pollingIntervalMillis", 10000)) // 1000
        next_poll = {
            "next_page_token": response.get("nextPageToken"),
            "delay_seconds": delay_seconds,
            "offline_at": response.get("offlineAt"),
            "rate_limited": any(error.get("reason") == "rateLimitExceeded" for error in response.get("error", {}).get("errors", [])),
        }
        if next_poll["next_page_token"] and not next_poll["rate_limited"]:
            _enqueue_job("DIOPSIDE_CHAT_QUEUE_URL", {"job_type": "chat_collect", "job_id": f"manual-live-{video_id}", "input": {"video_id": video_id, "mode": "live", "live_chat_id": video.get("live_chat_id") or params.get("live_chat_id"), "page_token": next_poll["next_page_token"]}}, delay_seconds=min(delay_seconds, 900))
    raw_key = f"raw/youtube/chat/video_id={video_id}/source={source}/{now_iso()}.jsonl"
    body = ("\n".join(json.dumps(message, ensure_ascii=False) for message in messages) + ("\n" if messages else "")).encode("utf-8")
    raw_uri = _write_blob(raw_key, body, "application/x-ndjson")
    offsets = [int(message.get("video_offset_time_msec") or 0) for message in messages]
    repo.put_item(
        {
            "item_type": "ChatMessageChunkManifest",
            "pk": f"VIDEO#{video_id}",
            "sk": f"CHAT#RAW#{source}#{now_iso()}",
            "video_id": video_id,
            "source": source,
            "s3_uri": raw_uri,
            "message_count": len(messages),
            "sha256": hashlib.sha256(body).hexdigest(),
            "first_offset_msec": min(offsets) if offsets else None,
            "last_offset_msec": max(offsets) if offsets else None,
            "next_poll": next_poll,
        }
    )
    return {"video_id": video_id, "source": source, "message_count": len(messages), "next_poll": next_poll}


def chat_normalize(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    chunks = repo.list_chat_chunks(video_id)
    messages = [message for chunk in chunks for message in _read_jsonl(chunk["s3_uri"])]
    summary = summarize_chat_messages(messages)
    repo.put_chat_aggregate(video_id, summary)
    normalized_key = f"processed/chat-normalized/video_id={video_id}/part-000.jsonl"
    aggregate_key = f"processed/chat-aggregate/video_id={video_id}/summary.json"
    _write_blob(normalized_key, "\n".join(json.dumps(message, ensure_ascii=False) for message in messages).encode("utf-8"), "application/x-ndjson", bucket_env="DIOPSIDE_PROCESSED_BUCKET")
    _write_blob(aggregate_key, json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", bucket_env="DIOPSIDE_PROCESSED_BUCKET")
    repo.put_item({"item_type": "ChatManifest", "pk": f"VIDEO#{video_id}", "sk": "CHAT#MANIFEST", "video_id": video_id, "normalized_uri": f"s3://{os.environ.get('DIOPSIDE_PROCESSED_BUCKET', 'processed')}/{normalized_key}", "message_count": len(messages), "updated_at": now_iso()})
    return {"video_id": video_id, "message_count": len(messages), "top_term_count": len(summary["top_terms"])}


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
        {"job_type": target["job_type"], "job_id": target_job_id, "input": target.get("payload", {}), "retry_of": target_job_id},
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


def rebuild_artifacts(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    video_id = params["video_id"]
    video = repo.get_video(video_id) or {"description": ""}
    aggregate = repo.get_chat_aggregate(video_id) or summarize_chat_messages([])
    timestamps = build_timestamp_candidates(aggregate, video.get("description", ""))
    repo.put_video({**video, "video_id": video_id, "timestamps": timestamps})
    repo.put_artifact(video_id, {"artifact_type": "timestamp", "public_url_path": f"/data/latest-video/{video_id}", "content_type": "application/json"})
    if aggregate.get("top_terms"):
        repo.put_artifact(video_id, {"artifact_type": "wordcloud", "public_url_path": f"/data/artifacts/wordcloud/{video_id}.svg", "content_type": "image/svg+xml"})
    return {"video_id": video_id, "timestamp_count": len(timestamps), "wordcloud_available": bool(aggregate.get("top_terms"))}


def _channel_config(repo: Any, params: dict[str, Any]) -> dict[str, Any]:
    if params.get("uploads_playlist_id"):
        return {"channel_id": params.get("channel_id", "manual"), "uploads_playlist_id": params["uploads_playlist_id"]}
    config = repo.get_item("CONFIG#app", "CHANNEL#default")
    if not config:
        raise ValueError("uploads_playlist_id is required when default channel is not configured")
    return config


def _metadata_cursor(repo: Any, channel_id: str) -> dict[str, Any]:
    return repo.get_item(f"CHANNEL#{channel_id}", "CURSOR#metadata") or {}


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


def _read_jsonl(uri: str) -> list[dict[str, Any]]:
    if uri.startswith("s3://"):
        if "/" not in uri[5:]:
            raise ValueError(f"invalid s3 uri: {uri}")
        bucket, key = uri[5:].split("/", 1)
        import boto3

        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
        return _parse_jsonl(body.decode("utf-8"))
    path = pathlib.Path(uri)
    if not path.is_absolute():
        local_root = os.environ.get("DIOPSIDE_LOCAL_ARTIFACT_DIR")
        if local_root:
            path = pathlib.Path(local_root) / uri
    return _parse_jsonl(path.read_text(encoding="utf-8"))


def _parse_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _queue_env_for_job_type(job_type: str) -> str:
    return {
        "metadata_sync": "DIOPSIDE_METADATA_QUEUE_URL",
        "live_status_scan": "DIOPSIDE_METADATA_QUEUE_URL",
        "chat_collect": "DIOPSIDE_CHAT_QUEUE_URL",
        "chat_normalize": "DIOPSIDE_NORMALIZE_QUEUE_URL",
        "rebuild_artifacts": "DIOPSIDE_AGGREGATE_QUEUE_URL",
        "static_export": "DIOPSIDE_STATIC_EXPORT_QUEUE_URL",
        "retry_job": "DIOPSIDE_METADATA_QUEUE_URL",
        "cancel_job": "DIOPSIDE_METADATA_QUEUE_URL",
    }[job_type]


def _enqueue_job(queue_env: str, payload: dict[str, Any], delay_seconds: int = 0) -> str | None:
    queue_url = os.environ.get(queue_env)
    if not queue_url:
        return None
    import boto3

    args: dict[str, Any] = {"QueueUrl": queue_url, "MessageBody": json.dumps(payload, ensure_ascii=False)}
    if delay_seconds:
        args["DelaySeconds"] = delay_seconds
    boto3.client("sqs").send_message(**args)
    return queue_url
