from __future__ import annotations

import hashlib
import os
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol

try:
    import boto3
    from boto3.dynamodb.conditions import Key
except Exception:  # pragma: no cover - available in Lambda package.
    boto3 = None
    Key = None


ITEM_TYPES = {
    "AppConfig",
    "Channel",
    "ChannelCursor",
    "Video",
    "VideoIndex",
    "VideoTagIndex",
    "ChatManifest",
    "ChatMessageChunkManifest",
    "ChatAggregate",
    "Artifact",
    "Job",
    "JobEvent",
    "QuotaUsage",
    "Lock",
}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]}"


def video_item(video: dict[str, Any]) -> dict[str, Any]:
    video_id = video["video_id"]
    published_at = video.get("published_at") or video.get("scheduled_start_time") or "1970-01-01T00:00:00Z"
    tags = list(dict.fromkeys(video.get("tags", [])))
    item = {
        **video,
        "item_type": "Video",
        "pk": f"VIDEO#{video_id}",
        "sk": "META",
        "gsi1pk": "VIDEO#PUBLIC",
        "gsi1sk": f"{published_at}#{video_id}",
        "updated_at": now_iso(),
        "tags": tags,
    }
    return item


class Repository(Protocol):
    def put_item(self, item: dict[str, Any]) -> dict[str, Any]: ...
    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None: ...
    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]: ...
    def get_video(self, video_id: str) -> dict[str, Any] | None: ...
    def list_tags(self) -> list[dict[str, Any]]: ...
    def put_video(self, video: dict[str, Any]) -> dict[str, Any]: ...
    def put_chat_aggregate(self, video_id: str, aggregate: dict[str, Any]) -> dict[str, Any]: ...
    def get_chat_aggregate(self, video_id: str) -> dict[str, Any] | None: ...
    def put_artifact(self, video_id: str, artifact: dict[str, Any]) -> dict[str, Any]: ...
    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]: ...
    def record_quota_usage(self, method: str, units: int, details: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]: ...
    def get_job(self, job_id: str) -> dict[str, Any] | None: ...
    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]: ...


@dataclass
class MemoryRepository:
    items: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    idempotency_index: dict[str, str] = field(default_factory=dict)

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if item.get("item_type") not in ITEM_TYPES:
            raise ValueError(f"unsupported item_type: {item.get('item_type')}")
        self.items[(item["pk"], item["sk"])] = deepcopy(item)
        return deepcopy(item)

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self.items.get((pk, sk))
        return deepcopy(item) if item else None

    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]:
        videos = [item for item in self.items.values() if item.get("item_type") == "Video" and item.get("public", True)]
        videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(videos[:limit])

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        return self.get_item(f"VIDEO#{video_id}", "META")

    def list_tags(self) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for video in self.list_videos(10000):
            for tag in video.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        return [{"tag_id": stable_id("tag", tag), "label": tag, "video_count": count, "category": "auto"} for tag, count in sorted(counts.items())]

    def put_video(self, video: dict[str, Any]) -> dict[str, Any]:
        item = self.put_item(video_item(video))
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
        return item

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

    def record_quota_usage(self, method: str, units: int, details: dict[str, Any] | None = None) -> dict[str, Any]:
        stamp = now_iso()
        return self.put_item({"item_type": "QuotaUsage", "pk": f"QUOTA#{stamp[:10]}", "sk": f"{stamp}#{method}#{uuid.uuid4().hex}", "method": method, "units": units, "details": details or {}, "created_at": stamp})

    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]:
        if idempotency_key in self.idempotency_index:
            existing = self.get_job(self.idempotency_index[idempotency_key])
            if existing:
                return existing, True
        stamp = now_iso()
        job_id = stable_id("job", f"{job_type}:{idempotency_key}")
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
            "gsi3pk": f"JOB#{job_type}",
            "gsi3sk": stamp,
        }
        self.put_item(item)
        self.idempotency_index[idempotency_key] = job_id
        self.append_job_event(job_id, "queued", {"job_type": job_type})
        return self.get_job(job_id) or item, False

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_item(f"JOB#{job_id}", "META")
        if not job:
            return None
        events = [item for (pk, _), item in self.items.items() if pk == f"JOB#{job_id}" and item.get("item_type") == "JobEvent"]
        events.sort(key=lambda item: item["created_at"])
        job["events"] = deepcopy(events)
        if events:
            terminal = {"completed": "succeeded", "failed": "failed", "cancelled": "cancelled"}
            job["derived_state"] = terminal.get(events[-1]["event_type"], events[-1]["event_type"])
        return job

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        jobs = [self.get_job(item["job_id"]) for item in self.items.values() if item.get("item_type") == "Job"]
        present = [job for job in jobs if job]
        present.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(present[:limit])

    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        stamp = now_iso()
        return self.put_item({"item_type": "JobEvent", "pk": f"JOB#{job_id}", "sk": f"EVENT#{stamp}#{uuid.uuid4().hex}", "job_id": job_id, "event_type": event_type, "details": details or {}, "created_at": stamp})


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
        self.table.put_item(Item=item)
        return deepcopy(item)

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key={"pk": pk, "sk": sk}).get("Item")
        return deepcopy(item) if item else None

    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]:
        response = self.table.scan(Limit=limit * 2)
        videos = [item for item in response.get("Items", []) if item.get("item_type") == "Video" and item.get("public", True)]
        videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(videos[:limit])

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        response = self.table.scan(Limit=limit * 5)
        jobs = [item for item in response.get("Items", []) if item.get("item_type") == "Job"]
        jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(jobs[:limit])

    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"VIDEO#{video_id}"))
        return [item for item in response.get("Items", []) if item.get("item_type") == "Artifact"]
