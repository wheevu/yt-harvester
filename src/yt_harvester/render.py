from typing import Any, Dict, List

from .utils import compact_whitespace, format_like_count, format_timestamp


def _timecode(seconds: float) -> str:
    total = int(max(seconds, 0.0))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _normalise_author(raw_author: str) -> str:
    value = compact_whitespace(raw_author)
    if not value:
        return "@Unknown"
    return value if value.startswith("@") else f"@{value}"


def _single_line(value: str, max_len: int = 500) -> str:
    text = compact_whitespace(value)
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3].rstrip()}..."


def _format_upload_date(raw_date: str) -> str:
    value = compact_whitespace(raw_date)
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value or "(Unknown date)"


def _format_duration(duration_seconds: Any) -> str:
    if not isinstance(duration_seconds, (int, float)) or duration_seconds < 0:
        return "(Unknown duration)"
    total = int(duration_seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _render_metadata(lines: List[str], metadata: Dict[str, Any]) -> None:
    lines.append("METADATA")
    lines.append(f"Title: {metadata.get('Title') or '(Unknown title)'}")
    lines.append(f"Channel: {metadata.get('Channel') or '(Unknown channel)'}")
    lines.append(f"Date: {_format_upload_date(str(metadata.get('UploadDate') or ''))}")
    lines.append(f"URL: {metadata.get('URL') or ''}")

    view_count = metadata.get("ViewCount")
    if isinstance(view_count, int) and view_count >= 0:
        lines.append(f"Views: {view_count:,}")
    else:
        lines.append("Views: (Unknown)")

    lines.append(f"Duration: {_format_duration(metadata.get('Duration'))}")
    lines.append(f"Video ID: {metadata.get('VideoID') or '(Unknown id)'}")
    lines.append("")


def _render_transcript(
    lines: List[str], transcript_segments: List[Dict[str, Any]]
) -> None:
    lines.append("TIMESTAMPED TRANSCRIPT")
    if not transcript_segments:
        lines.append("(Transcript unavailable.)")
        lines.append("")
        return

    # Render segment-by-segment to preserve timestamp fidelity for downstream LLM use.
    sorted_segments = sorted(
        transcript_segments,
        key=lambda seg: float(seg.get("start", 0.0) or 0.0),
    )

    for segment in sorted_segments:
        start = float(segment.get("start", 0.0) or 0.0)
        duration = float(segment.get("duration", 0.0) or 0.0)
        end = max(start + duration, start)
        text = _single_line(str(segment.get("text") or ""), max_len=850)
        if not text:
            continue
        lines.append(f"- [{_timecode(start)}-{_timecode(end)}] {text}")

    lines.append("")


def _render_comments(lines: List[str], comments: List[Dict[str, Any]]) -> None:
    lines.append("COMMENTS")
    if not comments:
        lines.append("(No comments found.)")
        lines.append("")
        return

    # Render retained comment threads directly; no summarization layer by design.
    for root in comments:
        root_text = _single_line(str(root.get("text") or ""), max_len=850)
        if not root_text:
            continue

        root_likes = format_like_count(int(root.get("like_count") or 0))
        root_author = _normalise_author(str(root.get("author") or ""))
        root_when = format_timestamp(root.get("timestamp"))
        root_time = f" [{root_when}]" if root_when else ""
        replies = (
            root.get("replies", []) if isinstance(root.get("replies"), list) else []
        )

        lines.append(
            "- "
            f"likes={root_likes} replies={len(replies)} "
            f"author={root_author}{root_time}: {root_text}"
        )

        for reply in replies:
            reply_text = _single_line(str(reply.get("text") or ""), max_len=700)
            if not reply_text:
                continue
            reply_likes = format_like_count(int(reply.get("like_count") or 0))
            reply_author = _normalise_author(str(reply.get("author") or ""))
            reply_when = format_timestamp(reply.get("timestamp"))
            reply_time = f" [{reply_when}]" if reply_when else ""
            lines.append(
                "  - "
                f"reply likes={reply_likes} author={reply_author}{reply_time}: {reply_text}"
            )

    lines.append("")


def render_report(
    metadata: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    _render_metadata(lines, metadata)
    _render_transcript(lines, transcript_segments)
    _render_comments(lines, comments)
    return "\n".join(lines).strip() + "\n"
