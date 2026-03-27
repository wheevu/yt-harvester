# YouTube Harvester

A lean CLI that turns one YouTube video into one raw `.txt` file for reading or LLM discussion.

## What it does

For a single YouTube URL or video ID, it fetches:
- metadata
- timestamped transcript
- threaded comments

Then it produces one text report with exactly these sections:
- `METADATA`
- `TIMESTAMPED TRANSCRIPT`
- `COMMENTS`

The output is intentionally raw and faithful. It does not try to summarize, rank themes, or add analysis layers.

## Install

```bash
pip install -e .
```

## Usage

```bash
yt-harvester https://www.youtube.com/watch?v=dQw4w9WgXcQ
yt-harvester dQw4w9WgXcQ
```

Optional output path:

```bash
yt-harvester dQw4w9WgXcQ -o report.txt
```

If `-o` is omitted, output defaults to:

```text
output/<video title> [<video_id>].txt
```

## Report format

```text
METADATA
Title: ...
Channel: ...
Date: ...
URL: ...
Views: ...
Duration: ...
Video ID: ...

TIMESTAMPED TRANSCRIPT
- [00:00-00:08] ...
- [00:08-00:15] ...

COMMENTS
- likes=... replies=... author=@... [YYYY-MM-DD]: ...
  - reply likes=... author=@... [YYYY-MM-DD]: ...
```

## Performance and cleanup notes

- Metadata and comments are fetched in one yt-dlp pass.
- Transcript fetching runs in parallel with metadata/comments fetching.
- Temporary yt-dlp sidecar files are isolated in a temp directory instead of being written into the repo root.
- Comments are intentionally bounded to keep runtime predictable while still retaining a rich discussion sample.

Current comment caps:
- up to `4000` total extracted comments
- up to `300` root comments
- up to `12` replies per retained thread

These limits are deliberate: they keep the discussion useful without paying extreme latency costs on very large videos.

## Transcript fallback order

The tool tries transcripts in this order:
1. manually created English transcript via `youtube-transcript-api`
2. generated English transcript via `youtube-transcript-api`
3. yt-dlp auto captions fallback

If no transcript is available, the report renders `(Transcript unavailable.)`.

## Project layout

```text
src/yt_harvester/
  __main__.py   # orchestration
  cli.py        # minimal CLI args
  downloader.py # metadata/transcript/comments fetch
  render.py     # txt renderer
  utils.py      # shared helpers
```

## Dependencies

- yt-dlp
- youtube-transcript-api

## Notes

- This version intentionally removes analysis sections like theme clustering, controversy detection, outliers, and comment scoring.
- No API credentials are required.
