package util

import (
	"fmt"
	"net/url"
	"regexp"
	"strings"
)

var videoIDPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{11}$`)

func ExtractVideoID(value string) (string, error) {
	candidate := strings.TrimSpace(value)
	if candidate == "" {
		return "", fmt.Errorf("no video identifier provided")
	}

	if videoIDPattern.MatchString(candidate) {
		return candidate, nil
	}

	parsed, err := url.Parse(candidate)
	if err == nil {
		host := strings.ToLower(parsed.Hostname())

		if host == "youtu.be" || host == "www.youtu.be" {
			parts := pathSegments(parsed.Path)
			if len(parts) > 0 && videoIDPattern.MatchString(parts[0]) {
				return parts[0], nil
			}
		}

		if strings.HasSuffix(host, "youtube.com") {
			if videoID := parsed.Query().Get("v"); videoIDPattern.MatchString(videoID) {
				return videoID, nil
			}

			parts := pathSegments(parsed.Path)
			if len(parts) >= 2 {
				switch parts[0] {
				case "embed", "shorts", "watch":
					if videoIDPattern.MatchString(parts[1]) {
						return parts[1], nil
					}
				}
			}
		}
	}

	if strings.Contains(candidate, "/") {
		parts := strings.Split(candidate, "/")
		tail := parts[len(parts)-1]
		if videoIDPattern.MatchString(tail) {
			return tail, nil
		}
	}

	return "", fmt.Errorf("unable to extract a valid YouTube video ID from the input")
}

func BuildWatchURL(videoID string) string {
	return fmt.Sprintf("https://www.youtube.com/watch?v=%s", videoID)
}

func pathSegments(value string) []string {
	raw := strings.Split(value, "/")
	segments := make([]string, 0, len(raw))
	for _, part := range raw {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		segments = append(segments, part)
	}
	return segments
}
