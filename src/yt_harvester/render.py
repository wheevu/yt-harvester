from typing import List

from .pack import VideoDiscussionPack, comment_lookup
from .utils import format_like_count, format_timestamp


def _timecode(seconds: float) -> str:
    total = int(max(seconds, 0.0))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _normalise_author(raw_author: str) -> str:
    value = (raw_author or "").strip()
    if not value:
        return "@Unknown"
    return value if value.startswith("@") else f"@{value}"


def _single_line(value: str, max_len: int = 260) -> str:
    text = " ".join((value or "").split())
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3].rstrip()}..."


def _format_upload_date(raw_date: str) -> str:
    value = (raw_date or "").strip()
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value or "(Unknown date)"


def render_discussion_pack(pack: VideoDiscussionPack) -> str:
    lookup = comment_lookup(pack.scored_comments)
    metadata = pack.metadata

    lines: List[str] = []

    lines.append("TITLE")
    lines.append(str(metadata.get("Title") or "(Unknown title)"))
    lines.append("")
    lines.append("CHANNEL")
    lines.append(str(metadata.get("Channel") or "(Unknown channel)"))
    lines.append("")
    lines.append("DATE")
    lines.append(_format_upload_date(str(metadata.get("UploadDate") or "")))
    lines.append("")
    lines.append("URL")
    lines.append(str(metadata.get("URL") or ""))
    lines.append("")

    lines.append("VIDEO CORE")
    if pack.thesis:
        for bullet in pack.thesis[:4]:
            lines.append(f"- {bullet}")
    else:
        lines.append("- No strong core signals were detected from transcript/comments.")
    lines.append("")

    lines.append("FULL TIMESTAMPED TRANSCRIPT")
    if pack.transcript_chunks:
        for chunk in pack.transcript_chunks:
            start_code = _timecode(chunk.start_seconds)
            end_code = _timecode(chunk.end_seconds)
            lines.append(
                f"- [{start_code}-{end_code}] {_single_line(chunk.text, max_len=600)}"
            )
    else:
        lines.append("(Transcript unavailable.)")
    lines.append("")

    lines.append("AUDIENCE READ")
    if pack.audience_read:
        for bullet in pack.audience_read:
            lines.append(f"- {bullet}")
    else:
        lines.append("- Audience reaction could not be characterized.")
    lines.append("")

    lines.append("MAIN COMMENT THEMES")
    if pack.theme_clusters:
        for index, theme in enumerate(pack.theme_clusters[:6], start=1):
            lines.append(f"{index}. {theme.name}")
            lines.append(f"   - {theme.interpretation}")

            representative_comments = [
                lookup[comment_id]
                for comment_id in theme.representative_comment_ids
                if comment_id in lookup
            ][:4]

            for comment in representative_comments:
                lines.append(
                    f"   - {_normalise_author(comment.author)}: {_single_line(comment.text, max_len=200)}"
                )
            lines.append("")
    else:
        lines.append("(No clear themes detected from available comments.)")
        lines.append("")

    lines.append("CONTROVERSY / SPLIT")
    if pack.controversies:
        for controversy in pack.controversies:
            lines.append(f"- {controversy.issue} ({controversy.level})")
            lines.append(f"  - {controversy.summary}")
            for comment_id in controversy.representative_comment_ids:
                comment = lookup.get(comment_id)
                if not comment:
                    continue
                lines.append(
                    f"  - {_normalise_author(comment.author)}: {_single_line(comment.text, max_len=180)}"
                )
    else:
        lines.append(
            "- Audience is mostly aligned; no meaningful split surfaced in top discussion threads."
        )
    lines.append("")

    lines.append("INTERESTING OUTLIERS")
    if pack.outliers:
        for outlier in pack.outliers:
            comment = lookup.get(outlier.comment_id)
            if not comment:
                continue
            lines.append(
                f"- {_normalise_author(comment.author)}: {_single_line(comment.text, max_len=210)}"
            )
            lines.append(f"  - Why: {outlier.reason}")
    else:
        lines.append("(No high-signal outliers detected.)")
    lines.append("")

    lines.append("TOP COMMENTS")
    if pack.scored_comments:
        for comment in pack.scored_comments[:12]:
            when = format_timestamp(comment.timestamp)
            time_label = f" [{when}]" if when else ""
            lines.append(
                "- "
                f"likes={format_like_count(comment.like_count)} "
                f"replies={comment.reply_count} "
                f"author={_normalise_author(comment.author)}{time_label}: "
                f"{_single_line(comment.text, max_len=190)}"
            )
            why = comment.why_it_matters or "Relevant signal in the discussion."
            lines.append(f"  - Why: {why}")
    else:
        lines.append("(No comments found.)")

    return "\n".join(lines).strip() + "\n"
