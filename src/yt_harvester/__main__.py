import sys
import json
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .cli import parse_args
from .config import load_config
from .utils import video_id_from_url, build_watch_url, cleanup_sidecar_files, format_like_count, format_timestamp
from .downloader import fetch_metadata, fetch_transcript, fetch_comments
from .processor import analyze_sentiment, extract_keywords

YOUTUBE_HARVESTER_BANNER = r"""
________________________________________________________________________________
________________________________________________________________________________

__   __            _         _          _    _                           _
\ \ / /__  _   _  | |_ _   _| |__   ___| |  | | __ _ _ ____   _____  ___| |_ ___ _ __
 \ V / _ \| | | | | __| | | | '_ \ / _ \ |  | |/ _` | '__\ \ / / _ \/ __| __/ _ \ '__|
  | | (_) | |_| | | |_| |_| | |_) |  __/ |  | | (_| | |   \ V /  __/\__ \ ||  __/ |
  |_|\___/ \__,_|  \__|\__,_|_.__/ \___|_|  |_|\__,_|_|    \_/ \___||___/\__\___|_|

Welcome to YouTube Harvester!
________________________________________________________________________________
________________________________________________________________________________
""".strip("\n")

def format_comments_for_txt(structured_comments):
    """
    Format structured comment data into text lines for display.
    """
    if not structured_comments:
        return ["(No comments found.)"]
    
    def normalise_author(raw_author):
        if not raw_author:
            return "@Unknown"
        raw_author = raw_author.strip()
        return raw_author if raw_author.startswith("@") else f"@{raw_author}"
    
    def render_comment(comment_dict, depth=0):
        indent = "  " * depth
        arrow = "↳ " if depth else ""
        author = normalise_author(comment_dict.get("author"))
        likes = format_like_count(comment_dict.get("like_count", 0))
        text = (comment_dict.get("text") or "").replace("\n", " ").strip()
        
        # Add timestamp for root comments only
        if depth == 0:
            timestamp = comment_dict.get("timestamp")
            time_str = format_timestamp(timestamp)
            time_display = f" [{time_str}]" if time_str else ""
            line = f"{indent}{arrow}{author} (likes: {likes}){time_display}: {text or '(Comment deleted)'}"
        else:
            line = f"{indent}{arrow}{author} (likes: {likes}): {text or '(Comment deleted)'}"
        
        rendered_lines = [line]
        
        for reply in comment_dict.get("replies", []):
            rendered_lines.extend(render_comment(reply, depth + 1))
        
        return rendered_lines
    
    rendered_threads = []
    for root_comment in structured_comments:
        rendered_threads.extend(render_comment(root_comment))
        rendered_threads.append("")
    
    while rendered_threads and rendered_threads[-1] == "":
        rendered_threads.pop()
    
    return rendered_threads if rendered_threads else ["(No comments found.)"]

def save_txt(output_path, meta, transcript, comments, sentiment=None, keywords=None, comments_only=False):
    comment_lines = comments or ["(Comments unavailable.)"]

    with open(output_path, "w", encoding="utf-8") as handle:
        if not comments_only:
            # Full mode: include metadata, analysis, and transcript
            transcript_lines = transcript or ["(Transcript unavailable.)"]
            
            handle.write("====== METADATA ======\n")
            handle.write(f"Title: {meta.get('Title', '(Unknown title)')}\n")
            handle.write(f"Channel: {meta.get('Channel', '(Unknown channel)')}\n")
            handle.write(f"URL: {meta.get('URL', '')}\n")
            if meta.get("ViewCount"):
                handle.write(f"Views: {format_like_count(meta['ViewCount'])}\n")
            if meta.get("UploadDate"):
                handle.write(f"Uploaded: {meta['UploadDate']}\n")
            handle.write("\n")

            if sentiment or keywords:
                handle.write("====== ANALYSIS ======\n")
                if sentiment:
                    handle.write(f"Sentiment: Polarity={sentiment['polarity']:.2f}, Subjectivity={sentiment['subjectivity']:.2f}\n")
                if keywords:
                    handle.write(f"Keywords: {', '.join(keywords)}\n")
                handle.write("\n")

            handle.write("====== TRANSCRIPT ======\n")
            handle.write("\n\n".join(transcript_lines).strip() + "\n\n")

        handle.write("====== COMMENTS ======\n")
        handle.write("\n".join(comment_lines).strip() + "\n")

    return output_path

