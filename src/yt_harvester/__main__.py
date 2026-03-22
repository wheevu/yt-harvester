import sys
from pathlib import Path

from .cli import parse_args
from .downloader import fetch_comments, fetch_metadata, fetch_transcript
from .pack import build_video_discussion_pack
from .render import render_discussion_pack
from .utils import (
    build_watch_url,
    cleanup_sidecar_files,
    safe_path_name,
    video_id_from_url,
)

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


def _cleanup_transient_files(video_id: str) -> None:
    cleanup_sidecar_files(
        video_id,
        (
            ".info.json",
            ".live_chat.json",
            ".vtt",
            ".srt",
            ".en.vtt",
            ".en-orig.vtt",
            ".en-en.vtt",
            ".en-de-DE.vtt",
        ),
    )

    for pattern in [f"{video_id}*.vtt", f"{video_id}*.srt"]:
        for file in Path(".").glob(pattern):
            try:
                file.unlink()
            except OSError:
                pass


def main() -> int:
    args = parse_args()

    try:
        video_id = video_id_from_url(args.input)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    watch_url = build_watch_url(video_id)

    try:
        print("Fetching metadata...")
        metadata = fetch_metadata(video_id, watch_url)

        print("Fetching transcript...")
        transcript_segments = fetch_transcript(video_id, watch_url)

        print("Fetching comments...")
        threaded_comments = fetch_comments(video_id, watch_url)

        print("Packing discussion signal...")
        pack = build_video_discussion_pack(
            metadata, transcript_segments, threaded_comments
        )

        output_path = _resolve_output_path(
            args.output, metadata.get("Title", video_id), video_id
        )
        report_text = render_discussion_pack(pack)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")

        print(f"Done: {output_path}")
        return 0
    except Exception as exc:
        print(f"Failed to harvest video discussion pack: {exc}")
        return 1
    finally:
        _cleanup_transient_files(video_id)


if __name__ == "__main__":
    sys.exit(main())
