from __future__ import annotations

import json
import os
import re
import socket
import urllib.parse
import urllib.error
import urllib.request
from typing import Any


class YouTubeClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, reason: str | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason
        self.retryable = retryable


class YouTubeClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://www.googleapis.com/youtube/v3") -> None:
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY") or os.environ.get("DIOPSIDE_YOUTUBE_API_KEY")
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY or DIOPSIDE_YOUTUBE_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def playlist_items(self, playlist_id: str, page_token: str | None = None, max_results: int = 50) -> dict[str, Any]:
        return self._get("playlistItems", {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": str(max_results), **({"pageToken": page_token} if page_token else {})})

    def videos(self, video_ids: list[str]) -> dict[str, Any]:
        return self._get("videos", {"part": "snippet,contentDetails,liveStreamingDetails,statistics,status", "id": ",".join(video_ids), "maxResults": "50"})

    def channels(self, channel_ids: list[str]) -> dict[str, Any]:
        return self._get("channels", {"part": "snippet,contentDetails", "id": ",".join(channel_ids), "maxResults": "50"})

    def live_chat_messages(self, live_chat_id: str, page_token: str | None = None) -> dict[str, Any]:
        params = {"part": "snippet,authorDetails", "liveChatId": live_chat_id, "maxResults": "2000"}
        if page_token:
            params["pageToken"] = page_token
        return self._get("liveChat/messages", params)

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode({**params, "key": self.api_key})
        url = f"{self.base_url}/{path}?{query}"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise _http_error(exc) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise YouTubeClientError("YouTube API network error", reason="network_error", retryable=True) from exc
        except json.JSONDecodeError as exc:
            raise YouTubeClientError("YouTube API returned malformed JSON", reason="malformed_response", retryable=False) from exc
        if not isinstance(payload, dict):
            raise YouTubeClientError("YouTube API returned malformed response", reason="malformed_response", retryable=False)
        return payload


def _http_error(exc: urllib.error.HTTPError) -> YouTubeClientError:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    errors = error.get("errors", []) if isinstance(error, dict) else []
    reason = next((item.get("reason") for item in errors if isinstance(item, dict) and item.get("reason")), None)
    reason = reason or (error.get("status") if isinstance(error, dict) else None) or f"http_{exc.code}"
    retryable = reason in {"quotaExceeded", "rateLimitExceeded", "backendError"} or exc.code in {429, 500, 502, 503, 504}
    message = error.get("message") if isinstance(error, dict) else None
    return YouTubeClientError(message or f"YouTube API returned HTTP {exc.code}", status_code=exc.code, reason=reason, retryable=retryable)


def parse_iso8601_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = re.fullmatch(r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?)?", value)
    if not match:
        return None
    return int(match.group("days") or 0) * 86400 + int(match.group("h") or 0) * 3600 + int(match.group("m") or 0) * 60 + int(match.group("s") or 0)


def normalize_video_resource(resource: dict[str, Any]) -> dict[str, Any]:
    snippet = resource.get("snippet", {})
    content = resource.get("contentDetails", {})
    live = resource.get("liveStreamingDetails", {})
    statistics = resource.get("statistics", {})
    status = resource.get("status", {})
    thumbnails = snippet.get("thumbnails", {})
    thumb = thumbnails.get("maxres") or thumbnails.get("standard") or thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}
    tags = snippet.get("tags") or []
    return {
        "video_id": resource["id"],
        "channel_id": snippet.get("channelId"),
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "published_at": snippet.get("publishedAt"),
        "scheduled_start_time": live.get("scheduledStartTime"),
        "actual_start_time": live.get("actualStartTime"),
        "actual_end_time": live.get("actualEndTime"),
        "live_chat_id": live.get("activeLiveChatId"),
        "duration_sec": parse_iso8601_duration(content.get("duration")),
        "thumbnail_url": thumb.get("url"),
        "youtube_url": f"https://www.youtube.com/watch?v={resource['id']}",
        "statistics": {k: int(v) for k, v in statistics.items() if str(v).isdigit()},
        "privacy_status": status.get("privacyStatus"),
        "live_broadcast_content": snippet.get("liveBroadcastContent"),
        "live_state": _live_state(snippet.get("liveBroadcastContent"), live),
        "tags": tags,
        "public": status.get("privacyStatus", "public") == "public",
    }


def normalize_channel_resource(resource: dict[str, Any]) -> dict[str, Any]:
    snippet = resource.get("snippet", {})
    content = resource.get("contentDetails", {})
    related = content.get("relatedPlaylists", {})
    return {
        "channel_id": resource["id"],
        "channel_title": snippet.get("title") or resource["id"],
        "display_name": snippet.get("title") or resource["id"],
        "description": snippet.get("description", ""),
        "published_at": snippet.get("publishedAt"),
        "custom_url": snippet.get("customUrl"),
        "uploads_playlist_id": related.get("uploads"),
        "collect_enabled": True,
        "enabled": True,
    }


def _live_state(content_state: str | None, live: dict[str, Any]) -> str:
    if content_state == "live":
        return "live"
    if content_state == "upcoming" or live.get("scheduledStartTime") and not live.get("actualEndTime"):
        return "upcoming"
    if live.get("actualEndTime"):
        return "archived"
    return "archived"


def extract_replay_actions_from_initial_data(initial_data: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if "replayChatItemAction" in value:
                actions.append(value)
                return
            if "addChatItemAction" in value or "addLiveChatTickerItemAction" in value:
                actions.append(value)
                return
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(initial_data)
    return actions


def extract_replay_continuations_from_initial_data(initial_data: dict[str, Any]) -> list[dict[str, Any]]:
    continuations: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(token: Any, source: str, timeout_ms: Any = None) -> None:
        if not token or not isinstance(token, str) or token in seen:
            return
        seen.add(token)
        continuations.append(
            {
                "token": token,
                "source": source,
                "timeout_ms": _int_or_none(timeout_ms),
            }
        )

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key in ("reloadContinuationData", "timedContinuationData", "invalidationContinuationData", "liveChatReplayContinuationData"):
                continuation = value.get(key)
                if isinstance(continuation, dict):
                    add(continuation.get("continuation"), key, continuation.get("timeoutMs"))
            command = value.get("continuationCommand")
            if isinstance(command, dict):
                add(command.get("token"), "continuationCommand")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(initial_data)
    return continuations


def extract_initial_data_from_watch_html(html: str) -> dict[str, Any]:
    match = re.search(r"ytInitialData\s*=\s*\{", html)
    if not match:
        raise ValueError("ytInitialData was not found in public watch html")
    start = match.end() - 1
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start : index + 1])
    raise ValueError("ytInitialData JSON was not closed")


def fetch_public_replay_actions(video_id: str) -> list[dict[str, Any]]:
    url = f"https://www.youtube.com/watch?{urllib.parse.urlencode({'v': video_id})}"
    with urllib.request.urlopen(url, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")
    return extract_replay_actions_from_initial_data(extract_initial_data_from_watch_html(html))


def fetch_public_replay_continuation(continuation_token: str) -> dict[str, Any]:
    url = "https://www.youtube.com/youtubei/v1/live_chat/get_live_chat_replay?prettyPrint=false"
    body = json.dumps(
        {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20260530.00.00",
                }
            },
            "continuation": continuation_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("YouTube replay continuation returned malformed response")
    return payload


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
