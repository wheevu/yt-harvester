package render

import (
	"math"
	"sort"
	"strings"
	"unicode/utf8"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/util"
)

const commentWrapWidth = 100

func Render(input model.ReportInput) string {
	lines := make([]string, 0, 64)
	renderMetadata(&lines, input.Metadata)
	renderTranscript(&lines, input.Transcript)
	renderComments(&lines, input.Comments)
	for len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return strings.Join(lines, "\n") + "\n"
}

func renderMetadata(lines *[]string, metadata model.Metadata) {
	appendLine(lines, "METADATA")
	appendLine(lines, "Title: "+valueOrDefault(metadata.Title, "(Unknown title)"))
	appendLine(lines, "Channel: "+valueOrDefault(metadata.Channel, "(Unknown channel)"))
	appendLine(lines, "Date: "+util.FormatUploadDate(metadata.UploadDate))
	appendLine(lines, "URL: "+metadata.URL)
	if metadata.ViewCount >= 0 {
		appendLine(lines, "Views: "+util.FormatIntWithCommas(metadata.ViewCount))
	} else {
		appendLine(lines, "Views: (Unknown)")
	}
	appendLine(lines, "Duration: "+util.FormatDuration(metadata.Duration))
	appendLine(lines, "Video ID: "+valueOrDefault(metadata.VideoID, "(Unknown id)"))
	appendLine(lines, "")
}

func renderTranscript(lines *[]string, transcript []model.TranscriptSegment) {
	appendLine(lines, "TIMESTAMPED TRANSCRIPT")
	if len(transcript) == 0 {
		appendLine(lines, "(Transcript unavailable.)")
		appendLine(lines, "")
		return
	}

	segments := append([]model.TranscriptSegment(nil), transcript...)
	sort.Slice(segments, func(i, j int) bool {
		return segments[i].Start < segments[j].Start
	})

	printed := 0
	for _, segment := range segments {
		text := util.CompactWhitespace(segment.Text)
		if text == "" {
			continue
		}
		end := segment.Start + segment.Duration
		if end < segment.Start {
			end = segment.Start
		}
		displayStart := math.Floor(segment.Start)
		displayEnd := math.Ceil(end)
		if displayEnd <= displayStart && end > segment.Start {
			displayEnd = displayStart + 1
		}
		appendLine(lines, "- ["+util.Timecode(displayStart)+"-"+util.Timecode(displayEnd)+"] "+text)
		printed++
	}

	if printed == 0 {
		appendLine(lines, "(Transcript unavailable.)")
	}
	appendLine(lines, "")
}

func renderComments(lines *[]string, comments []model.CommentThread) {
	appendLine(lines, "COMMENTS")
	if len(comments) == 0 {
		appendLine(lines, "(No comments found.)")
		appendLine(lines, "")
		return
	}

	// Render retained comment threads directly; the report stays raw by design.
	printed := 0
	for _, thread := range comments {
		rootText := util.CompactWhitespace(thread.Root.Text)
		if rootText == "" {
			continue
		}

		rootWhen := util.FormatTimestamp(thread.Root.Timestamp)
		rootTime := ""
		if rootWhen != "" {
			rootTime = " [" + rootWhen + "]"
		}

		appendLine(lines, "- "+normaliseAuthor(thread.Root.Author)+rootTime+" · "+formatLikesLabel(thread.Root.LikeCount))
		appendWrappedText(lines, rootText, "  ", "  ")
		printed++

		for index, reply := range thread.Replies {
			replyText := util.CompactWhitespace(reply.Text)
			if replyText == "" {
				continue
			}
			replyWhen := util.FormatTimestamp(reply.Timestamp)
			replyTime := ""
			if replyWhen != "" {
				replyTime = " [" + replyWhen + "]"
			}

			branchPrefix := "  ├─ "
			bodyPrefix := "  │  "
			if index == len(thread.Replies)-1 {
				branchPrefix = "  └─ "
				bodyPrefix = "     "
			}

			appendLine(lines, branchPrefix+normaliseAuthor(reply.Author)+replyTime+" · "+formatLikesLabel(reply.LikeCount))
			appendWrappedText(lines, replyText, bodyPrefix, bodyPrefix)
		}
	}

	if printed == 0 {
		appendLine(lines, "(No comments found.)")
	}
	appendLine(lines, "")
}

func normaliseAuthor(raw string) string {
	value := util.CompactWhitespace(raw)
	if value == "" {
		return "@Unknown"
	}
	if strings.HasPrefix(value, "@") {
		return value
	}
	return "@" + value
}

func singleLine(value string, maxLen int) string {
	text := util.CompactWhitespace(value)
	if len(text) <= maxLen {
		return text
	}
	return strings.TrimSpace(text[:maxLen-3]) + "..."
}

func formatLikesLabel(count int) string {
	return util.FormatLikeCount(count) + " likes"
}

func appendWrappedText(lines *[]string, text, firstPrefix, nextPrefix string) {
	wrapped := wrapIndentedText(text, commentWrapWidth, firstPrefix, nextPrefix)
	for _, line := range wrapped {
		appendLine(lines, line)
	}
}

func wrapIndentedText(text string, width int, firstPrefix, nextPrefix string) []string {
	text = util.CompactWhitespace(text)
	if text == "" {
		return nil
	}
	words := strings.Fields(text)
	if len(words) == 0 {
		return nil
	}

	lines := make([]string, 0, 4)
	currentPrefix := firstPrefix
	currentWords := make([]string, 0, 8)
	currentLen := 0

	flush := func() {
		if len(currentWords) == 0 {
			return
		}
		lines = append(lines, currentPrefix+strings.Join(currentWords, " "))
		currentPrefix = nextPrefix
		currentWords = currentWords[:0]
		currentLen = 0
	}

	for _, word := range words {
		wordLen := utf8.RuneCountInString(word)
		lineBudget := width - utf8.RuneCountInString(currentPrefix)
		if lineBudget < 20 {
			lineBudget = 20
		}

		candidateLen := wordLen
		if len(currentWords) > 0 {
			candidateLen = currentLen + 1 + wordLen
		}

		if len(currentWords) > 0 && candidateLen > lineBudget {
			flush()
			lineBudget = width - utf8.RuneCountInString(currentPrefix)
			if lineBudget < 20 {
				lineBudget = 20
			}
		}

		currentWords = append(currentWords, word)
		if len(currentWords) == 1 {
			currentLen = wordLen
		} else {
			currentLen += 1 + wordLen
		}
	}
	flush()

	return lines
}

func valueOrDefault(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func appendLine(lines *[]string, value string) {
	*lines = append(*lines, value)
}
