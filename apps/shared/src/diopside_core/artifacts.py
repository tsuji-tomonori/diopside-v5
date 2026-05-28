from __future__ import annotations

import html
import re
from collections import Counter
from typing import Any

STOPWORDS = {"これ", "それ", "あれ", "する", "いる", "ある", "こと", "ため", "さん", "ちゃん", "https", "http", "www"}


def summarize_chat_messages(messages: list[dict[str, Any]], bucket_sec: int = 60) -> dict[str, Any]:
    authors = {msg.get("author_external_channel_id") or msg.get("author_name") for msg in messages if msg.get("author_external_channel_id") or msg.get("author_name")}
    paid = [msg for msg in messages if msg.get("message_type") == "paid"]
    emoji_count = sum(1 for msg in messages for run in msg.get("message_runs", []) if run.get("type") == "emoji")
    terms = Counter()
    timeline: Counter[int] = Counter()
    for msg in messages:
        offset = int(msg.get("video_offset_time_msec") or 0) // 1000
        timeline[(offset // bucket_sec) * bucket_sec] += 1
        for term in _terms(msg.get("message_text", "")):
            terms[term] += 1
    return {
        "message_count": len(messages),
        "unique_author_count": len(authors),
        "paid_message_count": len(paid),
        "emoji_count": emoji_count,
        "timeline_buckets": [{"offset_sec": offset, "message_count": count} for offset, count in sorted(timeline.items())],
        "top_terms": [{"term": term, "score": count} for term, count in terms.most_common(40)],
    }


def build_timestamp_candidates(summary: dict[str, Any], description: str = "") -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*([^\n]{0,40})", description):
        hour = int(match.group(1) or 0)
        minute = int(match.group(2))
        second = int(match.group(3))
        candidates.append({"offset_sec": hour * 3600 + minute * 60 + second, "label": match.group(4).strip() or "概要欄タイムスタンプ", "score": 1.0, "source": "description", "evidence_terms": [], "message_count": 0})
    buckets = sorted(summary.get("timeline_buckets", []), key=lambda item: item.get("message_count", 0), reverse=True)[:5]
    top_terms = [item["term"] for item in summary.get("top_terms", [])[:5]]
    for bucket in buckets:
        if bucket.get("message_count", 0) <= 0:
            continue
        candidates.append({"offset_sec": bucket["offset_sec"], "label": "チャット盛り上がり候補", "score": min(0.99, bucket["message_count"] / max(summary.get("message_count", 1), 1) * 10), "source": "chat_burst", "evidence_terms": top_terms[:3], "message_count": bucket["message_count"]})
    seen: set[int] = set()
    unique: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (item["offset_sec"], -item["score"])):
        if candidate["offset_sec"] not in seen:
            unique.append(candidate)
            seen.add(candidate["offset_sec"])
    return unique[:20]


def generate_wordcloud_svg(top_terms: list[dict[str, Any]], width: int = 960, height: int = 540) -> str:
    terms = top_terms[:40]
    max_score = max([float(item.get("score", 1)) for item in terms] or [1])
    rows = []
    for index, item in enumerate(terms):
        x = 48 + (index % 5) * 170
        y = 88 + (index // 5) * 54
        size = 18 + int(34 * float(item.get("score", 1)) / max_score)
        rows.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="#12343b">{html.escape(str(item["term"]))}</text>')
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="diopside wordcloud">',
            '<rect width="100%" height="100%" fill="#f7fbfa"/>',
            *rows,
            "</svg>",
        ]
    )


def _terms(text: str) -> list[str]:
    cleaned = re.sub(r"https?://\S+", " ", text)
    cleaned = re.sub(r"[\u3000\s\W_]+", " ", cleaned, flags=re.UNICODE)
    result = []
    for raw in cleaned.split():
        term = raw.strip().lower()
        if len(term) < 2 or term in STOPWORDS:
            continue
        result.append(term)
    return result
