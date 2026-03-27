import json
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from youtube_transcript_api import YouTubeTranscriptApi

from .utils import compact_whitespace

OFFICIAL_TRANSCRIPT_LANGS = ["en", "en-US", "en-GB", "en-CA", "en-AU"]

# These caps preserve meaningful discussion context while avoiding long-tail fetch costs.
MAX_COMMENTS_TOTAL = 4_000
MAX_COMMENT_PARENTS = 300
MAX_COMMENT_REPLIES_TOTAL = 2_600
MAX_REPLIES_PER_THREAD = 12
MAX_COMMENT_DEPTH = 2

TranscriptSegment = Dict[str, Any]
CommentDict = Dict[str, Any]
StructuredComments = List[CommentDict]


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
            cleaned = compact_whitespace(cleaned)
            if cleaned:
                text_lines.append(cleaned)
            idx += 1

        text = compact_whitespace(" ".join(text_lines))
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


def _normalise_likes(value: Any) -> int:
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return 0


def _normalise_comment(comment: Dict[str, Any]) -> Optional[CommentDict]:
    text = compact_whitespace(str(comment.get("text") or ""))
    if not text:
        return None

    return {
        "author": compact_whitespace(str(comment.get("author") or "")),
        "text": text,
        "like_count": _normalise_likes(comment.get("like_count")),
        "timestamp": comment.get("timestamp"),
        "id": str(comment.get("id") or ""),
    }


def _extract_metadata_from_info(
    info: Dict[str, Any], video_id: str, watch_url: str
) -> Dict[str, Any]:
    return {
        "Title": info.get("title") or "(Unknown title)",
        "Channel": info.get("uploader") or "(Unknown channel)",
        "URL": info.get("webpage_url") or watch_url,
        "ViewCount": info.get("view_count"),
        "Duration": info.get("duration"),
        "UploadDate": info.get("upload_date"),
        "VideoID": video_id,
    }


def _extract_comments_from_info(info: Dict[str, Any]) -> StructuredComments:
    data = info.get("comments", [])
    if not isinstance(data, list) or not data:
        return []

    children = defaultdict(list)
    roots: List[Dict[str, Any]] = []
    for raw_comment in data:
        if not isinstance(raw_comment, dict):
            continue

        comment = _normalise_comment(raw_comment)
        if not comment:
            continue

        parent_id = raw_comment.get("parent")
        if parent_id and parent_id != "root":
            children[str(parent_id)].append(comment)
        else:
            roots.append(comment)

    roots.sort(key=lambda c: c["like_count"], reverse=True)

    structured: StructuredComments = []
    for root in roots[:MAX_COMMENT_PARENTS]:
        root_replies = children.get(root["id"], [])
        replies_sorted = sorted(
            root_replies,
            key=lambda r: (
                r["like_count"],
                r.get("timestamp") or 0,
            ),
            reverse=True,
        )
        root_with_replies = dict(root)
        root_with_replies["replies"] = replies_sorted[:MAX_REPLIES_PER_THREAD]
        structured.append(root_with_replies)

    return structured


def _load_info_json_from_dir(
    directory: Path, video_id: str
) -> Optional[Dict[str, Any]]:
    primary = directory / f"{video_id}.info.json"
    candidates = [primary] if primary.exists() else []
    if not candidates:
        candidates = sorted(directory.glob("*.info.json"))

    if not candidates:
        return None

    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def fetch_metadata_and_comments(
    video_id: str,
    watch_url: str,
) -> Tuple[Dict[str, Any], StructuredComments]:
    extractor_comments = (
        "youtube:max_comments="
        f"{MAX_COMMENTS_TOTAL},{MAX_COMMENT_PARENTS},"
        f"{MAX_COMMENT_REPLIES_TOTAL},{MAX_REPLIES_PER_THREAD},{MAX_COMMENT_DEPTH}"
        ";comment_sort=top;player_client=default"
    )

    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--skip-download",
        "--write-comments",
        "--write-info-json",
        "--extractor-args",
        extractor_comments,
        "--no-write-playlist-metafiles",
        "-o",
        f"{video_id}.%(ext)s",
        watch_url,
    ]

    # yt-dlp sidecar naming can vary across extractors; isolate everything in tmp.
    with tempfile.TemporaryDirectory(prefix="yt-harvester-") as tmp:
        tmp_path = Path(tmp)
        try:
            subprocess.run(
                cmd,
                check=True,
                cwd=tmp,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, Exception):
            return (_extract_metadata_from_info({}, video_id, watch_url), [])

        info = _load_info_json_from_dir(tmp_path, video_id)
        if not isinstance(info, dict):
            return (_extract_metadata_from_info({}, video_id, watch_url), [])

        metadata = _extract_metadata_from_info(info, video_id, watch_url)
        comments = _extract_comments_from_info(info)
        return (metadata, comments)


def _segment_from_snippet(snippet: Any) -> Optional[TranscriptSegment]:
    if isinstance(snippet, dict):
        text = compact_whitespace(str(snippet.get("text") or ""))
        start = float(snippet.get("start", 0.0) or 0.0)
        duration = float(snippet.get("duration", 0.0) or 0.0)
    else:
        text = compact_whitespace(str(getattr(snippet, "text", "") or ""))
        start = float(getattr(snippet, "start", 0.0) or 0.0)
        duration = float(getattr(snippet, "duration", 0.0) or 0.0)

    if not text:
        return None

    return {"start": start, "duration": duration, "text": text}


def _segments_from_transcript_items(items: Any) -> List[TranscriptSegment]:
    segments: List[TranscriptSegment] = []
    for snippet in items or []:
        segment = _segment_from_snippet(snippet)
        if segment:
            segments.append(segment)
    return segments


def try_official_transcript(video_id: str) -> List[TranscriptSegment]:
    api = YouTubeTranscriptApi()

    # Prefer manual captions, then generated captions, then legacy fetch fallback.
    try:
        transcript_list = api.list(video_id)
    except Exception:
        transcript_list = None

    if transcript_list is not None:
        finders = [
            getattr(transcript_list, "find_manually_created_transcript", None),
            getattr(transcript_list, "find_generated_transcript", None),
            getattr(transcript_list, "find_transcript", None),
        ]

        for finder in finders:
            if not callable(finder):
                continue
            try:
                transcript = finder(OFFICIAL_TRANSCRIPT_LANGS)
                segments = _segments_from_transcript_items(transcript.fetch())
                if segments:
                    return segments
            except Exception:
                continue

    try:
        transcript = api.fetch(video_id, languages=OFFICIAL_TRANSCRIPT_LANGS)
    except Exception:
        return []

    return _segments_from_transcript_items(transcript)


def try_auto_captions(video_id: str, watch_url: str) -> List[TranscriptSegment]:
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
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
        f"{video_id}.%(ext)s",
        watch_url,
    ]

    # Keep caption sidecars out of the project root and let tempdir clean up.
    with tempfile.TemporaryDirectory(prefix="yt-harvester-") as tmp:
        tmp_path = Path(tmp)
        try:
            subprocess.run(
                cmd,
                check=True,
                cwd=tmp,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, Exception):
            return []

        caption_files = sorted(tmp_path.glob(f"{video_id}*.vtt")) + sorted(
            tmp_path.glob(f"{video_id}*.srt")
        )
        if not caption_files:
            return []
        return _parse_caption_segments(caption_files[0])


def fetch_transcript(video_id: str, watch_url: str) -> List[TranscriptSegment]:
    official = try_official_transcript(video_id)
    if official:
        return official

    auto = try_auto_captions(video_id, watch_url)
    if auto:
        return auto

    return []