def save_json(output_path, meta, transcript, comments, sentiment=None, keywords=None, comments_only=False):
    if comments_only:
        # Comments-only mode: just output comments array
        full_data = {"comments": comments}
    else:
        # Full mode: include all sections
        full_data = {
            "metadata": meta,
            "analysis": {
                "sentiment": sentiment,
                "keywords": keywords
            },
            "transcript": transcript,
            "comments": comments
        }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(full_data, handle, indent=2, ensure_ascii=False)
    return output_path

def save_csv(output_path, video_id, structured_comments, append=False):
    """
    Save comments as a flat CSV file for easy import into Google Sheets or Pandas.
    
    Headers: comment_id, video_id, author, comment_text, like_count, timestamp, is_reply, parent_comment_id
    
    Args:
        append: If True, append to existing file without writing headers (for bulk mode)
    """
    mode = "a" if append else "w"
    write_header = not append
    
    with open(output_path, mode, encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow([
                "comment_id",
                "video_id",
                "author",
                "comment_text",
                "like_count",
                "timestamp",
                "is_reply",
                "parent_comment_id"
            ])
        
        for comment in structured_comments:
            # Write the root comment
            writer.writerow([
                comment.get("id", ""),
                video_id,
                comment.get("author", ""),
                comment.get("text", ""),
                comment.get("like_count", 0),
                comment.get("timestamp", ""),
                "false",
                ""
            ])
            
            # Write all replies
            parent_id = comment.get("id", "")
            for reply in comment.get("replies", []):
                writer.writerow([
                    reply.get("id", ""),
                    video_id,
                    reply.get("author", ""),
                    reply.get("text", ""),
                    reply.get("like_count", 0),
                    reply.get("timestamp", ""),
                    "true",
                    parent_id
                ])
    
    return output_path

def process_single_video_for_bulk_csv(url, args, pbar=None):
    """
    Process a video and return comments data for bulk CSV mode.
    Returns: (success, message, (video_id, structured_comments) or None)
    """
    try:
        video_id = video_id_from_url(url)
    except ValueError as exc:
        return False, f"Invalid URL '{url}': {exc}", None
    
    try:
        watch_url = build_watch_url(video_id)
        comment_sort = getattr(args, 'comment_sort', 'top')
        
        if pbar: pbar.set_description(f"Processing {video_id}")

        structured_comments = fetch_comments(
            video_id, 
            watch_url, 
            max_dl=args.max_comments, 
            top_n=args.comments,
            comment_sort=comment_sort
        )
        
        return True, f"✅ {video_id}", (video_id, structured_comments)

    except Exception as exc:
        return False, f"❌ {video_id}: {exc}", None
    
    finally:
        # Always cleanup sidecar files, even if processing fails
        cleanup_sidecar_files(video_id, (
            ".info.json", ".live_chat.json", ".vtt", ".srt", 
            ".en.vtt", ".en-orig.vtt", ".en-en.vtt", ".en-de-DE.vtt"
        ))


def process_single_video(url, args, output_dir=None, pbar=None, progress_callback=None):
    try:
        video_id = video_id_from_url(url)
    except ValueError as exc:
        return False, f"Invalid URL '{url}': {exc}"
    
    watch_url = build_watch_url(video_id)
    comments_only = getattr(args, 'comments_only', False)
    comment_sort = getattr(args, 'comment_sort', 'top')
    
    # Determine output path early
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"{video_id}.{args.format}")
    
    if output_dir:
        output_path = output_dir / output_path.name

    if pbar: pbar.set_description(f"Processing {video_id}")

    try:
        metadata = {}
        transcript = []
        sentiment = None
        keywords = None
        
        if not comments_only:
            # 1. Metadata
            if progress_callback: progress_callback("Fetching metadata...")
            metadata = fetch_metadata(video_id, watch_url)
            
            # 2. Transcript
            if progress_callback: progress_callback("Fetching transcript...")
            transcript = fetch_transcript(video_id, watch_url)
        # In comments-only mode, skip metadata and transcript silently (no progress update)
        
        # 3. Comments (always fetch)
        if progress_callback: progress_callback("Fetching comments...")
        structured_comments = fetch_comments(
            video_id, 
            watch_url, 
            max_dl=args.max_comments, 
            top_n=args.comments,
            comment_sort=comment_sort
        )
        
        # 4. Analysis (skip in comments-only mode)
        if not comments_only:
            if progress_callback: progress_callback("Analyzing content...")
            full_text = " ".join(transcript)
            if not args.no_sentiment:
                sentiment = analyze_sentiment(full_text)
            if not args.no_keywords:
                keywords = extract_keywords(full_text)
        # In comments-only mode, skip analysis silently (no progress update)

        # 5. Save
        if progress_callback: progress_callback("Saving output...")
        if args.format == "csv":
            save_csv(output_path, video_id, structured_comments)
        elif args.format == "json":
            save_json(output_path, metadata, transcript, structured_comments, sentiment, keywords, comments_only)
        else:
            formatted_comments = format_comments_for_txt(structured_comments)
            save_txt(output_path, metadata, transcript, formatted_comments, sentiment, keywords, comments_only)
        
        # Cleanup
        cleanup_sidecar_files(video_id, (
            ".info.json", ".live_chat.json", ".vtt", ".srt", 
            ".en.vtt", ".en-orig.vtt", ".en-en.vtt", ".en-de-DE.vtt"
        ))
        for pattern in [f"{video_id}*.vtt", f"{video_id}*.srt"]:
            for file in Path(".").glob(pattern):
                try:
                    file.unlink()
                except OSError:
                    pass
                    
        return True, f"✅ {video_id} -> {output_path}"

    except Exception as exc:
        return False, f"❌ {video_id}: {exc}"

