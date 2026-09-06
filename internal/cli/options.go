package cli

import (
	"errors"
	"flag"
	"fmt"
	"strings"
)

// ErrVersion is returned by Parse when -v or --version is passed.
var ErrVersion = errors.New("version requested")

type Options struct {
	Input              string
	Output             string
	CookiesFile        string
	CookiesFromBrowser string
}

func Parse(args []string) (Options, error) {
	var opts Options
	positionals := make([]string, 0, 1)

	for index := 0; index < len(args); index++ {
		arg := strings.TrimSpace(args[index])
		switch {
		case arg == "-h" || arg == "--help":
			return Options{}, flag.ErrHelp
		case arg == "-v" || arg == "--version":
			return Options{}, ErrVersion
		case arg == "-o" || arg == "--output":
			if index+1 >= len(args) {
				return Options{}, fmt.Errorf("missing value for %s", arg)
			}
			index++
			opts.Output = strings.TrimSpace(args[index])
		case strings.HasPrefix(arg, "-o="):
			opts.Output = strings.TrimSpace(strings.TrimPrefix(arg, "-o="))
		case strings.HasPrefix(arg, "--output="):
			opts.Output = strings.TrimSpace(strings.TrimPrefix(arg, "--output="))
		case arg == "--cookies":
			if index+1 >= len(args) {
				return Options{}, fmt.Errorf("missing value for %s", arg)
			}
			index++
			opts.CookiesFile = strings.TrimSpace(args[index])
		case strings.HasPrefix(arg, "--cookies="):
			opts.CookiesFile = strings.TrimSpace(strings.TrimPrefix(arg, "--cookies="))
		case arg == "--cookies-from-browser":
			if index+1 >= len(args) {
				return Options{}, fmt.Errorf("missing value for %s", arg)
			}
			index++
			opts.CookiesFromBrowser = strings.TrimSpace(args[index])
		case strings.HasPrefix(arg, "--cookies-from-browser="):
			opts.CookiesFromBrowser = strings.TrimSpace(strings.TrimPrefix(arg, "--cookies-from-browser="))
		case strings.HasPrefix(arg, "-"):
			return Options{}, fmt.Errorf("unknown flag: %s", arg)
		case arg != "":
			positionals = append(positionals, arg)
		}
	}

	if len(positionals) != 1 {
		return Options{}, fmt.Errorf("expected exactly one YouTube video URL/ID or Instagram reel URL")
	}

	opts.Input = strings.TrimSpace(positionals[0])
	if opts.Input == "" {
		return Options{}, fmt.Errorf("no video identifier provided")
	}

	return opts, nil
}

func Usage() string {
	return "Usage: yt-harvester [-o FILE] [--cookies FILE] [--cookies-from-browser BROWSER] <youtube-url-or-video-id|instagram-reel-url>\n\n" +
		"Build a single .txt report with metadata, timestamped transcript, and comments\n" +
		"from one YouTube video or Instagram reel.\n" +
		"Instagram reels are transcribed locally (requires ffmpeg and whisper-cli).\n" +
		"Use --cookies or --cookies-from-browser when Instagram asks for a login.\n"
}
