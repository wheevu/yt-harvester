# YouTube Harvester 🎬
(First open-source project 🤞🏻, I don't really know if someone has made a tool like this before. Alas, here we are...)

I built this scrappy little Python tool to do the grunt work. It pulls YouTube videos apart and hands you the **good stuff** — transcripts, comments, metadata — in clean, readable files. I built it for personal use, but I'm sharing it here because maybe someone might need it too. 😌

## The Why Behind It 🤔
This whole thing started during a late-night development research rabbit hole. I knew the gold wasn't just in the Youtube videos, but also buried in the comment threads— real discussions, raw feedback, unfiltered ideas. And manually copying everything would have been a nightmare.

While this tool is simple, it's the first step in a bigger picture. My goal was to compile and catalog insights from my research. Once I have enough info in a clean text format, I can start feeding it into other tools to connect dots and find patterns that weren't obvious before.

yt-harvester is the data collection engine for that bigger mission. It turns messy web pages into neat, analyzable data.

## What It Does 🔧

* 📺 **Metadata** — video title, channel name, URL
* 📜 **Transcript** — official or auto-captions, stripped of timecodes
* 💬 **Comments** — top-liked, threaded with replies
* 📁 **Formats** — save as `.txt` or `.json`, up to you
* ✨ **Clean Output** — like counts (e.g., `1.3M`), proper dates, nested replies
* 🌀 **Progress Bar** — lets you know stuff’s happening

---

## Install Me 🛠️

### Step 1: Clone the Repo

```bash
git clone https://github.com/wheevu/yt-harvester.git
cd yt-harvester
```

### Option 1: Install as CLI Tool (Recommended)

```bash
pip install -e .
yt-harvester "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Option 2: Run Directly

```bash
pip install -r requirements.txt
python yt_harvester.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## Use Me 🧠

### Basic (Single Video)

```bash
yt-harvester https://youtube.com/watch?v=dQw4w9WgXcQ
yt-harvester dQw4w9WgXcQ  # just the ID works too
```

### Bulk Processing (Multiple Videos)

Process multiple videos from a file:

```bash
yt-harvester --bulk links.txt
```

Create a text file with one YouTube URL per line:

```
# links.txt
https://www.youtube.com/watch?v=ZncbtRo7RXs
https://www.youtube.com/watch?v=Q3K0TOvTOno
https://youtu.be/g2X2LdJAIpU
# Lines starting with # are ignored
```

Save outputs to a specific directory:

```bash
yt-harvester --bulk links.txt --bulk-output-dir ./outputs
yt-harvester --bulk links.txt -f json --bulk-output-dir ./results -c 30
```

### Options

```bash
-c 10               # Grab 10 top comments only
-f json             # Save as JSON instead of TXT
-o my_file.txt      # Custom output filename (single video only)
--max-comments 20000  # Pull deeper into the comment pit
--bulk FILE         # Process multiple videos from file
--bulk-output-dir DIR  # Output directory for bulk mode
```

Combine as needed:

```bash
# Single video
yt-harvester dQw4w9WgXcQ -c 5 -f json -o output.json

# Bulk processing
yt-harvester --bulk my_videos.txt -c 15 -f json --bulk-output-dir ./downloads
```

### Full CLI Reference

```
positional:
  url                  YouTube video URL or video ID (not used with --bulk)

options:
  -h, --help           Show help
  -c N, --comments N   Top N comments (default: 20)
  -f {txt,json}        Format (default: txt)
  --max-comments N     Cap total comments/replies (default: 10000)
  -o FILE              Custom filename (single video only)
  --bulk FILE          Process multiple videos from file (one URL per line)
  --bulk-output-dir DIR  Output directory for bulk mode
```

---

## Output Samples 🧾

### Text

```
====== METADATA ======
Title: ...
Channel: ...
URL: ...

====== TRANSCRIPT ======
...

====== COMMENTS ======
@user (likes: 2.2M) [2022-07-22]: This video changed my life
  ↳ @replier (likes: 2k): Same here 💯
```

### JSON

```json
{
  "metadata": {...},
  "transcript": ["..."],
  "comments": [
    {
      "author": "@...",
      "text": "...",
      "like_count": 12345,
      "replies": [...]
    }
  ]
}
```

---

## How Comments Are Sorted 🔍

* 🧠 Top N root comments by likes (default 20)
* 🪆 Replies under each root, newest first (up to 50 per root)

---

## Requirements 📦

* Python 3.8+
* [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
* [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api)

---

## Dev Mode 👨🏻‍💻

```bash
git clone https://github.com/wheevu/yt-harvester.git
cd yt-harvester
pip install -e .
# Hack on: src/yt_harvester/__main__.py
```

### Structure

```
yt_harvester/
├── pyproject.toml
├── requirements.txt
└── src/
    └── yt_harvester/
        ├── __init__.py
        └── __main__.py
```

---

## Common Errors & Fixes 😮‍💨

* `ModuleNotFoundError: yt_dlp`

```bash
pip install yt-dlp
```

* `ModuleNotFoundError: youtube_transcript_api`

```bash
pip install youtube-transcript-api
```

* `command not found: yt-harvester`

```bash
pip install -e .
# Make sure your scripts dir is in PATH
```

---

## License 📜

Use it, remix it, just don’t sell NFTs of it (without me).

---

## Credits & Creator ✨

Made with questionable sleep habits by **Josh** 😉
