# YouTube Harvester 🎬

A scrappy little Python tool that pulls YouTube videos apart and hands you the **good stuff** — transcripts, comments, metadata — in clean, readable files. Built because I wanted it. Sharing because maybe you do too. 😌

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

### Basic

```bash
yt-harvester https://youtube.com/watch?v=dQw4w9WgXcQ
yt-harvester dQw4w9WgXcQ  # just the ID works too
```

### Options

```bash
-c 10               # Grab 10 top comments only
-f json             # Save as JSON instead of TXT
-o my_file.txt      # Custom output filename
--max-comments 20000  # Pull deeper into the comment pit
```

Combine as needed:

```bash
yt-harvester dQw4w9WgXcQ -c 5 -f json -o output.json
```

### Full CLI Reference

```
positional:
  url                  YouTube video URL or video ID

options:
  -h, --help           Show help
  -c N, --comments N   Top N comments (default: 20)
  -f {txt,json}        Format (default: txt)
  --max-comments N     Cap total comments/replies (default: 10000)
  -o FILE              Custom filename
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
@user (likes: 1.2M) [2024-05-01]: This video changed my life
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

MIT. Use it, remix it, just don’t sell NFTs of it.

---

## Credits & Creator ✨

Made with questionable sleep habits by **Josh (Huy Vũ)** — just a guy from Vietnam who just wanted to make something cool and useful.

You found this repo? That means it worked. 😊
