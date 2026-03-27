package util

import (
	"html"
	"path/filepath"
	"regexp"
	"strings"
)

var invalidPathCharsPattern = regexp.MustCompile(`[\\/:*?"<>|\x00-\x1f]+`)

func CompactWhitespace(value string) string {
	parts := strings.Fields(value)
	if len(parts) == 0 {
		return ""
	}
	return strings.Join(parts, " ")
}

func SafePathName(value string) string {
	const maxLen = 120

	text := CompactWhitespace(value)
	text = html.UnescapeString(text)
	text = invalidPathCharsPattern.ReplaceAllString(text, " ")
	text = CompactWhitespace(text)
	text = strings.Trim(strings.TrimSpace(text), ". ")

	if text == "" {
		return "untitled"
	}

	runes := []rune(text)
	if len(runes) > maxLen {
		text = strings.Trim(strings.TrimSpace(string(runes[:maxLen])), ". ")
	}

	if text == "" {
		return "untitled"
	}

	return text
}

func ResolveOutputPath(requested, title, videoID string) string {
	requested = strings.TrimSpace(requested)
	if requested != "" {
		ext := strings.ToLower(filepath.Ext(requested))
		if ext != ".txt" {
			base := strings.TrimSuffix(requested, filepath.Ext(requested))
			if base == "" {
				base = requested
			}
			requested = base + ".txt"
		}
		return requested
	}

	safeTitle := SafePathName(title)
	return filepath.Join("output", safeTitle+" ["+videoID+"]"+".txt")
}
