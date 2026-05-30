from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol

try:
    import boto3
    from boto3.dynamodb.conditions import Key
    from botocore.exceptions import ClientError
except Exception:  # pragma: no cover - available in Lambda package.
    boto3 = None
    Key = None
    ClientError = Exception


ITEM_TYPES = {
    "AppConfig",
    "Channel",
    "ChannelRef",
    "ChannelCursor",
    "Video",
    "VideoIndex",
    "VideoTagIndex",
    "VideoMonthIndex",
    "TagSummary",
    "ChatManifest",
    "ChatMessageChunkManifest",
    "ChatAggregate",
    "Artifact",
    "NotificationPlan",
    "StaticExport",
    "Job",
    "JobEvent",
    "QuotaUsage",
    "Lock",
    "Idempotency",
    "RandomBucket",
}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]}"


def _unique_tags(tags: list[str]) -> list[str]:
    return list(dict.fromkeys(tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()))


def tag_id_for_label(label: str) -> str:
    return stable_id("tag", label)


def video_month_key(published_at: str | None) -> str | None:
    if not published_at or len(published_at) < 7:
        return None
    year = published_at[:4]
    month = published_at[5:7]
    if not (year.isdigit() and month.isdigit() and 1 <= int(month) <= 12):
        return None
    return f"{year}{month}"


def channel_ref_item(channel: dict[str, Any]) -> dict[str, Any]:
    channel_id = channel["channel_id"]
    collect_enabled = bool(channel.get("collect_enabled", channel.get("enabled", True)))
    channel_title = channel.get("channel_title") or channel.get("display_name") or channel_id
    priority = int(channel.get("priority", 100))
    stamp = now_iso()
    return {
        "item_type": "ChannelRef",
        "pk": "APP#CHANNELS",
        "sk": f"CH#{channel_id}",
        "channel_id": channel_id,
        "collect_enabled": collect_enabled,
        "enabled": collect_enabled,
        "priority": priority,
        "channel_title": channel_title,
        "display_name": channel.get("display_name") or channel_title,
        "uploads_playlist_id": channel.get("uploads_playlist_id"),
        "notification_enabled": bool(channel.get("notification_enabled", False)),
        "metadata_interval_minutes": channel.get("metadata_interval_minutes"),
        "live_scan_interval_minutes": channel.get("live_scan_interval_minutes"),
        "updated_at": channel.get("updated_at") or stamp,
    }


def video_item(video: dict[str, Any]) -> dict[str, Any]:
    video_id = video["video_id"]
    published_at = video.get("published_at") or video.get("scheduled_start_time") or "1970-01-01T00:00:00Z"
    tags = list(dict.fromkeys(video.get("tags", [])))
    item = {
        **video,
        "item_type": "Video",
        "pk": f"VIDEO#{video_id}",
        "sk": "META",
        "updated_at": now_iso(),
        "tags": tags,
    }
    if item.get("public", True):
        item["gsi1pk"] = "VIDEO#PUBLIC"
        item["gsi1sk"] = f"{published_at}#{video_id}"
    return item


def video_month_index_item(video: dict[str, Any]) -> dict[str, Any] | None:
    published_at = video.get("published_at")
    yyyy_mm_key = video_month_key(published_at)
    if yyyy_mm_key is None:
        return None
    video_id = video["video_id"]
    return {
        "item_type": "VideoMonthIndex",
        "pk": f"VID#{video_id}",
        "sk": f"INDEX#MONTH#{yyyy_mm_key}",
        "video_id": video_id,
        "yyyy_mm": f"{yyyy_mm_key[:4]}-{yyyy_mm_key[4:]}",
        "published_at": published_at,
        "title": video.get("title", ""),
        "thumbnail_url": video.get("thumbnail_url"),
        "duration_sec": video.get("duration_sec"),
        "archive_state": video.get("archive_state") or video.get("live_state") or "archived",
        "detail_path": video.get("detail_path") or f"/api/videos/{video_id}",
        "tags": video.get("tags", []),
        "gsi1pk": f"VIDEO#MONTH#{yyyy_mm_key}",
        "gsi1sk": f"PUB#{published_at}#{video_id}",
        "updated_at": now_iso(),
    }


def random_bucket_item(video: dict[str, Any]) -> dict[str, Any]:
    video_id = video["video_id"]
    bucket_no = int(hashlib.sha256(video_id.encode("utf-8")).hexdigest()[:8], 16) % 10000
    return {
        "item_type": "RandomBucket",
        "pk": "RANDOM#DEFAULT",
        "sk": f"VID#{bucket_no:04d}#{video_id}",
        "bucket_no": bucket_no,
        "video_id": video_id,
        "title": video.get("title", ""),
        "thumbnail_url": video.get("thumbnail_url"),
        "duration_sec": video.get("duration_sec"),
        "published_at": video.get("published_at"),
        "tags": video.get("tags", []),
        "generated_at": now_iso(),
    }


