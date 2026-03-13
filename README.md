# YouTube Harvester

A lean CLI that turns one YouTube video into one discussion-ready `.txt` file.

## What it does

For a single video URL or video ID, it always fetches:
- metadata
- transcript (with timestamps preserved)
- threaded comments

Then it produces one text report with:
- a short thesis at the top
- timestamped transcript chunks (`[00:00-00:42] ...`)
- audience themes
- controversial points (side A / side B)
- interesting outliers
- high-signal comments ranked by a thread signal score

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
URL

THESIS
- ...

TRANSCRIPT SNAPSHOT
[00:00-00:42] ...

AUDIENCE THEMES
1. ...

CONTROVERSIAL POINTS
- issue
  - side A
  - side B

INTERESTING OUTLIERS
- comment
  - why it stands out

HIGH-SIGNAL COMMENTS
- score=... likes=... replies=... author=...: ...
```

## Signal scoring

Thread ranking uses a weighted heuristic over:
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
