import html
import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_INVALID_PATH_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
_WHITESPACE_RE = re.compile(r"\s+")


def compact_whitespace(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value or "").strip()


def safe_path_name(value: str, max_len: int = 120) -> str:
    """Convert a title into a filesystem-safe path segment."""
    text = compact_whitespace(value)
    text = html.unescape(text)
    text = _INVALID_PATH_CHARS_RE.sub(" ", text)
    text = compact_whitespace(text)
    text = text.strip(". ").strip()

    if not text:
        return "untitled"

    if len(text) > max_len:
        text = text[:max_len].rstrip(". ").strip()

    return text or "untitled"


def video_id_from_url(value: str) -> str:
    """Extract the 11-character YouTube video ID from a URL or raw ID string."""
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("No video identifier provided.")

    if VIDEO_ID_RE.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()

    if host in {"youtu.be", "www.youtu.be"}:
        parts = [segment for segment in parsed.path.split("/") if segment]
        if parts and VIDEO_ID_RE.fullmatch(parts[0]):
            return parts[0]

    if host.endswith("youtube.com"):
        query_params = parse_qs(parsed.query)
        if "v" in query_params:
            vid = query_params["v"][0]
            if VIDEO_ID_RE.fullmatch(vid):
                return vid

        path_segments = [segment for segment in parsed.path.split("/") if segment]
        if len(path_segments) >= 2 and path_segments[0] in {"embed", "shorts", "watch"}:
            vid = path_segments[1]
            if VIDEO_ID_RE.fullmatch(vid):
                return vid

    if "/" in candidate:
        tail = candidate.split("/")[-1]
        if VIDEO_ID_RE.fullmatch(tail):
            return tail

    raise ValueError("Unable to extract a valid YouTube video ID from the input.")


def build_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def format_like_count(count: int) -> str:
    """Format like count to compact notation (e.g., 1.2M, 531k)."""
    if count >= 1_000_000:
        if count % 1_000_000 == 0:
            return f"{count // 1_000_000}M"
        formatted = f"{count / 1_000_000:.1f}M"
        return formatted.rstrip("0").rstrip(".")

    if count >= 1_000:
        if count % 1_000 == 0:
            return f"{count // 1_000}k"
        formatted = f"{count / 1_000:.1f}k"
        return formatted.rstrip("0").rstrip(".")

    return str(count)


def format_timestamp(timestamp) -> str:
    """Format timestamp to date only (YYYY-MM-DD)."""
    if not timestamp:
        return ""

    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(timestamp) if timestamp else ""
