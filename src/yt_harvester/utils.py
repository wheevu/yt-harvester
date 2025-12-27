import re
import html
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Iterable, List, Optional
from datetime import datetime

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
SENTENCE_ENDINGS = (".", "!", "?", "…")

_INVALID_PATH_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
_WHITESPACE_RE = re.compile(r"\s+")

def safe_path_name(value: str, *, max_len: int = 120) -> str:
    """
    Convert a title into a safe filename/directory name.
    - Removes characters invalid on Windows/macOS/Linux filesystems
    - Collapses whitespace
    - Strips trailing dots/spaces (Windows)
    """
    text = (value or "").strip()
    text = html.unescape(text)
    text = _INVALID_PATH_CHARS_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = text.strip(". ").strip()
    if not text:
        return "untitled"
    if len(text) > max_len:
        text = text[:max_len].rstrip(". ").strip()
    return text or "untitled"


def playlist_id_from_url(value: str) -> Optional[str]:
    """
    Extract a YouTube playlist ID (the `list` query param) if present.
    Returns None if input doesn't look like a playlist URL.
    """
    candidate = (value or "").strip()
    if not candidate:
        return None

    # Raw video IDs should never be treated as playlists.
    if VIDEO_ID_RE.fullmatch(candidate):
        return None

    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if not (host.endswith("youtube.com") or host in {"youtu.be", "www.youtu.be"}):
        return None

    query_params = parse_qs(parsed.query)
    playlist_id = (query_params.get("list") or [None])[0]
    if isinstance(playlist_id, str) and playlist_id.strip():
        return playlist_id.strip()
    return None


def is_youtube_playlist_url(value: str) -> bool:
    """Heuristic: treat any URL with a `list=` query param as a playlist input."""
    return playlist_id_from_url(value) is not None


def normalise_playlist_url(value: str) -> Optional[str]:
    """Convert a URL containing a playlist id into a canonical playlist URL."""
    playlist_id = playlist_id_from_url(value)
    if not playlist_id:
        return None
    return f"https://www.youtube.com/playlist?list={playlist_id}"


def video_id_from_url(value: str) -> str:
    """Extract the 11-character YouTube video ID from a URL or raw ID string."""
    candidate = value.strip()
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


def cleanup_sidecar_files(video_id: str, suffixes: Iterable[str]) -> None:
    for suffix in suffixes:
        candidate = Path(f"{video_id}{suffix}")
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                pass


def _strip_sentence_end(text: str) -> str:
    return text.rstrip('"\')]}»›”’')


def _is_sentence_end(text: str) -> bool:
    stripped = _strip_sentence_end(text)
    return bool(stripped) and stripped[-1] in SENTENCE_ENDINGS


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def merge_fragments(fragments: Iterable[str]) -> List[str]:
    """Merge short caption fragments into readable sentences."""
    paragraphs: List[str] = []
    buffer = ""
    for raw in fragments:
        text = _normalise_text(raw)
        if not text:
            continue
        buffer = f"{buffer} {text}".strip() if buffer else text
        if _is_sentence_end(buffer):
            if not paragraphs or paragraphs[-1] != buffer:
                paragraphs.append(buffer)
            buffer = ""
    if buffer:
        if not paragraphs or paragraphs[-1] != buffer:
            paragraphs.append(buffer)
    return paragraphs


def clean_caption_lines(path: Path) -> List[str]:
    """Normalize caption lines from VTT/SRT files."""
    html_tag_re = re.compile(r"</?[^>]+>")
    inline_ts_re = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>")
    cleaned: List[str] = []
    last_line = ""

    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                if line.upper() == "WEBVTT" or line.startswith("NOTE") or "-->" in line:
                    continue
                if path.suffix.lower() == ".srt" and line.isdigit():
                    continue
                line = html_tag_re.sub("", line)
                line = inline_ts_re.sub("", line)
                if line.startswith(("Kind:", "Language:", "Style:", "Region:")):
                    continue
                line = re.sub(r"\s+", " ", line).strip()
                if not line or line == last_line:
                    continue
                last_line = line
                cleaned.append(html.unescape(line))
    except OSError:
        return []
    return cleaned

def format_like_count(count: int) -> str:
    """Format like count to compact notation (e.g., 1.2M, 531k)."""
    if count >= 1_000_000:
        if count % 1_000_000 == 0:
            return f"{count // 1_000_000}M"
        else:
            formatted = f"{count / 1_000_000:.1f}M"
            return formatted.rstrip('0').rstrip('.')
    elif count >= 1_000:
        if count % 1_000 == 0:
            return f"{count // 1_000}k"
        else:
            formatted = f"{count / 1_000:.1f}k"
            return formatted.rstrip('0').rstrip('.')
    else:
        return str(count)

def format_timestamp(timestamp) -> str:
    """Format timestamp to date only (YYYY-MM-DD)."""
    if not timestamp:
        return ""
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            # Try parsing ISO format or other formats
            dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(timestamp) if timestamp else ""
