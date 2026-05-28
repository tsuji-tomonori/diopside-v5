from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any


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

    def live_chat_messages(self, live_chat_id: str, page_token: str | None = None) -> dict[str, Any]:
        params = {"part": "snippet,authorDetails", "liveChatId": live_chat_id, "maxResults": "2000"}
        if page_token:
            params["pageToken"] = page_token
        return self._get("liveChat/messages", params)

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode({**params, "key": self.api_key})
        with urllib.request.urlopen(f"{self.base_url}/{path}?{query}", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))


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


def _live_state(content_state: str | None, live: dict[str, Any]) -> str:
    if content_state == "live":
        return "live"
    if content_state == "upcoming" or live.get("scheduledStartTime") and not live.get("actualEndTime"):
        return "upcoming"
    if live.get("actualEndTime"):
        return "archived"
    return "archived"
