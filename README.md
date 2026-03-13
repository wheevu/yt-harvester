# YouTube Harvester

A lean CLI that turns one YouTube video into one discussion-ready `.txt` file.

## What it does

For a single video URL or video ID, it always fetches:
- metadata
- transcript (with timestamps preserved)
- threaded comments

Then it produces one text report with:
- a short video core at the top
- full timestamped transcript chunks (`[00:00-00:42] ...`)
- audience read + main comment themes
- controversy/split read
- interesting outliers
- top comments with concise `Why` notes

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
<video title> [<video_id>].txt
```

## Report format

```text
TITLE
CHANNEL
DATE
URL

VIDEO CORE
- ...

FULL TIMESTAMPED TRANSCRIPT
[00:00-00:42] ...

AUDIENCE READ
- ...

MAIN COMMENT THEMES
1. ...

CONTROVERSY / SPLIT
- ...

INTERESTING OUTLIERS
- comment
  - Why: ...

TOP COMMENTS
- likes=... replies=... author=...: ...
  - Why: ...
```

## Signal scoring

Comment ranking uses a weighted heuristic over:
- root comment likes
- reply count
- total likes across replies
- unique repliers count
- text quality floor (very short comments are penalized)
- optional recency boost when timestamps exist

## Project layout

```text
src/yt_harvester/
  __main__.py   # one-command orchestration
  cli.py        # minimal CLI args
  downloader.py # metadata/transcript/comments fetch
  pack.py       # chunking, scoring, themes, controversy, outliers, thesis
  render.py     # one txt renderer
  utils.py      # shared helpers
```

## Dependencies

- yt-dlp
- youtube-transcript-api

## Notes

- This version intentionally removes JSON/CSV output, sentiment, keyword extraction, comments-only mode, comment-sort mode, and YAML config.
- Embeddings-based grouping can be added later without changing the one-input, one-output flow.
