package cli

import (
	"flag"
	"fmt"
	"strings"
)

type Options struct {
	Input  string
	Output string
}

func Parse(args []string) (Options, error) {
	var opts Options
	positionals := make([]string, 0, 1)

	for index := 0; index < len(args); index++ {
		arg := strings.TrimSpace(args[index])
		switch {
		case arg == "-h" || arg == "--help":
			return Options{}, flag.ErrHelp
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
		case strings.HasPrefix(arg, "-"):
			return Options{}, fmt.Errorf("unknown flag: %s", arg)
		case arg != "":
			positionals = append(positionals, arg)
		}
	}

	if len(positionals) != 1 {
		return Options{}, fmt.Errorf("expected exactly one YouTube video URL or 11-character video ID")
	}

	opts.Input = strings.TrimSpace(positionals[0])
	if opts.Input == "" {
		return Options{}, fmt.Errorf("no video identifier provided")
	}

	return opts, nil
}

func Usage() string {
	return "Usage: yt-harvester [-o FILE] <youtube-url-or-video-id>\n\n" +
		"Build a single .txt report with metadata, timestamped transcript, and comments\n" +
		"from one YouTube video URL or ID.\n"
}
