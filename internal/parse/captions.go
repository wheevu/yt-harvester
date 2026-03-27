package parse

import (
	"fmt"
	"html"
	"os"
	"regexp"
	"strconv"
	"strings"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/util"
)

var (
	htmlTagPattern         = regexp.MustCompile(`</?[^>]+>`)
	inlineTimestampPattern = regexp.MustCompile(`<\d{2}:\d{2}:\d{2}\.\d{3}>`)
)

func ParseCaptionFile(path string) ([]model.TranscriptSegment, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read caption file: %w", err)
	}

	contents := strings.ReplaceAll(string(data), "\r\n", "\n")
	lines := strings.Split(contents, "\n")
	segments := make([]model.TranscriptSegment, 0)
	previousFullText := ""

	for index := 0; index < len(lines); {
		line := strings.TrimSpace(lines[index])
		if line == "" || strings.EqualFold(line, "WEBVTT") || strings.HasPrefix(line, "NOTE") {
			index++
			continue
		}

		if isNumericLine(line) && index+1 < len(lines) && strings.Contains(lines[index+1], "-->") {
			index++
			line = strings.TrimSpace(lines[index])
		}

		start, end, ok := parseTimeBounds(line)
		if !ok {
			index++
			continue
		}

		index++
		textLines := make([]string, 0, 2)
		for index < len(lines) {
			current := strings.TrimSpace(lines[index])
			if current == "" {
				break
			}
			if strings.HasPrefix(current, "Kind:") || strings.HasPrefix(current, "Language:") || strings.HasPrefix(current, "Style:") || strings.HasPrefix(current, "Region:") {
				index++
				continue
			}

			cleaned := normalizeCaptionText(current)
			if cleaned != "" {
				textLines = append(textLines, cleaned)
			}
			index++
		}

		fullText := normalizeCaptionText(strings.Join(textLines, " "))
		if fullText != "" {
			emitText := extractIncrementalText(previousFullText, fullText)
			previousFullText = fullText

			duration := end - start
			if duration < 0 {
				duration = 0
			}
			if emitText != "" && (len(segments) == 0 || segments[len(segments)-1].Text != emitText) {
				segments = append(segments, model.TranscriptSegment{
					Start:    start,
					Duration: duration,
					Text:     emitText,
				})
			}
		}

		index++
	}

	return segments, nil
}

func parseTimeBounds(line string) (float64, float64, bool) {
	if !strings.Contains(line, "-->") {
		return 0, 0, false
	}

	parts := strings.SplitN(line, "-->", 2)
	startRaw := strings.ReplaceAll(strings.TrimSpace(parts[0]), ",", ".")
	endFields := strings.Fields(strings.ReplaceAll(strings.TrimSpace(parts[1]), ",", "."))
	if len(endFields) == 0 {
		return 0, 0, false
	}

	start, err := parseTimestampSeconds(startRaw)
	if err != nil {
		return 0, 0, false
	}
	end, err := parseTimestampSeconds(endFields[0])
	if err != nil {
		return 0, 0, false
	}
	if end < start {
		end = start
	}
	return start, end, true
}

func parseTimestampSeconds(raw string) (float64, error) {
	parts := strings.Split(strings.TrimSpace(raw), ":")
	if len(parts) == 0 {
		return 0, fmt.Errorf("empty timestamp")
	}

	toFloat := func(value string) (float64, error) {
		return strconv.ParseFloat(value, 64)
	}

	switch len(parts) {
	case 3:
		hours, err := strconv.Atoi(parts[0])
		if err != nil {
			return 0, err
		}
		minutes, err := strconv.Atoi(parts[1])
		if err != nil {
			return 0, err
		}
		seconds, err := toFloat(parts[2])
		if err != nil {
			return 0, err
		}
		return float64(hours*3600+minutes*60) + seconds, nil
	case 2:
		minutes, err := strconv.Atoi(parts[0])
		if err != nil {
			return 0, err
		}
		seconds, err := toFloat(parts[1])
		if err != nil {
			return 0, err
		}
		return float64(minutes*60) + seconds, nil
	default:
		return toFloat(parts[0])
	}
}

func isNumericLine(value string) bool {
	for _, r := range value {
		if r < '0' || r > '9' {
			return false
		}
	}
	return value != ""
}

func normalizeCaptionText(value string) string {
	cleaned := htmlTagPattern.ReplaceAllString(value, "")
	cleaned = inlineTimestampPattern.ReplaceAllString(cleaned, "")
	cleaned = html.UnescapeString(cleaned)
	return util.CompactWhitespace(cleaned)
}

func extractIncrementalText(previous, current string) string {
	previous = util.CompactWhitespace(previous)
	current = util.CompactWhitespace(current)

	if current == "" {
		return ""
	}
	if previous == "" {
		return current
	}
	if current == previous || strings.Contains(previous, current) {
		return ""
	}
	if strings.HasPrefix(current, previous) {
		return util.CompactWhitespace(strings.TrimSpace(current[len(previous):]))
	}

	previousWords := strings.Fields(previous)
	currentWords := strings.Fields(current)
	maxOverlap := len(previousWords)
	if len(currentWords) < maxOverlap {
		maxOverlap = len(currentWords)
	}

	for overlap := maxOverlap; overlap >= 1; overlap-- {
		if wordSlicesEqual(previousWords[len(previousWords)-overlap:], currentWords[:overlap]) {
			if overlap >= len(currentWords) {
				return ""
			}
			return strings.Join(currentWords[overlap:], " ")
		}
	}

	return current
}

func wordSlicesEqual(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}