def static_export_item(
    manifest: dict[str, Any],
    *,
    reason: str = "manual",
    manifest_s3_uri: str | None = None,
    public_prefix: str | None = None,
    video_count: int | None = None,
    tag_count: int | None = None,
    generated_job_id: str | None = None,
    uploaded_object_count: int | None = None,
    publish_state: str = "published",
) -> dict[str, Any]:
    exported_at = manifest["generated_at"]
    export_version = manifest["export_version"]
    static_paths = manifest.get("static_paths", {})
    content_hash = static_paths.get("STATIC-006", {}).get("checksum_sha256") or hashlib.sha256(
        repr(manifest).encode("utf-8")
    ).hexdigest()
    item = {
        "item_type": "StaticExport",
        "pk": "EXPORT#public",
        "sk": f"VERSION#{exported_at}",
        "export_id": stable_id("export", export_version),
        "export_version": export_version,
        "exported_at": exported_at,
        "reason": reason,
        "manifest_s3_uri": manifest_s3_uri or "local://latest-manifest.json",
        "public_prefix": public_prefix or f"data/v/{export_version}/public",
        "video_count": video_count if video_count is not None else len(static_paths.get("STATIC-003", {}).get("items", {})),
        "tag_count": tag_count if tag_count is not None else int(manifest.get("tag_count", 0)),
        "schema_versions": _static_export_schema_versions(manifest),
        "content_hash": content_hash,
        "publish_state": publish_state,
        "updated_at": now_iso(),
    }
    if generated_job_id:
        item["generated_job_id"] = generated_job_id
    if uploaded_object_count is not None:
        item["uploaded_object_count"] = uploaded_object_count
    return item


def _static_export_schema_versions(manifest: dict[str, Any]) -> dict[str, str]:
    versions = {"manifest": manifest.get("schema_version", "public-manifest/v1")}
    versions.update(
        {
            "home": "public-home/v1",
            "video_list": "public-video-list/v1",
            "tag_list": "public-tag-list/v1",
            "video_search": "public-video-search/v1",
            "archive_calendar": "public-archive-calendar/v1",
            "video_detail": "public-video-detail/v1",
            "wordcloud": "public-wordcloud/v1",
            "timestamps": "public-timestamp-list/v1",
        }
    )
    return versions


