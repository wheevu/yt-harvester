from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path

from .cli import parse_args
from .downloader import fetch_metadata_and_comments, fetch_transcript
from .render import render_report
from .utils import build_watch_url, safe_path_name, video_id_from_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def _resolve_output_path(requested_output: str, title: str, video_id: str) -> Path:
    if requested_output:
        output_path = Path(requested_output)
        if output_path.suffix.lower() != ".txt":
            output_path = output_path.with_suffix(".txt")
        return output_path

    safe_title = safe_path_name(title or video_id)
    return DEFAULT_OUTPUT_DIR / f"{safe_title} [{video_id}].txt"


def main() -> int:
    args = parse_args()

    try:
        video_id = video_id_from_url(args.input)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    watch_url = build_watch_url(video_id)

    try:
        print("Fetching transcript + metadata/comments...")
        # Keep transcript separate: transcript and comment extraction fail independently.
        with ThreadPoolExecutor(max_workers=2) as executor:
            transcript_future = executor.submit(fetch_transcript, video_id, watch_url)
            comments_future = executor.submit(
                fetch_metadata_and_comments, video_id, watch_url
            )

            transcript_segments = transcript_future.result()
            metadata, threaded_comments = comments_future.result()

        print("Rendering report...")
        report_text = render_report(metadata, transcript_segments, threaded_comments)

        output_path = _resolve_output_path(
            args.output, metadata.get("Title", video_id), video_id
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")

        print(f"Done: {output_path}")
        return 0
    except Exception as exc:
        print(f"Failed to harvest video report: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
