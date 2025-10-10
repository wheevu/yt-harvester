# YouTube Harvester 🎬

A Python tool to extract metadata, transcripts, and comments from YouTube videos into organized text or JSON files.

## Features ✨

- **Metadata Extraction**: Get video title, channel name, and URL
- **Transcript Harvesting**: Fetch official transcripts or auto-generated captions
- **Comment Collection**: Extract top-liked comments with their replies
- **Flexible Output**: Save as formatted text (.txt) or structured JSON (.json)
- **Smart Formatting**: 
  - Compact like counts (e.g., "1M", "343k")
  - Clean date format (YYYY-MM-DD)
  - Threaded comment display with replies
- **Progress Indicators**: Visual feedback during long operations

## Installation 📦

### Method 1: Install as a Command-Line Tool (Recommended)

```bash
# Clone or download this repository
cd yt_harvester

# Install in editable mode (changes reflect immediately)
pip install -e .

# Now you can use it from anywhere!
yt-harvester "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Method 2: Direct Script Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python yt_harvester.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Usage 🚀

### Basic Usage

```bash
# Using the installed command
yt-harvester "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Or with just the video ID
yt-harvester dQw4w9WgXcQ
```

### Advanced Options

```bash
# Get only 10 top comments
yt-harvester dQw4w9WgXcQ -c 10

# Output as JSON instead of text
yt-harvester dQw4w9WgXcQ -f json

# Specify custom output filename
yt-harvester dQw4w9WgXcQ -o my_video.txt

# Download more comments (default: 10000)
yt-harvester dQw4w9WgXcQ --max-comments 20000

# Combine options
yt-harvester dQw4w9WgXcQ -c 5 -f json -o output.json
```

### Command-Line Options

```
positional arguments:
  url                   YouTube video URL or 11-character video ID

options:
  -h, --help            Show this help message and exit
  -c N, --comments N    Number of top comments to include (default: 20)
  -f {txt,json}, --format {txt,json}
                        Output format (default: txt)
  --max-comments N      Maximum total comments to download including replies (default: 10000)
  -o FILE, --output FILE
                        Output filename (default: VIDEO_ID.txt or VIDEO_ID.json)
```

## Output Format 📄

### Text Format (.txt)

```
====== METADATA ======
Title: Video Title
Channel: Channel Name
URL: https://www.youtube.com/watch?v=...

====== TRANSCRIPT ======
[Full video transcript text...]

====== COMMENTS ======
@Username (likes: 1M) [2020-10-10]: This is the top comment!
  ↳ @Replier (likes: 5k): Great reply!
  ↳ @AnotherUser (likes: 100): Another reply

@SecondUser (likes: 343k) [2021-05-15]: Second top comment
  ↳ @Someone (likes: 2): A reply here
```

### JSON Format (.json)

```json
{
  "metadata": {
    "Title": "Video Title",
    "Channel": "Channel Name",
    "URL": "https://www.youtube.com/watch?v=..."
  },
  "transcript": ["Full transcript text..."],
  "comments": [
    {
      "author": "@Username",
      "text": "Comment text",
      "like_count": 1000000,
      "timestamp": 1602316800,
      "id": "comment_id",
      "replies": [
        {
          "author": "@Replier",
          "text": "Reply text",
          "like_count": 5000,
          "timestamp": 1602403200,
          "id": "reply_id"
        }
      ]
    }
  ]
}
```

## Comment Sorting Logic 🎯

- **Root Comments**: Top 20 (or custom count) sorted by like count (most liked first)
- **Replies**: Up to 50 per root comment, sorted by timestamp (newest first)

## Requirements 📋

- Python 3.8 or higher
- `yt-dlp`: For downloading video metadata and comments
- `youtube-transcript-api`: For fetching video transcripts

## Development 🛠️

```bash
# Clone the repository
git clone https://github.com/yourusername/yt-harvester.git
cd yt-harvester

# Install in editable mode with dependencies
pip install -e .

# Make changes to src/yt_harvester/__main__.py
# Changes are immediately available when you run yt-harvester
```

## Project Structure 📁

```
yt_harvester/
├── pyproject.toml              # Package configuration
├── README.md                   # This file
├── requirements.txt            # Dependencies
└── src/
    └── yt_harvester/
        ├── __init__.py         # Package initialization
        └── __main__.py         # Main script
```

## Troubleshooting 🔧

### "yt-dlp is not installed"
```bash
pip install yt-dlp
```

### "youtube-transcript-api not found"
```bash
pip install youtube-transcript-api
```

### Command not found: yt-harvester
Make sure you installed the package:
```bash
pip install -e .
```

And ensure your Python scripts directory is in your PATH.

## License 📝

MIT License - Feel free to use and modify as needed.

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## Author ✍️

Created with ❤️ for the YouTube research community.
