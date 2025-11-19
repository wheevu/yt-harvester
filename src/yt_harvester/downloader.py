import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from .utils import merge_fragments, clean_caption_lines, cleanup_sidecar_files

OFFICIAL_TRANSCRIPT_LANGS = ["en", "en-US", "en-GB", "en-CA", "en-AU"]

# Type alias for structured comment data
CommentDict = dict  # {author, text, like_count, timestamp, id, replies}
StructuredComments = List[CommentDict]

def fetch_metadata(video_id: str, watch_url: str) -> dict:
    """Fetch video title and channel via yt-dlp; fall back to placeholders."""
    ydl_opts = {"quiet": True, "skip_download": True}
    info = {}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(watch_url, download=False)
    except Exception:
        info = {}

    title = info.get("title") if isinstance(info, dict) else None
    channel = info.get("uploader") if isinstance(info, dict) else None
    canonical = info.get("webpage_url") if isinstance(info, dict) else None
    
    # Extended metadata
    view_count = info.get("view_count") if isinstance(info, dict) else None
    duration = info.get("duration") if isinstance(info, dict) else None
    upload_date = info.get("upload_date") if isinstance(info, dict) else None
    description = info.get("description") if isinstance(info, dict) else None
    tags = info.get("tags") if isinstance(info, dict) else []

    return {
        "Title": title or "(Unknown title)",
        "Channel": channel or "(Unknown channel)",
        "URL": canonical or watch_url,
        "ViewCount": view_count,
        "Duration": duration,
        "UploadDate": upload_date,
        "Description": description,
        "Tags": tags
    }

def try_official_transcript(video_id: str) -> List[str]:
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=OFFICIAL_TRANSCRIPT_LANGS)
    except Exception:
        return []
    return merge_fragments(chunk.text for chunk in transcript)


def try_auto_captions(video_id: str, watch_url: str) -> List[str]:
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
        "-o",
        output_pattern,
        watch_url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return ["(Transcript unavailable: yt-dlp is not installed.)"]
    except subprocess.CalledProcessError:
        cleanup_sidecar_files(video_id, (".info.json",))
        return []
    except Exception as exc:
        cleanup_sidecar_files(video_id, (".info.json",))
        return [f"(Transcript unavailable: {exc})"]

    caption_files = sorted(Path(".").glob(f"{video_id}*.vtt")) + sorted(Path(".").glob(f"{video_id}*.srt"))
    fragments: List[str] = []
    
    # Only use the first caption file to avoid duplicates from multiple language variants
    if caption_files:
        fragments.extend(clean_caption_lines(caption_files[0]))
    
    # Clean up all caption files
    for caption_file in caption_files:
        try:
            caption_file.unlink()
        except OSError:
            pass

    cleanup_sidecar_files(video_id, (".info.json",))
    if not fragments:
        return []
    return merge_fragments(fragments)


def fetch_transcript(video_id: str, watch_url: str) -> List[str]:
    official = try_official_transcript(video_id)
    if official:
        return official

    auto = try_auto_captions(video_id, watch_url)
    if auto:
        return auto

    return ["(Transcript unavailable.)"]


def fetch_comments(
    video_id: str, 
    watch_url: str, 
    max_dl: int = 10000, 
    top_n: int = 20
) -> StructuredComments:
    """
    Fetch comments via yt-dlp and return structured data. Does NOT clean up files - caller must do cleanup.
    """
    info_json_path = Path(f"{video_id}.info.json")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-comments",
        "--write-info-json",
        "--extractor-args",
        f"youtube:max_comments={max_dl};comment_sort=top",
        "--no-write-playlist-metafiles",
        "-o",
        f"{video_id}.%(ext)s",
        watch_url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    def normalise_likes(value) -> int:
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    # Sort root comments by like count (descending) and take top_n
    roots.sort(key=lambda c: normalise_likes(c.get("like_count")), reverse=True)
    top_roots = roots[:top_n]
    
    # Build structured comment data
    structured_comments = []
    for root in top_roots:
        root_replies = children.get(root.get("id"), [])
        replies_sorted = sorted(root_replies, key=lambda r: r.get("timestamp", 0), reverse=True)
        limited_replies = replies_sorted[:50]
        
        structured_comments.append({
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
                for reply in limited_replies
            ]
        })
    
    return structured_comments
