from __future__ import annotations

import hashlib
from typing import Any


def normalize_live_chat_items(items: list[dict[str, Any]], video_id: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in items:
        snippet = item.get("snippet", {})
        author = item.get("authorDetails", {})
        text = snippet.get("displayMessage") or ""
        message = {
            "message_id": item.get("id") or _message_id(video_id, snippet.get("publishedAt"), author.get("channelId"), text),
            "video_id": video_id,
            "source": "live",
            "message_type": "paid" if snippet.get("type", "").lower().find("paid") >= 0 else "text",
            "author_external_channel_id": author.get("channelId"),
            "author_name": author.get("displayName"),
            "author_badges": _badges(author),
            "timestamp_usec": _usec(snippet.get("publishedAt")),
            "timestamp_text": snippet.get("publishedAt"),
            "video_offset_time_msec": snippet.get("elapsedTimeMsec"),
            "message_runs": [{"type": "text", "text": text}] if text else [],
            "message_text": text,
            "raw_renderer_type": snippet.get("type"),
            "parse_warning": None,
        }
        messages.append(message)
    return messages


def normalize_replay_actions(actions: list[dict[str, Any]], video_id: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for action in actions:
        replay_action = action.get("replayChatItemAction", {})
        replay_offset_msec = _int_or_none(replay_action.get("videoOffsetTimeMsec"))
        add_action = replay_action.get("actions", [action])[0]
        item = add_action.get("addChatItemAction", {}).get("item") or add_action.get("addLiveChatTickerItemAction", {}).get("item") or action
        renderer_type, renderer = _first_renderer(item)
        if renderer_type in {"liveChatTextMessageRenderer", "liveChatPaidMessageRenderer", "liveChatPaidStickerRenderer", "liveChatTickerPaidMessageItemRenderer"}:
            runs = _message_runs(renderer.get("message", {}).get("runs", []))
            text = "".join(run.get("text", run.get("emoji", {}).get("shortcuts", [""])[0]) for run in runs)
            author_badges = [badge.get("liveChatAuthorBadgeRenderer", {}).get("tooltip") for badge in renderer.get("authorBadges", [])]
            messages.append(
                {
                    "message_id": renderer.get("id") or _message_id(video_id, renderer.get("timestampUsec"), renderer.get("authorExternalChannelId"), text),
                    "video_id": video_id,
                    "source": "replay",
                    "message_type": "paid" if "Paid" in renderer_type else "text",
                    "author_external_channel_id": renderer.get("authorExternalChannelId"),
                    "author_name": _simple_text(renderer.get("authorName")),
                    "author_badges": [badge for badge in author_badges if badge],
                    "timestamp_usec": int(renderer.get("timestampUsec", "0") or 0),
                    "timestamp_text": _simple_text(renderer.get("timestampText")),
                    "video_offset_time_msec": replay_offset_msec if replay_offset_msec is not None else int(renderer.get("videoOffsetTimeMsec", "0") or 0),
                    "message_runs": runs,
                    "message_text": text,
                    "purchase_amount_text": _simple_text(renderer.get("purchaseAmountText")),
                    "raw_renderer_type": renderer_type,
                    "parse_warning": None,
                }
            )
        else:
            messages.append(
                {
                    "message_id": _message_id(video_id, "", renderer_type, str(renderer)[:160]),
                    "video_id": video_id,
                    "source": "replay",
                    "message_type": "unknown",
                    "author_external_channel_id": None,
                    "author_name": None,
                    "author_badges": [],
                    "timestamp_usec": 0,
                    "timestamp_text": None,
                    "video_offset_time_msec": 0,
                    "message_runs": [],
                    "message_text": "",
                    "raw_renderer_type": renderer_type,
                    "parse_warning": "unknown_renderer",
                    "raw_renderer": renderer,
                }
            )
    return messages


def _first_renderer(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key, value in item.items():
        if key.endswith("Renderer") and isinstance(value, dict):
            return key, value
    return "unknown", item


def _message_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for run in runs:
        if "emoji" in run:
            normalized.append({"type": "emoji", "emoji": run["emoji"], "text": run["emoji"].get("shortcuts", [""])[0] if run["emoji"].get("shortcuts") else ""})
        else:
            normalized.append({"type": "text", "text": run.get("text", "")})
    return normalized


def _simple_text(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    if "simpleText" in value:
        return value["simpleText"]
    if "runs" in value:
        return "".join(run.get("text", "") for run in value["runs"])
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _badges(author: dict[str, Any]) -> list[str]:
    return [name for flag, name in [("isChatOwner", "owner"), ("isChatSponsor", "member"), ("isChatModerator", "moderator")] if author.get(flag)]


def _usec(value: str | None) -> int:
    return int(hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:12], 16) if value else 0


def _message_id(video_id: str, timestamp: Any, author: Any, text: str) -> str:
    src = f"{video_id}:{timestamp}:{author}:{text}"
    return hashlib.sha256(src.encode("utf-8")).hexdigest()
