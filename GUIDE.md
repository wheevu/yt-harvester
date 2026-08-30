# YouTube Harvester

A CLI tool that extracts metadata, timestamped transcript and threaded comments. *Previously written in Python.*

## Format

<p align="center">
  <img src="./asset/1.png" width="80%">
</p>

<p align="center">
  <img src="./asset/2.png" width="80%">
</p>

<p align="center">
  <img src="./asset/3.png" width="80%">
</p>

Current comment caps:
- up to `4000` total extracted comments
- up to `300` root comments
- up to `2600` replies across retained threads
- up to `12` replies per retained thread
- maximum comment depth: `2`


## Install

Prerequisites: [Go 1.24+](https://go.dev/dl/) and `yt-dlp` on your `PATH`.

```bash
# Install yt-dlp
brew install yt-dlp

# Global install into $GOPATH/bin (use from any terminal)
go install github.com/wheevu/yt-harvester@latest

# Or from a local clone
git clone https://github.com/wheevu/yt-harvester && cd yt-harvester && go install .
```

Make sure `$GOPATH/bin` (usually `~/go/bin`) is on your `PATH`.

## Usage

```bash
yt-harvester https://www.youtube.com/watch?v=dQw4w9WgXcQ
yt-harvester dQw4w9WgXcQ
```

Optional output path:

```bash
yt-harvester dQw4w9WgXcQ -o report.txt
```

Check version:

```bash
yt-harvester --version
```

If `-o` is omitted, output defaults to:

```text
output/<video title> [<video_id>].txt
```

## Transcript selection order

The tool is yt-dlp-centric. It looks for available subtitle tracks, then chooses:
1. manual English subtitles if available
2. automatic English captions if no manual English track exists

If no transcript is available, the report renders `(Transcript unavailable.)`
