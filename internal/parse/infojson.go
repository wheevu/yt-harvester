package parse

import (
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/util"
)

// These caps keep comment extraction rich enough for discussion without pulling the full long tail.
const (
	MaxCommentsTotal       = 4_000
	MaxCommentParents      = 300
	MaxCommentRepliesTotal = 2_600
	MaxRepliesPerThread    = 12
	MaxCommentDepth        = 2
)

type InfoJSON struct {
	Title             string                     `json:"title"`
	Uploader          string                     `json:"uploader"`
	WebpageURL        string                     `json:"webpage_url"`
	ViewCount         int64                      `json:"view_count"`
	Duration          int                        `json:"duration"`
	UploadDate        string                     `json:"upload_date"`
	Comments          []InfoComment              `json:"comments"`
	Subtitles         map[string][]SubtitleTrack `json:"subtitles"`
	AutomaticCaptions map[string][]SubtitleTrack `json:"automatic_captions"`
}

type InfoComment struct {
	Author    string `json:"author"`
	Text      string `json:"text"`
	LikeCount any    `json:"like_count"`
	Timestamp any    `json:"timestamp"`
	ID        any    `json:"id"`
	Parent    any    `json:"parent"`
}

type SubtitleTrack struct {
	Ext  string `json:"ext"`
	URL  string `json:"url"`
	Name string `json:"name"`
	Kind string `json:"kind"`
}

func DecodeInfoJSON(data []byte) (*InfoJSON, error) {
	var info InfoJSON
	if err := json.Unmarshal(data, &info); err != nil {
		return nil, err
	}
	return &info, nil
}

func ExtractMetadata(info *InfoJSON, videoID, watchURL string) model.Metadata {
	metadata := model.Metadata{
		Title:      "(Unknown title)",
		Channel:    "(Unknown channel)",
		URL:        watchURL,
		ViewCount:  -1,
		Duration:   -1,
		UploadDate: "",
		VideoID:    videoID,
	}

	if info == nil {
		return metadata
	}

	if strings.TrimSpace(info.Title) != "" {
		metadata.Title = info.Title
	}
	if strings.TrimSpace(info.Uploader) != "" {
		metadata.Channel = info.Uploader
	}
	if strings.TrimSpace(info.WebpageURL) != "" {
		metadata.URL = info.WebpageURL
	}
	if info.ViewCount >= 0 {
		metadata.ViewCount = info.ViewCount
	}
	if info.Duration >= 0 {
		metadata.Duration = info.Duration
	}
	metadata.UploadDate = info.UploadDate

	return metadata
}

func ExtractCommentThreads(info *InfoJSON) []model.CommentThread {
	if info == nil || len(info.Comments) == 0 {
		return nil
	}

	children := make(map[string][]model.Comment)
	roots := make([]model.Comment, 0, len(info.Comments))

	for _, raw := range info.Comments {
		comment, ok := normalizeComment(raw)
		if !ok {
			continue
		}

		parent := strings.TrimSpace(stringValue(raw.Parent))
		if parent != "" && parent != "root" {
			children[parent] = append(children[parent], comment)
			continue
		}

		roots = append(roots, comment)
	}

	sort.SliceStable(roots, func(i, j int) bool {
		return roots[i].LikeCount > roots[j].LikeCount
	})

	if len(roots) > MaxCommentParents {
		roots = roots[:MaxCommentParents]
	}

	threads := make([]model.CommentThread, 0, len(roots))
	for _, root := range roots {
		replies := append([]model.Comment(nil), children[root.ID]...)
		sort.SliceStable(replies, func(i, j int) bool {
			if replies[i].LikeCount != replies[j].LikeCount {
				return replies[i].LikeCount > replies[j].LikeCount
			}
			return sortableTimestamp(replies[i].Timestamp) > sortableTimestamp(replies[j].Timestamp)
		})

		if len(replies) > MaxRepliesPerThread {
			replies = replies[:MaxRepliesPerThread]
		}

		threads = append(threads, model.CommentThread{Root: root, Replies: replies})
	}

	return threads
}

func normalizeComment(raw InfoComment) (model.Comment, bool) {
	text := util.CompactWhitespace(raw.Text)
	if text == "" {
		return model.Comment{}, false
	}

	return model.Comment{
		Author:    util.CompactWhitespace(raw.Author),
		Text:      text,
		LikeCount: normalizeLikes(raw.LikeCount),
		Timestamp: raw.Timestamp,
		ID:        stringValue(raw.ID),
	}, true
}

func normalizeLikes(value any) int {
	switch current := value.(type) {
	case nil:
		return 0
	case int:
		if current < 0 {
			return 0
		}
		return current
	case int32:
		if current < 0 {
			return 0
		}
		return int(current)
	case int64:
		if current < 0 {
			return 0
		}
		return int(current)
	case float64:
		if current < 0 {
			return 0
		}
		return int(current)
	case string:
		cleaned := strings.ReplaceAll(strings.TrimSpace(current), ",", "")
		parsed, err := strconv.Atoi(cleaned)
		if err != nil || parsed < 0 {
			return 0
		}
		return parsed
	default:
		return 0
	}
}

func sortableTimestamp(value any) float64 {
	switch current := value.(type) {
	case nil:
		return 0
	case int:
		return float64(current)
	case int32:
		return float64(current)
	case int64:
		return float64(current)
	case float32:
		return float64(current)
	case float64:
		return current
	case string:
		trimmed := strings.TrimSpace(current)
		if trimmed == "" {
			return 0
		}
		if unix, err := strconv.ParseFloat(trimmed, 64); err == nil {
			return unix
		}
		if parsed, err := time.Parse(time.RFC3339, strings.ReplaceAll(trimmed, "Z", "+00:00")); err == nil {
			return float64(parsed.Unix())
		}
		return 0
	default:
		return 0
	}
}

func stringValue(value any) string {
	switch current := value.(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(current)
	default:
		return strings.TrimSpace(fmt.Sprint(value))
	}
}
