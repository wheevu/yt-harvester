import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from .utils import cleanup_sidecar_files

OFFICIAL_TRANSCRIPT_LANGS = ["en", "en-US", "en-GB", "en-CA", "en-AU"]

TranscriptSegment = Dict[str, Any]
CommentDict = Dict[str, Any]
StructuredComments = List[CommentDict]


def _compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _parse_timestamp_seconds(raw: str) -> float:
    parts = raw.strip().split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    return float(parts[0])


def _parse_time_bounds(line: str) -> Tuple[Optional[float], Optional[float]]:
    if "-->" not in line:
        return (None, None)

    left, right = line.split("-->", 1)
    start_raw = left.strip().replace(",", ".")
    end_raw = right.strip().split()[0].replace(",", ".")
    try:
        start_seconds = _parse_timestamp_seconds(start_raw)
        end_seconds = _parse_timestamp_seconds(end_raw)
    except Exception:
        return (None, None)

    if end_seconds < start_seconds:
        end_seconds = start_seconds
    return (start_seconds, end_seconds)


def _parse_caption_segments(path: Path) -> List[TranscriptSegment]:
    html_tag_re = re.compile(r"</?[^>]+>")
    inline_ts_re = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>")
    segments: List[TranscriptSegment] = []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        if not line or line.upper() == "WEBVTT" or line.startswith("NOTE"):
            idx += 1
            continue

        if line.isdigit() and idx + 1 < len(lines) and "-->" in lines[idx + 1]:
            idx += 1
            line = lines[idx].strip()

        start_seconds, end_seconds = _parse_time_bounds(line)
        if start_seconds is None or end_seconds is None:
            idx += 1
            continue

        idx += 1
        text_lines: List[str] = []
        while idx < len(lines):
            current = lines[idx].strip()
            if not current:
                break
            if current.startswith(("Kind:", "Language:", "Style:", "Region:")):
                idx += 1
                continue
            cleaned = html_tag_re.sub("", current)
            cleaned = inline_ts_re.sub("", cleaned)
            cleaned = _compact_whitespace(cleaned)
            if cleaned:
                text_lines.append(cleaned)
            idx += 1

        text = _compact_whitespace(" ".join(text_lines))
        if text and (not segments or segments[-1]["text"] != text):
            duration = max(end_seconds - start_seconds, 0.0)
            segments.append(
                {
                    "start": float(start_seconds),
                    "duration": float(duration),
                    "text": text,
                }
            )

        idx += 1

    return segments


def fetch_metadata(video_id: str, watch_url: str) -> dict:
    """Fetch video metadata via yt-dlp; fall back to placeholders."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extractor_args": {"youtube": {"player_client": ["default"]}},
    }

    info = {}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(watch_url, download=False)
    except Exception:
        info = {}

    title = info.get("title") if isinstance(info, dict) else None
    channel = info.get("uploader") if isinstance(info, dict) else None
    canonical = info.get("webpage_url") if isinstance(info, dict) else None

    view_count = info.get("view_count") if isinstance(info, dict) else None
    duration = info.get("duration") if isinstance(info, dict) else None
    upload_date = info.get("upload_date") if isinstance(info, dict) else None
    description = info.get("description") if isinstance(info, dict) else None

    return {
        "Title": title or "(Unknown title)",
        "Channel": channel or "(Unknown channel)",
        "URL": canonical or watch_url,
        "ViewCount": view_count,
        "Duration": duration,
        "UploadDate": upload_date,
        "Description": description,
        "VideoID": video_id,
    }


def try_official_transcript(video_id: str) -> List[TranscriptSegment]:
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=OFFICIAL_TRANSCRIPT_LANGS)
    except Exception:
        return []

    segments: List[TranscriptSegment] = []
    for snippet in transcript:
        text = _compact_whitespace(getattr(snippet, "text", ""))
        if not text:
            continue
        start = float(getattr(snippet, "start", 0.0) or 0.0)
        duration = float(getattr(snippet, "duration", 0.0) or 0.0)
        segments.append({"start": start, "duration": duration, "text": text})
    return segments


def try_auto_captions(video_id: str, watch_url: str) -> List[TranscriptSegment]:
    output_pattern = f"{video_id}.%(ext)s"
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--sub-format",
        "vtt",
        "--sub-langs",
        "en.*,en",
        "--no-write-playlist-metafiles",
        "--extractor-args",
        "youtube:player_client=default",
        "-o",
        output_pattern,
        watch_url,
    ]

    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError, Exception):
        cleanup_sidecar_files(video_id, (".info.json",))
        return []

    caption_files = sorted(Path(".").glob(f"{video_id}*.vtt")) + sorted(
        Path(".").glob(f"{video_id}*.srt")
    )

    segments: List[TranscriptSegment] = []
    if caption_files:
        segments = _parse_caption_segments(caption_files[0])

    for caption_file in caption_files:
        try:
            caption_file.unlink()
        except OSError:
            pass

    cleanup_sidecar_files(video_id, (".info.json",))
    return segments


def fetch_transcript(video_id: str, watch_url: str) -> List[TranscriptSegment]:
    official = try_official_transcript(video_id)
    if official:
        return official

    auto = try_auto_captions(video_id, watch_url)
    if auto:
        return auto

    return []


def fetch_comments(
    video_id: str, watch_url: str, max_dl: int = 20000, top_n: int = 120
) -> StructuredComments:
    """
    Fetch comments via yt-dlp and return threaded root comments with replies.
    Does not clean up files; caller should clean up sidecar files.
    """
    info_json_path = Path(f"{video_id}.info.json")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-comments",
        "--write-info-json",
        "--extractor-args",
        f"youtube:max_comments={max_dl},all,100;comment_sort=top;player_client=default",
        "--no-write-playlist-metafiles",
        "-o",
        f"{video_id}.%(ext)s",
        watch_url,
    ]

    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError, Exception):
        return []

    if not info_json_path.exists():
        return []

    try:
        with info_json_path.open("r", encoding="utf-8") as handle:
            info_data = json.load(handle)
        data = info_data.get("comments", [])
    except Exception:
        return []

    if not isinstance(data, list) or not data:
        return []

    children = defaultdict(list)
    roots = []
    for comment in data:
        parent_id = comment.get("parent")
        if parent_id and parent_id != "root":
            children[parent_id].append(comment)
        else:
            roots.append(comment)

    def normalise_likes(value: Any) -> int:
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    roots.sort(key=lambda c: normalise_likes(c.get("like_count")), reverse=True)

    structured_comments: StructuredComments = []
    for root in roots[:top_n]:
        root_replies = children.get(root.get("id"), [])
        replies_sorted = sorted(
            root_replies,
            key=lambda r: (
                normalise_likes(r.get("like_count")),
                r.get("timestamp", 0),
            ),
            reverse=True,
        )

        structured_comments.append(
            {
                "author": root.get("author", ""),
                "text": root.get("text", ""),
                "like_count": normalise_likes(root.get("like_count")),
                "timestamp": root.get("timestamp"),
                "id": root.get("id"),
                "replies": [
                    {
                        "author": reply.get("author", ""),
                        "text": reply.get("text", ""),
                        "like_count": normalise_likes(reply.get("like_count")),
                        "timestamp": reply.get("timestamp"),
                        "id": reply.get("id"),
                    }
                    for reply in replies_sorted[:100]
                ],
            }
        )

    return structured_comments
