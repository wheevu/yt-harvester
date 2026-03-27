package parse

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"unicode/utf8"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/util"
)

const (
	json3HardGapSeconds           = 1.2
	json3SentenceGapSeconds       = 0.2
	json3SoftSentenceDurationSecs = 10.0
	json3SoftSentenceChars        = 220
	json3SpeakerSplitDurationSecs = 3.0
	json3SpeakerSplitChars        = 60
	json3HardBlockDurationSecs    = 18.0
	json3HardBlockChars           = 360
)

type json3Document struct {
	Events []json3Event `json:"events"`
}

type json3Event struct {
	StartMS    int64      `json:"tStartMs"`
	DurationMS int64      `json:"dDurationMs"`
	Segs       []json3Seg `json:"segs"`
}

type json3Seg struct {
	UTF8 string `json:"utf8"`
}

type json3Cue struct {
	Start float64
	End   float64
	Text  string
}

func ParseJSON3CaptionFile(path string) ([]model.TranscriptSegment, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read json3 caption file: %w", err)
	}
	return ParseJSON3CaptionData(data)
}

func ParseJSON3CaptionData(data []byte) ([]model.TranscriptSegment, error) {
	var document json3Document
	if err := json.Unmarshal(data, &document); err != nil {
		return nil, fmt.Errorf("decode json3 captions: %w", err)
	}

	cues := make([]json3Cue, 0, len(document.Events))
	for _, event := range document.Events {
		text := normalizeJSON3EventText(event.Segs)
		if text == "" {
			continue
		}

		start := float64(event.StartMS) / 1000.0
		duration := float64(event.DurationMS) / 1000.0
		if duration < 0 {
			duration = 0
		}
		end := start + duration
		if end <= start {
			end = start + 0.1
		}

		cues = append(cues, json3Cue{Start: start, End: end, Text: text})
	}

	if len(cues) == 0 {
		return nil, nil
	}

	blocks := buildSentenceBlocks(cues)
	segments := make([]model.TranscriptSegment, 0, len(blocks))
	for _, block := range blocks {
		text := util.CompactWhitespace(block.Text)
		if text == "" {
			continue
		}
		duration := block.End - block.Start
		if duration <= 0 {
			duration = 0.1
		}
		segments = append(segments, model.TranscriptSegment{
			Start:    block.Start,
			Duration: duration,
			Text:     text,
		})
	}

	return segments, nil
}

func normalizeJSON3EventText(segs []json3Seg) string {
	if len(segs) == 0 {
		return ""
	}

	parts := make([]string, 0, len(segs))
	for _, seg := range segs {
		if seg.UTF8 == "" {
			continue
		}
		parts = append(parts, seg.UTF8)
	}

	joined := normalizeCaptionText(strings.Join(parts, ""))
	if joined == "" || joined == "\n" {
		return ""
	}
	return joined
}

func buildSentenceBlocks(cues []json3Cue) []json3Cue {
	blocks := make([]json3Cue, 0, len(cues))
	current := json3Cue{}
	haveCurrent := false

	for index, cue := range cues {
		if !haveCurrent {
			current = cue
			haveCurrent = true
			continue
		}

		if shouldBreakBeforeCue(current, cue) {
			blocks = append(blocks, current)
			current = cue
			continue
		}

		current.End = maxFloat(current.End, cue.End)
		current.Text = util.CompactWhitespace(current.Text + " " + cue.Text)

		var next *json3Cue
		if index+1 < len(cues) {
			next = &cues[index+1]
		}
		if shouldFlushSentenceBlock(current, next) {
			blocks = append(blocks, current)
			haveCurrent = false
		}
	}
	if haveCurrent {
		blocks = append(blocks, current)
	}

	for index := 0; index < len(blocks)-1; index++ {
		nextStart := blocks[index+1].Start
		if blocks[index].End > nextStart {
			blocks[index].End = nextStart
		}
		if blocks[index].End <= blocks[index].Start {
			blocks[index].End = blocks[index].Start + 0.1
		}
	}
	last := len(blocks) - 1
	if last >= 0 && blocks[last].End <= blocks[last].Start {
		blocks[last].End = blocks[last].Start + 0.1
	}

	return blocks
}

func shouldBreakBeforeCue(current, next json3Cue) bool {
	if current.Text == "" {
		return false
	}

	gap := next.Start - current.End
	if gap > json3HardGapSeconds {
		return true
	}
	if startsSpeakerMarker(next.Text) {
		return endsStrongSentence(current.Text) ||
			current.End-current.Start >= json3SpeakerSplitDurationSecs ||
			utf8.RuneCountInString(current.Text) >= json3SpeakerSplitChars
	}
	return false
}

func shouldFlushSentenceBlock(current json3Cue, next *json3Cue) bool {
	if current.Text == "" {
		return false
	}
	if next == nil {
		return true
	}

	duration := current.End - current.Start
	charCount := utf8.RuneCountInString(current.Text)
	gap := next.Start - current.End

	if endsStrongSentence(current.Text) && (gap > json3SentenceGapSeconds || duration >= json3SoftSentenceDurationSecs || charCount >= json3SoftSentenceChars) {
		return true
	}
	if duration >= json3HardBlockDurationSecs || charCount >= json3HardBlockChars {
		return true
	}
	return false
}

func startsSpeakerMarker(value string) bool {
	return strings.HasPrefix(util.CompactWhitespace(value), ">>")
}

func endsStrongSentence(value string) bool {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return false
	}
	for len(trimmed) > 0 {
		last, size := utf8.DecodeLastRuneInString(trimmed)
		switch last {
		case '"', '\'', '”', '’', ')', ']', '}':
			trimmed = strings.TrimSpace(trimmed[:len(trimmed)-size])
			continue
		case '.', '?', '!':
			return true
		default:
			return false
		}
	}
	return false
}

func maxFloat(left, right float64) float64 {
	if right > left {
		return right
	}
	return left
}
