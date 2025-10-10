import argparse
import html
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
SENTENCE_ENDINGS = (".", "!", "?", "…")
OFFICIAL_TRANSCRIPT_LANGS = ["en", "en-US", "en-GB", "en-CA", "en-AU"]

# Type alias for structured comment data
CommentDict = dict  # {author, text, like_count, timestamp, id, replies}
StructuredComments = List[CommentDict]


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

    return {
        "Title": title or "(Unknown title)",
        "Channel": channel or "(Unknown channel)",
        "URL": canonical or watch_url,
    }


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
    
    Args:
        video_id: YouTube video ID
        watch_url: Full YouTube URL
        max_dl: Maximum total comments to download (including replies)
        top_n: Number of top root comments to extract
    
    Returns:
        List of structured comment dictionaries with nested replies
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


def format_comments_for_txt(structured_comments: StructuredComments) -> List[str]:
    """
    Format structured comment data into text lines for display.
    
    Args:
        structured_comments: List of structured comment dictionaries
    
    Returns:
        List of formatted comment strings ready for text output
    """
    if not structured_comments:
        return ["(No comments found.)"]
    
    def normalise_author(raw_author: Optional[str]) -> str:
        if not raw_author:
            return "@Unknown"
        raw_author = raw_author.strip()
        return raw_author if raw_author.startswith("@") else f"@{raw_author}"
    
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
    
    def render_comment(comment_dict: dict, depth: int = 0) -> List[str]:
        """Render a single comment with its replies."""
        indent = "  " * depth
        arrow = "↳ " if depth else ""
        author = normalise_author(comment_dict.get("author"))
        likes = format_like_count(comment_dict.get("like_count", 0))
        text = html.unescape((comment_dict.get("text") or "").replace("\n", " ").strip())
        text = re.sub(r"\s+", " ", text)
        
        # Add timestamp for root comments only
        if depth == 0:
            timestamp = comment_dict.get("timestamp")
            time_str = format_timestamp(timestamp)
            time_display = f" [{time_str}]" if time_str else ""
            line = f"{indent}{arrow}{author} (likes: {likes}){time_display}: {text or '(Comment deleted)'}"
        else:
            line = f"{indent}{arrow}{author} (likes: {likes}): {text or '(Comment deleted)'}"
        
        rendered_lines = [line]
        
        # Render replies
        replies = comment_dict.get("replies", [])
        for reply in replies:
            reply_line = render_comment(reply, depth + 1)
            rendered_lines.extend(reply_line)
        
        return rendered_lines
    
    # Render all root comments with their replies
    rendered_threads: List[str] = []
    for root_comment in structured_comments:
        rendered_threads.extend(render_comment(root_comment))
        rendered_threads.append("")  # Blank line between comment threads
    
    # Remove trailing blank lines
    while rendered_threads and rendered_threads[-1] == "":
        rendered_threads.pop()
    
    return rendered_threads if rendered_threads else ["(No comments found.)"]


def save_txt(output_path: str, meta: dict, transcript: List[str], comments: List[str]) -> str:
    transcript_lines = transcript or ["(Transcript unavailable.)"]
    comment_lines = comments or ["(Comments unavailable.)"]

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("====== METADATA ======\n")
        handle.write(f"Title: {meta.get('Title', '(Unknown title)')}\n")
        handle.write(f"Channel: {meta.get('Channel', '(Unknown channel)')}\n")
        handle.write(f"URL: {meta.get('URL', '')}\n\n")

        handle.write("====== TRANSCRIPT ======\n")
        handle.write("\n\n".join(transcript_lines).strip() + "\n\n")

        handle.write("====== COMMENTS ======\n")
        handle.write("\n".join(comment_lines).strip() + "\n")

    return output_path


def save_json(output_path: str, meta: dict, transcript: List[str], comments_data: List[dict]) -> str:
    """Save harvested data in JSON format."""
    full_data = {
        "metadata": meta,
        "transcript": transcript,
        "comments": comments_data
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(full_data, handle, indent=2, ensure_ascii=False)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Harvest transcript and comments from a YouTube video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python yt_harvester.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
  python yt_harvester.py dQw4w9WgXcQ -c 10 -f json
  python yt_harvester.py <URL> --max-comments 5000 -o output.txt
        """
    )
    parser.add_argument(
        "url",
        help="The URL or Video ID of the YouTube video"
    )
    parser.add_argument(
        "-c", "--comments",
        type=int,
        default=20,
        metavar="N",
        help="Number of top-level comments to fetch (sorted by likes). Default: 20"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["txt", "json"],
        default="txt",
        help="Output format. Default: txt"
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=10000,
        metavar="N",
        help="Maximum total comments (including replies) for yt-dlp to download. Default: 10000"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Specify an output file name. Defaults to [video_id].[format]"
    )
    
    args = parser.parse_args()
    
    raw_value = args.url
    try:
        video_id = video_id_from_url(raw_value)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    watch_url = build_watch_url(video_id)

    # Fetch all data first (without cleanup)
    print("📥 Fetching metadata...")
    metadata = fetch_metadata(video_id, watch_url)
    
    print("📝 Fetching transcript...")
    transcript = fetch_transcript(video_id, watch_url)
    
    print("💬 Fetching comments... (this might take a while)")
    structured_comments = fetch_comments(
        video_id, 
        watch_url, 
        max_dl=args.max_comments, 
        top_n=args.comments
    )
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        output_file = f"{video_id}.{args.format}"
    
    # Save the output file in the requested format
    print(f"💾 Saving output...")
    if args.format == "json":
        output_file = save_json(output_file, metadata, transcript, structured_comments)
    else:
        # Format comments for text output
        formatted_comments = format_comments_for_txt(structured_comments)
        output_file = save_txt(output_file, metadata, transcript, formatted_comments)
    
    # Now clean up all temporary files
    print("🧹 Cleaning up temporary files...")
    cleanup_sidecar_files(video_id, (
        ".info.json",
        ".live_chat.json",
        ".vtt",
        ".srt",
        ".en.vtt",
        ".en-orig.vtt",
        ".en-en.vtt",
        ".en-de-DE.vtt",
    ))
    
    # Clean up any remaining caption files with glob patterns
    for pattern in [f"{video_id}*.vtt", f"{video_id}*.srt"]:
        for file in Path(".").glob(pattern):
            try:
                file.unlink()
            except OSError:
                pass
    
    print(f"✅ Harvest complete: {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