def request_hash(job_type: str, payload: dict[str, Any]) -> str:
    body = json.dumps({"job_type": job_type, "payload": payload}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def idempotency_item(idempotency_key: str, job_id: str, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_type": "Idempotency",
        "pk": f"IDEMP#{idempotency_key}",
        "sk": "META",
        "dedupe_key": idempotency_key,
        "idempotency_key": idempotency_key,
        "entity_id": idempotency_key,
        "first_job_id": job_id,
        "job_id": job_id,
        "job_type": job_type,
        "request_hash": request_hash(job_type, payload),
    }


def lock_item(lock_key: str, owner_job_id: str, ttl_seconds: int, owner_request_id: str | None = None) -> dict[str, Any]:
    now = int(time.time())
    stamp = now_iso()
    item = {
        "item_type": "Lock",
        "pk": f"LOCK#{lock_key}",
        "sk": "META",
        "lock_key": lock_key,
        "owner_job_id": owner_job_id,
        "acquired_at": stamp,
        "expires_at": now + ttl_seconds,
    }
    if owner_request_id:
        item["owner_request_id"] = owner_request_id
    return item


def item_schema_version(item_type: str) -> str:
    return f"ddb-{item_type}-v1"


def item_entity_id(item: dict[str, Any]) -> str:
    for key in [
        "entity_id",
        "video_id",
        "channel_id",
        "tag_id",
        "job_id",
        "export_id",
        "artifact_id",
        "lock_key",
        "quota_date",
        "idempotency_key",
    ]:
        value = item.get(key)
        if value:
            return str(value)
    return f"{item['pk']}#{item['sk']}"


def normalize_item_metadata(item: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = deepcopy(item)
    stamp = now_iso()
    if not normalized.get("schema_version"):
        normalized["schema_version"] = existing.get("schema_version") if existing else item_schema_version(normalized["item_type"])
    if not normalized.get("entity_id"):
        normalized["entity_id"] = existing.get("entity_id") if existing else item_entity_id(normalized)
    if not normalized.get("created_at"):
        normalized["created_at"] = existing.get("created_at") if existing else normalized.get("updated_at", stamp)
    if not normalized.get("updated_at"):
        normalized["updated_at"] = stamp
    return normalized


JOB_STATE_BY_EVENT_TYPE = {
    "queued": "queued",
    "started": "running",
    "completed": "succeeded",
    "succeeded": "succeeded",
    "failed": "failed",
    "retry_requested": "retryable",
    "retry_scheduled": "retryable",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def job_event_name(event_type: str) -> str:
    if "." in event_type:
        return event_type
    aliases = {
        "completed": "succeeded",
        "cancelled": "canceled",
    }
    return f"job.{aliases.get(event_type, event_type)}"


def job_state_after(event_type: str) -> str:
    short_name = event_type.rsplit(".", 1)[-1]
    return JOB_STATE_BY_EVENT_TYPE.get(short_name, short_name)


def job_event_sort_key(item: dict[str, Any]) -> tuple[str, int, str]:
    occurred_at = item.get("occurred_at") or item.get("created_at", "")
    seq = item.get("seq")
    if isinstance(seq, int):
        return (occurred_at, seq, item.get("sk", ""))
    sk = item.get("sk", "")
    if sk.startswith("EVT#"):
        try:
            return (occurred_at, int(sk.removeprefix("EVT#")), sk)
        except ValueError:
            pass
    return (occurred_at, 0, sk)


def next_job_event_seq(events: list[dict[str, Any]]) -> int:
    seqs: list[int] = []
    for item in events:
        seq = item.get("seq")
        if isinstance(seq, int):
            seqs.append(seq)
            continue
        sk = item.get("sk", "")
        if sk.startswith("EVT#"):
            try:
                seqs.append(int(sk.removeprefix("EVT#")))
            except ValueError:
                continue
    return (max(seqs) + 1) if seqs else 1


def job_event_item(job_id: str, event_type: str, details: dict[str, Any] | None, seq: int) -> dict[str, Any]:
    stamp = now_iso()
    payload = details or {}
    state_after = job_state_after(event_type)
    return {
        "item_type": "JobEvent",
        "pk": f"JOB#{job_id}",
        "sk": f"EVT#{seq:08d}",
        "job_id": job_id,
        "seq": seq,
        "event_name": job_event_name(event_type),
        "state_after": state_after,
        "occurred_at": stamp,
        "payload": payload,
        "event_type": event_type,
        "details": payload,
        "created_at": stamp,
    }


def derive_job_state(events: list[dict[str, Any]]) -> str:
    if not events:
        return "queued"
    latest = sorted(events, key=job_event_sort_key)[-1]
    state_after = latest.get("state_after")
    if state_after:
        return str(state_after)
    return job_state_after(str(latest.get("event_type") or latest.get("event_name") or "queued"))


def normalize_job_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in events:
        event = deepcopy(item)
        event_type = str(event.get("event_type") or event.get("event_name", "").rsplit(".", 1)[-1] or "queued")
        if "event_name" not in event:
            event["event_name"] = job_event_name(event_type)
        if "state_after" not in event:
            event["state_after"] = job_state_after(event_type)
        if "payload" not in event:
            event["payload"] = deepcopy(event.get("details", {}))
        if "details" not in event:
            event["details"] = deepcopy(event.get("payload", {}))
        if "event_type" not in event:
            event["event_type"] = event_type
        if "occurred_at" not in event:
            event["occurred_at"] = event.get("created_at")
        normalized.append(event)
    normalized.sort(key=job_event_sort_key)
    return normalized


def job_events_for_job(items: list[dict[str, Any]], job_id: str) -> list[dict[str, Any]]:
    return [item for item in items if item.get("pk") == f"JOB#{job_id}" and item.get("item_type") == "JobEvent"]


class Repository(Protocol):
    def put_item(self, item: dict[str, Any]) -> dict[str, Any]: ...
    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None: ...
    def delete_item(self, pk: str, sk: str) -> None: ...
    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]: ...
    def get_video(self, video_id: str) -> dict[str, Any] | None: ...
    def list_video_month_indexes(self, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]: ...
    def list_tags(self) -> list[dict[str, Any]]: ...
    def rebuild_tag_summaries(self, tags: list[str] | None = None) -> list[dict[str, Any]]: ...
    def list_random_videos(self, limit: int = 1000) -> list[dict[str, Any]]: ...
    def record_static_export(self, manifest: dict[str, Any], **kwargs: Any) -> dict[str, Any]: ...
    def list_static_exports(self, limit: int = 20) -> list[dict[str, Any]]: ...
    def put_video(self, video: dict[str, Any]) -> dict[str, Any]: ...
    def update_video_tags(self, video_id: str, *, add_tags: list[str] | None = None, remove_tags: list[str] | None = None, replace_tags: list[str] | None = None) -> dict[str, Any]: ...
    def put_chat_aggregate(self, video_id: str, aggregate: dict[str, Any]) -> dict[str, Any]: ...
    def get_chat_aggregate(self, video_id: str) -> dict[str, Any] | None: ...
    def put_artifact(self, video_id: str, artifact: dict[str, Any]) -> dict[str, Any]: ...
    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]: ...
    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None: ...
    def put_channel(self, channel: dict[str, Any]) -> dict[str, Any]: ...
    def record_quota_usage(
        self,
        method: str,
        units: int,
        details: dict[str, Any] | None = None,
        *,
        channel_id: str | None = None,
        video_count: int | None = None,
        job_id: str | None = None,
    ) -> dict[str, Any]: ...
    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]: ...
    def get_job(self, job_id: str) -> dict[str, Any] | None: ...
    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def acquire_lock(self, lock_key: str, owner_job_id: str, ttl_seconds: int = 900, owner_request_id: str | None = None) -> dict[str, Any] | None: ...
    def release_lock(self, lock_key: str, owner_job_id: str) -> bool: ...
    def list_chat_chunks(self, video_id: str) -> list[dict[str, Any]]: ...
    def list_channels(self) -> list[dict[str, Any]]: ...
    def list_quota_usage(self, limit: int = 100) -> list[dict[str, Any]]: ...


