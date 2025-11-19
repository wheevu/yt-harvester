import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .cli import parse_args
from .config import load_config
from .utils import video_id_from_url, build_watch_url, cleanup_sidecar_files, format_like_count, format_timestamp
from .downloader import fetch_metadata, fetch_transcript, fetch_comments
from .processor import analyze_sentiment, extract_keywords

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

def save_txt(output_path, meta, transcript, comments, sentiment=None, keywords=None):
    transcript_lines = transcript or ["(Transcript unavailable.)"]
    comment_lines = comments or ["(Comments unavailable.)"]

    with open(output_path, "w", encoding="utf-8") as handle:
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

def save_json(output_path, meta, transcript, comments, sentiment=None, keywords=None):
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

def process_single_video(url, args, output_dir=None, pbar=None, progress_callback=None):
    try:
        video_id = video_id_from_url(url)
    except ValueError as exc:
        return False, f"Invalid URL '{url}': {exc}"
    
    watch_url = build_watch_url(video_id)
    
    # Determine output path early
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"{video_id}.{args.format}")
    
    if output_dir:
        output_path = output_dir / output_path.name

    if pbar: pbar.set_description(f"Processing {video_id}")

    try:
        # 1. Metadata
        if progress_callback: progress_callback("Fetching metadata...")
        metadata = fetch_metadata(video_id, watch_url)
        
        # 2. Transcript
        if progress_callback: progress_callback("Fetching transcript...")
        transcript = fetch_transcript(video_id, watch_url)
        
        # 3. Comments
        if progress_callback: progress_callback("Fetching comments...")
        structured_comments = fetch_comments(
            video_id, 
            watch_url, 
            max_dl=args.max_comments, 
            top_n=args.comments
        )
        
        # 4. Analysis
        if progress_callback: progress_callback("Analyzing content...")
        sentiment = None
        keywords = None
        
        full_text = " ".join(transcript)
        if not args.no_sentiment:
            sentiment = analyze_sentiment(full_text)
        if not args.no_keywords:
            keywords = extract_keywords(full_text)

        # 5. Save
        if progress_callback: progress_callback("Saving output...")
        if args.format == "json":
            save_json(output_path, metadata, transcript, structured_comments, sentiment, keywords)
        else:
            formatted_comments = format_comments_for_txt(structured_comments)
            save_txt(output_path, metadata, transcript, formatted_comments, sentiment, keywords)
        
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
        # Single video with detailed progress bar
        with tqdm(total=5, bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}]") as pbar:
            def update_progress(desc):
                pbar.set_description_str(desc)
                pbar.update(1)
            
            success, msg = process_single_video(args.url, args, progress_callback=update_progress)
            
            # Ensure bar completes if successful
            if success and pbar.n < 5:
                pbar.update(5 - pbar.n)
                
        print(msg)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