def main():
    print(YOUTUBE_HARVESTER_BANNER)
    args = parse_args()
    config = load_config()
    
    # Merge config with args if needed
    
    if args.bulk:
        try:
            with open(args.bulk, "r", encoding="utf-8") as f:
                links = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except Exception as e:
            print(f"❌ Error reading bulk file: {e}")
            return 1
            
        if not links:
            print("⚠️ No links found.")
            return 1

        output_dir = Path(args.bulk_output_dir) if args.bulk_output_dir else None
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🚀 Processing {len(links)} videos...")
        
        success_count = 0
        failed_count = 0
        
        # For CSV format in bulk mode, create a combined file
        if args.format == "csv":
            combined_csv_path = (output_dir / "comments.csv") if output_dir else Path("comments.csv")
            # Initialize CSV with headers
            save_csv(combined_csv_path, "", [], append=False)
            
            # Process sequentially to avoid race conditions when appending
            with tqdm(total=len(links), unit="video") as pbar:
                for link in links:
                    success, msg, comments_data = process_single_video_for_bulk_csv(link, args, pbar)
                    if success and comments_data:
                        video_id, structured_comments = comments_data
                        save_csv(combined_csv_path, video_id, structured_comments, append=True)
                        success_count += 1
                    else:
                        failed_count += 1
                        tqdm.write(msg)
                    pbar.update(1)
            
            print(f"\n📊 Done! Success: {success_count}, Failed: {failed_count}")
            if success_count > 0:
                print(f"📁 Combined CSV: {combined_csv_path}")
        else:
            # For other formats, use parallel processing with separate files
            with ThreadPoolExecutor(max_workers=4) as executor:
                with tqdm(total=len(links), unit="video") as pbar:
                    futures = {executor.submit(process_single_video, link, args, output_dir, pbar): link for link in links}
                    
                    for future in as_completed(futures):
                        success, msg = future.result()
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                            tqdm.write(msg)
                        pbar.update(1)
            
            print(f"\n📊 Done! Success: {success_count}, Failed: {failed_count}")
        
        return 0 if failed_count == 0 else 1

    else:
        # Single video mode - validate URL is provided
        if not args.url:
            print("❌ Error: Please provide a YouTube URL or video ID.")
            print("   Usage: yt-harvester <URL>")
            print("   Or use --bulk <file> for batch processing.")
            return 1
        
        # Adjust progress bar steps based on mode
        # Full mode: metadata → transcript → comments → analysis → save (5 steps)
        # Comments-only: comments → save (2 steps)
        total_steps = 2 if args.comments_only else 5
        
        # Single video with detailed progress bar
        with tqdm(total=total_steps, bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}]") as pbar:
            def update_progress(desc):
                pbar.set_description_str(desc)
                pbar.update(1)
            
            success, msg = process_single_video(args.url, args, progress_callback=update_progress)
            
            # Ensure bar completes if successful
            if success and pbar.n < total_steps:
                pbar.update(total_steps - pbar.n)
                
        print(msg)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
