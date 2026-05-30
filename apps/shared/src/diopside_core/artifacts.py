from __future__ import annotations

import html
import binascii
import hashlib
import re
import struct
import zlib
from collections import Counter
from typing import Any, Iterable

STOPWORDS = {"これ", "それ", "あれ", "する", "いる", "ある", "こと", "ため", "さん", "ちゃん", "https", "http", "www"}


def summarize_chat_messages(messages: Iterable[dict[str, Any]], bucket_sec: int = 60) -> dict[str, Any]:
    message_count = 0
    authors = set()
    paid_message_count = 0
    emoji_count = 0
    terms = Counter()
    timeline: Counter[int] = Counter()
    term_timeline: dict[str, Counter[int]] = {}
    for msg in messages:
        message_count += 1
        author = msg.get("author_external_channel_id") or msg.get("author_name")
        if author:
            authors.add(author)
        if msg.get("message_type") == "paid":
            paid_message_count += 1
        emoji_count += sum(1 for run in msg.get("message_runs", []) if run.get("type") == "emoji")
        offset = int(msg.get("video_offset_time_msec") or 0) // 1000
        bucket_offset = (offset // bucket_sec) * bucket_sec
        timeline[bucket_offset] += 1
        for term in _terms(msg.get("message_text", "")):
            terms[term] += 1
            term_timeline.setdefault(term, Counter())[bucket_offset] += 1
    return {
        "message_count": message_count,
        "unique_author_count": len(authors),
        "paid_message_count": paid_message_count,
        "emoji_count": emoji_count,
        "timeline_buckets": [{"offset_sec": offset, "message_count": count} for offset, count in sorted(timeline.items())],
        "top_terms": [{"term": term, "score": count} for term, count in terms.most_common(40)],
        "term_timeline": {
            term: [{"offset_sec": offset, "count": count} for offset, count in sorted(bucket_counts.items())]
            for term, bucket_counts in sorted(term_timeline.items())
        },
    }


def build_timestamp_candidates(summary: dict[str, Any], description: str = "") -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*([^\n]{0,40})", description):
        hour = int(match.group(1) or 0)
        minute = int(match.group(2))
        second = int(match.group(3))
        candidates.append(
            _timestamp_candidate(
                offset_sec=hour * 3600 + minute * 60 + second,
                label=match.group(4).strip() or "概要欄タイムスタンプ",
                score=1.0,
                source="description",
                evidence_terms=[],
                message_count=0,
            )
        )
    buckets = sorted(summary.get("timeline_buckets", []), key=lambda item: item.get("message_count", 0), reverse=True)[:5]
    top_terms = [item["term"] for item in summary.get("top_terms", [])[:5]]
    for bucket in buckets:
        if bucket.get("message_count", 0) <= 0:
            continue
        candidates.append(
            _timestamp_candidate(
                offset_sec=bucket["offset_sec"],
                label="チャット盛り上がり候補",
                score=min(0.99, bucket["message_count"] / max(summary.get("message_count", 1), 1) * 10),
                source="chat_burst",
                evidence_terms=top_terms[:3],
                message_count=bucket["message_count"],
            )
        )
    for term in top_terms[:10]:
        term_buckets = sorted(summary.get("term_timeline", {}).get(term, []), key=lambda item: item.get("count", 0), reverse=True)
        if not term_buckets:
            continue
        strongest = term_buckets[0]
        total = sum(item.get("count", 0) for item in term_buckets)
        if total >= 3 and strongest.get("count", 0) / max(total, 1) >= 0.5:
            candidates.append(
                _timestamp_candidate(
                    offset_sec=strongest["offset_sec"],
                    label=f"{term} のキーワードスパイク",
                    score=min(0.95, 0.5 + strongest["count"] / max(summary.get("message_count", 1), 1)),
                    source="keyword_spike",
                    evidence_terms=[term],
                    message_count=strongest["count"],
                )
            )
    return _dedupe_timestamp_candidates(candidates)[:20]


def generate_chapters_suggestion_markdown(video_id: str, candidates: list[dict[str, Any]]) -> str:
    lines = [f"# chapters_suggestion for {video_id}", "", "```text"]
    ordered = sorted(candidates, key=lambda item: (int(item.get("offset_sec") or 0), -float(item.get("score") or 0), str(item.get("label") or "")))
    if not ordered:
        lines.append("候補なし")
    for candidate in ordered:
        offset_sec = max(0, int(candidate.get("offset_sec") or 0))
        label = _chapter_label(str(candidate.get("label") or "チャプター候補"))
        lines.append(f"{_format_chapter_offset(offset_sec)} {label}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def _timestamp_candidate(*, offset_sec: int, label: str, score: float, source: str, evidence_terms: list[str], message_count: int) -> dict[str, Any]:
    return {
        "offset_sec": offset_sec,
        "label": label,
        "score": round(score, 4),
        "source": source,
        "merged_sources": [source],
        "evidence_terms": evidence_terms,
        "message_count": message_count,
    }


def _dedupe_timestamp_candidates(candidates: list[dict[str, Any]], window_sec: int = 15) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (item["offset_sec"], -item["score"], item["source"])):
        target = next((item for item in merged if abs(item["offset_sec"] - candidate["offset_sec"]) <= window_sec), None)
        if not target:
            merged.append({**candidate})
            continue
        if (candidate["score"], -candidate["offset_sec"], candidate["source"]) > (target["score"], -target["offset_sec"], target["source"]):
            target.update(
                {
                    "offset_sec": candidate["offset_sec"],
                    "label": candidate["label"],
                    "score": candidate["score"],
                    "source": candidate["source"],
                }
            )
        target["merged_sources"] = sorted(set(target.get("merged_sources", [])) | set(candidate.get("merged_sources", [candidate["source"]])))
        target["evidence_terms"] = sorted(set(target.get("evidence_terms", [])) | set(candidate.get("evidence_terms", [])))
        target["message_count"] = max(int(target.get("message_count", 0)), int(candidate.get("message_count", 0)))
    return sorted(merged, key=lambda item: (-item["score"], item["offset_sec"], item["source"]))


def _format_chapter_offset(offset_sec: int) -> str:
    hours, remainder = divmod(offset_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _chapter_label(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label).strip()
    return cleaned or "チャプター候補"


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


def generate_wordcloud_png(top_terms: list[dict[str, Any]], width: int = 960, height: int = 540) -> bytes:
    terms = top_terms[:40]
    pixels = bytearray([247, 251, 250] * width * height)
    _fill_rect(pixels, width, height, 0, 0, width, 8, (26, 78, 91))
    max_score = max([float(item.get("score", 1)) for item in terms] or [1])
    cell_width = max(80, (width - 96) // 4)
    for index, item in enumerate(terms):
        term = str(item.get("term", ""))
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        score = max(0.0, float(item.get("score", 1)))
        row = index // 4
        col = index % 4
        x = 48 + col * cell_width
        y = 44 + row * 48
        bar_width = max(16, min(cell_width - 18, int((cell_width - 18) * score / max_score)))
        bar_height = 16 + int(18 * score / max_score)
        color = (36 + digest[0] % 120, 70 + digest[1] % 120, 90 + digest[2] % 120)
        _fill_rect(pixels, width, height, x, y, bar_width, bar_height, color)
        stripe_color = (max(color[0] - 28, 0), max(color[1] - 28, 0), max(color[2] - 28, 0))
        for stripe in range(0, bar_width, 11 + digest[3] % 7):
            _fill_rect(pixels, width, height, x + stripe, y, 3, bar_height, stripe_color)
        marker = 6 + digest[4] % 10
        _fill_rect(pixels, width, height, x, y + bar_height + 5, marker * 2, 6, (18, 52, 59))
    return _encode_png_rgb(width, height, bytes(pixels))


def _fill_rect(pixels: bytearray, width: int, height: int, x: int, y: int, rect_width: int, rect_height: int, color: tuple[int, int, int]) -> None:
    left = max(0, x)
    top = max(0, y)
    right = min(width, x + rect_width)
    bottom = min(height, y + rect_height)
    if right <= left or bottom <= top:
        return
    row = bytes(color) * (right - left)
    for yy in range(top, bottom):
        start = (yy * width + left) * 3
        pixels[start : start + len(row)] = row


def _encode_png_rgb(width: int, height: int, rgb: bytes) -> bytes:
    rows = [b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height)]
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    png.extend(_png_chunk(b"IDAT", zlib.compress(b"".join(rows), level=9)))
    png.extend(_png_chunk(b"IEND", b""))
    return bytes(png)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


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
