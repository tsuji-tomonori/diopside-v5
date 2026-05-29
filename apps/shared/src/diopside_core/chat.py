from __future__ import annotations

import hashlib
from typing import Any

CHAT_MESSAGE_SCHEMA_VERSION = "chat-message/v1"

CHAT_MESSAGE_REQUIRED_KEYS = (
    "schema_version",
    "message_id",
    "video_id",
    "source",
    "message_type",
    "author",
    "author_external_channel_id",
    "author_name",
    "author_badges",
    "timestamp_usec",
    "timestamp_text",
    "offset_msec",
    "video_offset_time_msec",
    "message_runs",
    "plain_text",
    "message_text",
    "paid",
    "purchase_amount_text",
    "sticker",
    "raw_ref",
    "raw_renderer_type",
    "raw_renderer",
    "parse_warning",
    "collected_at",
)


def normalize_live_chat_items(items: list[dict[str, Any]], video_id: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in items:
        snippet = item.get("snippet", {})
        author = item.get("authorDetails", {})
        text = snippet.get("displayMessage") or ""
        message_type = _live_message_type(snippet.get("type"))
        messages.append(
            _chat_message(
                message_id=item.get("id") or _message_id(video_id, snippet.get("publishedAt"), author.get("channelId"), text),
                video_id=video_id,
                source="live",
                message_type=message_type,
                author_external_channel_id=author.get("channelId"),
                author_name=author.get("displayName"),
                author_badges=_badges(author),
                timestamp_usec=_usec(snippet.get("publishedAt")),
                timestamp_text=snippet.get("publishedAt"),
                offset_msec=_int_or_none(snippet.get("elapsedTimeMsec")),
                message_runs=[_text_run(text)] if text else [],
                message_text=text,
                paid=_paid(None),
                sticker=_sticker(None),
                raw_renderer_type=snippet.get("type"),
            )
        )
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
                _chat_message(
                    message_id=renderer.get("id") or _message_id(video_id, renderer.get("timestampUsec"), renderer.get("authorExternalChannelId"), text),
                    video_id=video_id,
                    source="replay",
                    message_type=_replay_message_type(renderer_type),
                    author_external_channel_id=renderer.get("authorExternalChannelId"),
                    author_name=_simple_text(renderer.get("authorName")),
                    author_badges=[badge for badge in author_badges if badge],
                    timestamp_usec=int(renderer.get("timestampUsec", "0") or 0),
                    timestamp_text=_simple_text(renderer.get("timestampText")),
                    offset_msec=replay_offset_msec if replay_offset_msec is not None else _int_or_none(renderer.get("videoOffsetTimeMsec")),
                    message_runs=runs,
                    message_text=text,
                    paid=_paid(renderer.get("purchaseAmountText")),
                    sticker=_sticker(renderer.get("sticker")),
                    raw_renderer_type=renderer_type,
                )
            )
        else:
            messages.append(
                _chat_message(
                    message_id=_message_id(video_id, "", renderer_type, str(renderer)[:160]),
                    video_id=video_id,
                    source="replay",
                    message_type="unknown",
                    author_external_channel_id=None,
                    author_name=None,
                    author_badges=[],
                    timestamp_usec=0,
                    timestamp_text=None,
                    offset_msec=replay_offset_msec,
                    message_runs=[],
                    message_text="",
                    paid=_paid(None),
                    sticker=_sticker(None),
                    raw_renderer_type=renderer_type,
                    raw_renderer=renderer,
                    parse_warning="unknown_renderer",
                )
            )
    return messages


def _chat_message(
    *,
    message_id: str,
    video_id: str,
    source: str,
    message_type: str,
    author_external_channel_id: str | None,
    author_name: str | None,
    author_badges: list[str],
    timestamp_usec: int,
    timestamp_text: str | None,
    offset_msec: int | None,
    message_runs: list[dict[str, Any]],
    message_text: str,
    paid: dict[str, Any],
    sticker: dict[str, Any] | None,
    raw_renderer_type: str | None,
    raw_renderer: dict[str, Any] | None = None,
    parse_warning: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CHAT_MESSAGE_SCHEMA_VERSION,
        "message_id": message_id,
        "video_id": video_id,
        "source": source,
        "message_type": message_type,
        "author": {
            "display_name": author_name,
            "channel_id_hash": f"sha256:{hashlib.sha256(author_external_channel_id.encode('utf-8')).hexdigest()}" if author_external_channel_id else None,
            "badges": author_badges,
        },
        "author_external_channel_id": author_external_channel_id,
        "author_name": author_name,
        "author_badges": author_badges,
        "timestamp_usec": timestamp_usec,
        "timestamp_text": timestamp_text,
        "offset_msec": offset_msec,
        "video_offset_time_msec": offset_msec,
        "message_runs": message_runs,
        "plain_text": message_text,
        "message_text": message_text,
        "paid": paid,
        "purchase_amount_text": paid.get("amount_text"),
        "sticker": sticker,
        "raw_ref": None,
        "raw_renderer_type": raw_renderer_type,
        "raw_renderer": raw_renderer,
        "parse_warning": parse_warning,
        "collected_at": None,
    }


def _first_renderer(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key, value in item.items():
        if key.endswith("Renderer") and isinstance(value, dict):
            return key, value
    return "unknown", item


def _message_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for run in runs:
        if "emoji" in run:
            emoji = run["emoji"]
            normalized.append(
                {
                    "type": "emoji",
                    "emoji": emoji,
                    "emoji_id": emoji.get("emojiId"),
                    "label": emoji.get("shortcuts", [""])[0] if emoji.get("shortcuts") else _simple_text(emoji.get("image", {}).get("accessibility", {}).get("accessibilityData", {}).get("label")),
                    "is_custom_emoji": bool(emoji.get("isCustomEmoji")),
                    "text": emoji.get("shortcuts", [""])[0] if emoji.get("shortcuts") else "",
                }
            )
        else:
            normalized.append(_text_run(run.get("text", "")))
    return normalized


def _text_run(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _live_message_type(value: Any) -> str:
    lowered = str(value or "").lower()
    if "sticker" in lowered:
        return "sticker"
    if "paid" in lowered or "superchat" in lowered:
        return "paid"
    return "text"


def _replay_message_type(renderer_type: str) -> str:
    if renderer_type == "liveChatPaidStickerRenderer":
        return "sticker"
    if "Paid" in renderer_type:
        return "paid"
    return "text"


def _paid(value: Any) -> dict[str, Any]:
    amount_text = _simple_text(value)
    return {"is_paid": bool(amount_text), "amount_text": amount_text, "currency": None}


def _sticker(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    image = value.get("image", {})
    thumbnails = image.get("thumbnails") or []
    return {
        "emoji_id": value.get("emojiId"),
        "alt_text": _simple_text(image.get("accessibility", {}).get("accessibilityData", {}).get("label")),
        "image_url": thumbnails[-1].get("url") if thumbnails else None,
    }


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