@dataclass
class MemoryRepository:
    items: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    idempotency_index: dict[str, str] = field(default_factory=dict)

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if item.get("item_type") not in ITEM_TYPES:
            raise ValueError(f"unsupported item_type: {item.get('item_type')}")
        normalized = normalize_item_metadata(item, self.items.get((item["pk"], item["sk"])))
        self.items[(normalized["pk"], normalized["sk"])] = deepcopy(normalized)
        return deepcopy(normalized)

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self.items.get((pk, sk))
        return deepcopy(item) if item else None

    def delete_item(self, pk: str, sk: str) -> None:
        self.items.pop((pk, sk), None)

    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]:
        videos = [item for item in self.items.values() if item.get("item_type") == "Video" and item.get("public", True)]
        videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(videos[:limit])

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        return self.get_item(f"VIDEO#{video_id}", "META")

    def list_video_month_indexes(self, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]:
        indexes = [item for item in self.items.values() if item.get("item_type") == "VideoMonthIndex"]
        if not indexes:
            indexes = [item for video in self.list_videos(10000) if (item := video_month_index_item(video))]
        if year is not None:
            indexes = [item for item in indexes if item.get("yyyy_mm", "").startswith(f"{year:04d}-")]
        if month is not None:
            indexes = [item for item in indexes if item.get("yyyy_mm", "").endswith(f"-{month:02d}")]
        indexes.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(indexes)

    def list_tags(self) -> list[dict[str, Any]]:
        summaries = [item for item in self.items.values() if item.get("item_type") == "TagSummary"]
        if summaries:
            summaries = [item for item in summaries if item.get("public_visible", True)]
            summaries.sort(key=lambda item: (int(item.get("sort_order", 0)), item.get("label", "")))
            return [
                {
                    "tag_id": item["tag_id"],
                    "label": item["label"],
                    "video_count": int(item.get("video_count", 0)),
                    "category": item.get("category", "auto"),
                    "aliases": item.get("aliases", []),
                    "latest_video_id": item.get("latest_video_id"),
                    "latest_video_at": item.get("latest_video_at"),
                    "sort_order": int(item.get("sort_order", 0)),
                    "public_visible": bool(item.get("public_visible", True)),
                }
                for item in summaries
            ]
        return self._dynamic_tag_summaries()

    def _dynamic_tag_summaries(self) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for video in self.list_videos(10000):
            for tag in video.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        return [
            {
                "tag_id": tag_id_for_label(tag),
                "label": tag,
                "video_count": count,
                "category": "auto",
                "aliases": [],
                "public_visible": True,
                "sort_order": 0,
            }
            for tag, count in sorted(counts.items())
        ]

    def rebuild_tag_summaries(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        target_tags = set(_unique_tags(tags or []))
        if not target_tags:
            target_tags = {tag for video in self.list_videos(10000) for tag in video.get("tags", [])}
        summaries = []
        for tag in sorted(target_tags):
            videos = [video for video in self.list_videos(10000) if tag in video.get("tags", [])]
            videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
            existing = self.get_item(f"TAG#{tag_id_for_label(tag)}", "META") or {}
            latest = videos[0] if videos else {}
            item = {
                **existing,
                "item_type": "TagSummary",
                "pk": f"TAG#{tag_id_for_label(tag)}",
                "sk": "META",
                "tag_id": tag_id_for_label(tag),
                "label": existing.get("label", tag),
                "category": existing.get("category", "auto"),
                "aliases": existing.get("aliases", []),
                "video_count": len(videos),
                "latest_video_id": latest.get("video_id"),
                "latest_video_at": latest.get("published_at"),
                "sort_order": int(existing.get("sort_order", 0)),
                "public_visible": len(videos) > 0 and bool(existing.get("public_visible", True)),
                "gsi2pk": "TAG#SUMMARY",
                "gsi2sk": f"{int(existing.get('sort_order', 0)):08d}#{tag}",
                "updated_at": now_iso(),
            }
            summaries.append(self.put_item(item))
        return summaries

    def put_video(self, video: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_video(video["video_id"])
        previous_tags = set(existing.get("tags", [])) if existing else set()
        previous_month_key = video_month_key(existing.get("published_at")) if existing else None
        item = self.put_item(video_item(video))
        current_month_index = video_month_index_item(item)
        current_month_key = current_month_index["sk"].replace("INDEX#MONTH#", "") if current_month_index else None
        if previous_month_key and previous_month_key != current_month_key:
            self.delete_item(f"VID#{item['video_id']}", f"INDEX#MONTH#{previous_month_key}")
        if item.get("public", True) and current_month_index:
            self.put_item(current_month_index)
        elif current_month_key:
            self.delete_item(f"VID#{item['video_id']}", f"INDEX#MONTH#{current_month_key}")
        current_tags = set(item.get("tags", []))
        for tag in previous_tags - current_tags:
            self.delete_item(f"TAG#{tag}", f"VIDEO#{item['video_id']}")
        for tag in item.get("tags", []):
            self.put_item(
                {
                    "item_type": "VideoTagIndex",
                    "pk": f"TAG#{tag}",
                    "sk": f"VIDEO#{item['video_id']}",
                    "video_id": item["video_id"],
                    "tag": tag,
                    "gsi2pk": f"TAG#{tag}",
                    "gsi2sk": item.get("published_at", ""),
                    "updated_at": now_iso(),
                }
            )
        random_bucket = random_bucket_item(item)
        if item.get("public", True):
            self.put_item(random_bucket)
        else:
            self.delete_item(random_bucket["pk"], random_bucket["sk"])
        self.rebuild_tag_summaries(sorted(previous_tags | current_tags))
        return item

    def list_random_videos(self, limit: int = 1000) -> list[dict[str, Any]]:
        items = [item for (pk, sk), item in self.items.items() if pk == "RANDOM#DEFAULT" and sk.startswith("VID#") and item.get("item_type") == "RandomBucket"]
        items.sort(key=lambda item: item.get("sk", ""))
        return deepcopy(items[:limit])

    def record_static_export(self, manifest: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        item = static_export_item(manifest, **kwargs)
        return self.put_item(item)

    def list_static_exports(self, limit: int = 20) -> list[dict[str, Any]]:
        exports = [item for (pk, sk), item in self.items.items() if pk == "EXPORT#public" and sk.startswith("VERSION#") and item.get("item_type") == "StaticExport"]
        exports.sort(key=lambda item: item.get("exported_at", ""), reverse=True)
        return deepcopy(exports[:limit])

    def update_video_tags(self, video_id: str, *, add_tags: list[str] | None = None, remove_tags: list[str] | None = None, replace_tags: list[str] | None = None) -> dict[str, Any]:
        video = self.get_video(video_id)
        if not video:
            raise KeyError(video_id)
        if replace_tags is not None:
            tags = _unique_tags(replace_tags)
        else:
            remove = set(remove_tags or [])
            tags = [tag for tag in video.get("tags", []) if tag not in remove]
            tags.extend(add_tags or [])
            tags = _unique_tags(tags)
        stamp = now_iso()
        manual = {
            "add_tags": _unique_tags(add_tags or []),
            "remove_tags": _unique_tags(remove_tags or []),
            **({"replace_tags": _unique_tags(replace_tags)} if replace_tags is not None else {}),
            "updated_at": stamp,
        }
        return self.put_video({**video, "tags": tags, "manual_tag_correction": manual, "manual_tags_updated_at": stamp})

    def put_chat_aggregate(self, video_id: str, aggregate: dict[str, Any]) -> dict[str, Any]:
        return self.put_item({"item_type": "ChatAggregate", "pk": f"VIDEO#{video_id}", "sk": "CHAT#AGGREGATE", "video_id": video_id, **aggregate, "updated_at": now_iso()})

    def get_chat_aggregate(self, video_id: str) -> dict[str, Any] | None:
        return self.get_item(f"VIDEO#{video_id}", "CHAT#AGGREGATE")

    def put_artifact(self, video_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
        artifact_type = artifact["artifact_type"]
        return self.put_item({"item_type": "Artifact", "pk": f"VIDEO#{video_id}", "sk": f"ARTIFACT#{artifact_type}", "video_id": video_id, **artifact, "updated_at": now_iso()})

    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]:
        prefix = f"VIDEO#{video_id}"
        artifacts = [item for (pk, sk), item in self.items.items() if pk == prefix and sk.startswith("ARTIFACT#")]
        return deepcopy(artifacts)

    def record_quota_usage(
        self,
        method: str,
        units: int,
        details: dict[str, Any] | None = None,
        *,
        channel_id: str | None = None,
        video_count: int | None = None,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        stamp = now_iso()
        usage_details = details or {}
        normalized_channel_id = channel_id if channel_id is not None else usage_details.get("channel_id")
        normalized_video_count = video_count if video_count is not None else usage_details.get("video_count")
        normalized_job_id = job_id if job_id is not None else usage_details.get("job_id")
        return self.put_item(
            {
                "item_type": "QuotaUsage",
                "pk": f"QUOTA#{stamp[:10]}",
                "sk": f"{stamp}#{method}#{uuid.uuid4().hex}",
                "method": method,
                "units": units,
                "channel_id": normalized_channel_id,
                "video_count": normalized_video_count,
                "job_id": normalized_job_id,
                "details": {**usage_details, "channel_id": normalized_channel_id, "video_count": normalized_video_count, "job_id": normalized_job_id},
                "record_type": "call",
                "created_at": stamp,
                "gsi3pk": "QUOTA#ALL",
                "gsi3sk": f"{stamp}#{method}",
            }
        )

    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]:
        if idempotency_key in self.idempotency_index:
            existing = self.get_job(self.idempotency_index[idempotency_key])
            if existing:
                return existing, True
        idempotency = self.get_item(f"IDEMP#{idempotency_key}", "META")
        if idempotency:
            existing = self.get_job(str(idempotency.get("first_job_id") or idempotency.get("job_id")))
            if existing:
                self.idempotency_index[idempotency_key] = existing["job_id"]
                return existing, True
        stamp = now_iso()
        job_id = stable_id("job", idempotency_key)
        item = {
            "item_type": "Job",
            "pk": f"JOB#{job_id}",
            "sk": "META",
            "job_id": job_id,
            "job_type": job_type,
            "idempotency_key": idempotency_key,
            "payload": payload,
            "derived_state": "queued",
            "created_at": stamp,
            "updated_at": stamp,
            "gsi3pk": "JOB#ALL",
            "gsi3sk": f"{stamp}#{job_type}#{job_id}",
        }
        self.put_item(item)
        self.put_item(idempotency_item(idempotency_key, job_id, job_type, payload))
        self.idempotency_index[idempotency_key] = job_id
        self.append_job_event(job_id, "queued", {"job_type": job_type})
        return self.get_job(job_id) or item, False

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_item(f"JOB#{job_id}", "META")
        if not job:
            return None
        events = normalize_job_events(job_events_for_job(list(self.items.values()), job_id))
        job["events"] = deepcopy(events)
        job["derived_state"] = derive_job_state(events)
        return job

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        jobs = [self.get_job(item["job_id"]) for item in self.items.values() if item.get("item_type") == "Job"]
        present = [job for job in jobs if job]
        present.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(present[:limit])

    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        events = job_events_for_job(list(self.items.values()), job_id)
        return self.put_item(job_event_item(job_id, event_type, details, next_job_event_seq(events)))

    def acquire_lock(self, lock_key: str, owner_job_id: str, ttl_seconds: int = 900, owner_request_id: str | None = None) -> dict[str, Any] | None:
        existing = self.get_item(f"LOCK#{lock_key}", "META")
        now = int(time.time())
        if existing and int(existing.get("expires_at", 0)) > now and existing.get("owner_job_id") != owner_job_id:
            return None
        return self.put_item(lock_item(lock_key, owner_job_id, ttl_seconds, owner_request_id))

    def release_lock(self, lock_key: str, owner_job_id: str) -> bool:
        existing = self.get_item(f"LOCK#{lock_key}", "META")
        if not existing or existing.get("owner_job_id") != owner_job_id:
            return False
        self.delete_item(f"LOCK#{lock_key}", "META")
        return True

    def list_chat_chunks(self, video_id: str) -> list[dict[str, Any]]:
        chunks = [item for (pk, _), item in self.items.items() if pk == f"VIDEO#{video_id}" and item.get("item_type") == "ChatMessageChunkManifest"]
        chunks.sort(key=lambda item: item.get("sk", ""))
        return deepcopy(chunks)

    def list_channels(self) -> list[dict[str, Any]]:
        refs = [item for item in self.items.values() if item.get("item_type") == "ChannelRef"]
        if refs:
            refs.sort(key=lambda item: (int(item.get("priority", 100)), item.get("channel_id", "")))
            return deepcopy(refs)
        channels = [item for item in self.items.values() if item.get("item_type") == "Channel"]
        channels.sort(key=lambda item: item.get("channel_id", ""))
        return deepcopy(channels)

    def put_channel(self, channel: dict[str, Any]) -> dict[str, Any]:
        channel_id = channel["channel_id"]
        stamp = now_iso()
        existing = self.get_item(f"CHANNEL#{channel_id}", "META") or {}
        item = {
            **existing,
            **channel,
            "item_type": "Channel",
            "pk": f"CHANNEL#{channel_id}",
            "sk": "META",
            "channel_id": channel_id,
            "updated_at": stamp,
        }
        if "collect_enabled" not in item:
            item["collect_enabled"] = bool(item.get("enabled", True))
        if "channel_title" not in item:
            item["channel_title"] = item.get("display_name") or channel_id
        if "priority" not in item:
            item["priority"] = 100
        if not item.get("created_at"):
            item["created_at"] = stamp
        saved = self.put_item(item)
        self.put_item(channel_ref_item(saved))
        return saved

    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None:
        if ":" in artifact_id:
            video_id, artifact_type = artifact_id.split(":", 1)
            return self.get_item(f"VIDEO#{video_id}", f"ARTIFACT#{artifact_type}")
        for item in self.items.values():
            if item.get("item_type") == "Artifact" and item.get("artifact_id") == artifact_id:
                return deepcopy(item)
        return None

    def list_quota_usage(self, limit: int = 100) -> list[dict[str, Any]]:
        usage = [item for item in self.items.values() if item.get("item_type") == "QuotaUsage" and not item.get("sk", "").startswith("METHOD#")]
        usage.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(usage[:limit])


class DynamoRepository(MemoryRepository):
    """DynamoDB adapter with a memory-compatible surface for tests and Lambda.

    The implementation intentionally uses the high-level Table resource so the
    stored document shape matches the item schema documented in README.
    """

    def __init__(self, table_name: str | None = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoRepository")
        self.table_name = table_name or os.environ["DIOPSIDE_TABLE_NAME"]
        self.table = boto3.resource("dynamodb").Table(self.table_name)
        self.idempotency_index = {}

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if item.get("item_type") not in ITEM_TYPES:
            raise ValueError(f"unsupported item_type: {item.get('item_type')}")
        existing = self.get_item(item["pk"], item["sk"])
        normalized = normalize_item_metadata(item, existing)
        self.table.put_item(Item=normalized)
        return deepcopy(normalized)

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key={"pk": pk, "sk": sk}).get("Item")
        return deepcopy(item) if item else None

    def delete_item(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})

    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]:
        job_id = stable_id("job", idempotency_key)
        stamp = now_iso()
        item = {
            "item_type": "Job",
            "pk": f"JOB#{job_id}",
            "sk": "META",
            "job_id": job_id,
            "job_type": job_type,
            "idempotency_key": idempotency_key,
            "payload": payload,
            "derived_state": "queued",
            "created_at": stamp,
            "updated_at": stamp,
            "gsi3pk": "JOB#ALL",
            "gsi3sk": f"{stamp}#{job_type}#{job_id}",
        }
        item = normalize_item_metadata(item)
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise
            existing = self.get_job(job_id)
            if existing:
                self.put_item(idempotency_item(idempotency_key, job_id, job_type, payload))
                return existing, True
            raise
        self.put_item(idempotency_item(idempotency_key, job_id, job_type, payload))
        self.append_job_event(job_id, "queued", {"job_type": job_type})
        return self.get_job(job_id) or item, False

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_item(f"JOB#{job_id}", "META")
        if not job:
            return None
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"JOB#{job_id}"))
        events = normalize_job_events([item for item in response.get("Items", []) if item.get("item_type") == "JobEvent"])
        job["events"] = deepcopy(events)
        job["derived_state"] = derive_job_state(events)
        return job

    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"JOB#{job_id}"))
        events = [item for item in response.get("Items", []) if item.get("item_type") == "JobEvent"]
        return self.put_item(job_event_item(job_id, event_type, details, next_job_event_seq(events)))

    def acquire_lock(self, lock_key: str, owner_job_id: str, ttl_seconds: int = 900, owner_request_id: str | None = None) -> dict[str, Any] | None:
        item = normalize_item_metadata(lock_item(lock_key, owner_job_id, ttl_seconds, owner_request_id))
        now = int(time.time())
        try:
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(pk) OR expires_at < :now OR owner_job_id = :owner_job_id",
                ExpressionAttributeValues={":now": now, ":owner_job_id": owner_job_id},
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return None
            raise
        return deepcopy(item)

    def release_lock(self, lock_key: str, owner_job_id: str) -> bool:
        try:
            self.table.delete_item(
                Key={"pk": f"LOCK#{lock_key}", "sk": "META"},
                ConditionExpression="owner_job_id = :owner_job_id",
                ExpressionAttributeValues={":owner_job_id": owner_job_id},
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        videos = [
            item
            for item in self._query_all(
                IndexName="by_public_date",
                KeyConditionExpression=Key("gsi1pk").eq("VIDEO#PUBLIC"),
                ScanIndexForward=False,
                Limit=limit,
            )
            if item.get("item_type") == "Video" and item.get("public", True)
        ]
        return deepcopy(videos[:limit])

    def list_video_month_indexes(self, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        if year is None:
            return super().list_video_month_indexes(year=year, month=month)
        months = [month] if month is not None else list(range(1, 13))
        items: list[dict[str, Any]] = []
        for month_value in months:
            yyyy_mm_key = f"{year:04d}{month_value:02d}"
            items.extend(
                self._query_all(
                    IndexName="by_public_date",
                    KeyConditionExpression=Key("gsi1pk").eq(f"VIDEO#MONTH#{yyyy_mm_key}"),
                    ScanIndexForward=False,
                    Limit=10000,
                )
            )
        items = [item for item in items if item.get("item_type") == "VideoMonthIndex"]
        if not items:
            return super().list_video_month_indexes(year=year, month=month)
        items.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(items)

    def list_random_videos(self, limit: int = 1000) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        items = self._query_all(
            KeyConditionExpression=Key("pk").eq("RANDOM#DEFAULT") & Key("sk").begins_with("VID#"),
            Limit=limit,
        )
        items = [item for item in items if item.get("item_type") == "RandomBucket"]
        items.sort(key=lambda item: item.get("sk", ""))
        return deepcopy(items[:limit])

    def list_tags(self) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        summaries = self._query_all(
            IndexName="by_tag",
            KeyConditionExpression=Key("gsi2pk").eq("TAG#SUMMARY"),
            Limit=10000,
        )
        summaries = [item for item in summaries if item.get("item_type") == "TagSummary"]
        if summaries:
            summaries = [item for item in summaries if item.get("public_visible", True)]
            summaries.sort(key=lambda item: (int(item.get("sort_order", 0)), item.get("label", "")))
            return deepcopy(summaries)
        return super().list_tags()

    def list_static_exports(self, limit: int = 20) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        items = self._query_all(
            KeyConditionExpression=Key("pk").eq("EXPORT#public") & Key("sk").begins_with("VERSION#"),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = [item for item in items if item.get("item_type") == "StaticExport"]
        items.sort(key=lambda item: item.get("exported_at", ""), reverse=True)
        return deepcopy(items[:limit])

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        job_items = self._query_all(
            IndexName="by_work_queue",
            KeyConditionExpression=Key("gsi3pk").eq("JOB#ALL"),
            ScanIndexForward=False,
            Limit=limit,
        )
        jobs = [self.get_job(item["job_id"]) for item in job_items if item.get("item_type") == "Job"]
        jobs = [job for job in jobs if job]
        jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(jobs[:limit])

    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"VIDEO#{video_id}"))
        return [item for item in response.get("Items", []) if item.get("item_type") == "Artifact"]

    def list_chat_chunks(self, video_id: str) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"VIDEO#{video_id}"))
        chunks = [item for item in response.get("Items", []) if item.get("item_type") == "ChatMessageChunkManifest"]
        chunks.sort(key=lambda item: item.get("sk", ""))
        return deepcopy(chunks)

    def list_channels(self) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        refs = self._query_all(
            KeyConditionExpression=Key("pk").eq("APP#CHANNELS") & Key("sk").begins_with("CH#"),
            Limit=1000,
        )
        refs = [item for item in refs if item.get("item_type") == "ChannelRef"]
        if refs:
            refs.sort(key=lambda item: (int(item.get("priority", 100)), item.get("channel_id", "")))
            return deepcopy(refs)
        return super().list_channels()

    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None:
        if ":" in artifact_id:
            video_id, artifact_type = artifact_id.split(":", 1)
            return self.get_item(f"VIDEO#{video_id}", f"ARTIFACT#{artifact_type}")
        return None

    def list_quota_usage(self, limit: int = 100) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        usage = [
            item
            for item in self._query_all(
                IndexName="by_work_queue",
                KeyConditionExpression=Key("gsi3pk").eq("QUOTA#ALL"),
                ScanIndexForward=False,
                Limit=limit,
            )
            if item.get("item_type") == "QuotaUsage" and not item.get("sk", "").startswith("METHOD#")
        ]
        return deepcopy(usage[:limit])

    def _query_all(self, **kwargs: Any) -> list[dict[str, Any]]:
        limit = int(kwargs.pop("Limit", 100))
        items: list[dict[str, Any]] = []
        request = {**kwargs, "Limit": limit}
        while len(items) < limit:
            response = self.table.query(**request)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            request["ExclusiveStartKey"] = last_key
            request["Limit"] = max(1, limit - len(items))
        return items[:limit]
