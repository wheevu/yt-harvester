package render

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/wheevu/yt-harvester/internal/model"
)

func TestRenderGolden(t *testing.T) {
	input := model.ReportInput{
		Metadata: model.Metadata{
			Title:      "Example Title",
			Channel:    "Example Channel",
			URL:        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
			ViewCount:  1234567,
			Duration:   213,
			UploadDate: "20260102",
			VideoID:    "dQw4w9WgXcQ",
		},
		Transcript: []model.TranscriptSegment{
			{Start: 1, Duration: 2, Text: "First line"},
			{Start: 3, Duration: 4, Text: "Second line"},
		},
		Comments: []model.CommentThread{
			{
				Root:    model.Comment{Author: "Alice", Text: "Root comment", LikeCount: 12345, Timestamp: "2026-01-03T12:00:00Z"},
				Replies: []model.Comment{{Author: "Bob", Text: "Reply one", LikeCount: 56, Timestamp: "2026-01-04T12:00:00Z"}},
			},
		},
	}

	got := Render(input)
	wantBytes, err := os.ReadFile(filepath.Join("testdata", "report.golden.txt"))
	if err != nil {
		t.Fatalf("read golden file: %v", err)
	}
	if got != string(wantBytes) {
		t.Fatalf("render output mismatch\n--- got ---\n%s\n--- want ---\n%s", got, string(wantBytes))
	}
	if strings.Contains(got, "author=") || strings.Contains(got, "replies=") {
		t.Fatalf("expected reddit-style comment rendering, got:\n%s", got)
	}
}

func TestRenderTranscriptRoundsSubsecondBounds(t *testing.T) {
	input := model.ReportInput{
		Transcript: []model.TranscriptSegment{{Start: 2.2, Duration: 0.6, Text: "Short cue"}},
	}

	got := Render(input)
	if !strings.Contains(got, "[00:02-00:03] Short cue") {
		t.Fatalf("expected rounded subsecond transcript bounds, got:\n%s", got)
	}
}
