package fetch

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/parse"
)

var preferredTranscriptLanguages = []string{"en", "en-US", "en-GB", "en-CA", "en-AU"}

type subtitleSelection struct {
	Language  string
	Automatic bool
	Format    string
}

func FetchTranscript(ctx context.Context, runner *Runner, videoID, watchURL string) ([]model.TranscriptSegment, error) {
	info, err := inspectSubtitleTracks(ctx, runner, watchURL)
	if err != nil {
		return nil, err
	}

	selection, ok := choosePreferredTrack(info)
	if !ok {
		return nil, nil
	}

	return downloadCaptionTrack(ctx, runner, videoID, watchURL, selection)
}

func inspectSubtitleTracks(ctx context.Context, runner *Runner, watchURL string) (*parse.InfoJSON, error) {
	args := []string{
		"-J",
		"--quiet",
		"--no-warnings",
		"--skip-download",
		"--extractor-args", "youtube:player_client=default",
		watchURL,
	}

	data, err := runner.Output(ctx, "", args...)
	if err != nil {
		return nil, err
	}

	info, err := parse.DecodeInfoJSON(data)
	if err != nil {
		return nil, fmt.Errorf("decode subtitle inspection json: %w", err)
	}
	return info, nil
}

func choosePreferredTrack(info *parse.InfoJSON) (subtitleSelection, bool) {
	if info == nil {
		return subtitleSelection{}, false
	}

	if language, tracks, ok := chooseLanguage(info.Subtitles); ok {
		// Manual subtitles are preferred because they are usually cleaner than generated captions.
		return subtitleSelection{Language: language, Automatic: false, Format: chooseSubtitleFormat(tracks, "vtt", "srt")}, true
	}
	if language, tracks, ok := chooseLanguage(info.AutomaticCaptions); ok {
		return subtitleSelection{Language: language, Automatic: true, Format: chooseSubtitleFormat(tracks, "json3", "vtt", "srt")}, true
	}
	return subtitleSelection{}, false
}

func chooseLanguage(tracks map[string][]parse.SubtitleTrack) (string, []parse.SubtitleTrack, bool) {
	if len(tracks) == 0 {
		return "", nil, false
	}

	for _, preferred := range preferredTranscriptLanguages {
		if usableTrackList(tracks[preferred]) {
			return preferred, tracks[preferred], true
		}
	}

	type fallbackTrack struct {
		language string
		tracks   []parse.SubtitleTrack
	}
	fallbacks := make([]fallbackTrack, 0, len(tracks))
	for language, list := range tracks {
		if usableTrackList(list) && strings.HasPrefix(strings.ToLower(language), "en") {
			fallbacks = append(fallbacks, fallbackTrack{language: language, tracks: list})
		}
	}
	if len(fallbacks) == 0 {
		return "", nil, false
	}

	sort.Slice(fallbacks, func(i, j int) bool {
		return fallbacks[i].language < fallbacks[j].language
	})
	return fallbacks[0].language, fallbacks[0].tracks, true
}

func usableTrackList(tracks []parse.SubtitleTrack) bool {
	return len(tracks) > 0
}

func downloadCaptionTrack(ctx context.Context, runner *Runner, videoID, watchURL string, selection subtitleSelection) ([]model.TranscriptSegment, error) {
	dir, err := os.MkdirTemp("", "yt-harvester-")
	if err != nil {
		return nil, fmt.Errorf("create temp dir: %w", err)
	}
	defer os.RemoveAll(dir)

	args := []string{
		"--quiet",
		"--no-warnings",
		"--skip-download",
		"--sub-format", selection.Format,
		"--sub-langs", selection.Language,
		"--no-write-playlist-metafiles",
		"--extractor-args", "youtube:player_client=default",
		"-o", videoID + ".%(ext)s",
	}
	if selection.Automatic {
		args = append(args, "--write-auto-subs")
	} else {
		args = append(args, "--write-subs")
	}
	args = append(args, watchURL)

	if err := runner.Run(ctx, dir, args...); err != nil {
		return nil, err
	}

	captionPath, err := findCaptionFile(dir, videoID)
	if err != nil {
		return nil, err
	}

	segments, err := parseTranscriptFile(captionPath)
	if err != nil {
		return nil, err
	}
	return segments, nil
}

func chooseSubtitleFormat(tracks []parse.SubtitleTrack, preferred ...string) string {
	available := make(map[string]struct{}, len(tracks))
	for _, track := range tracks {
		ext := strings.TrimSpace(strings.ToLower(track.Ext))
		if ext == "" {
			continue
		}
		available[ext] = struct{}{}
	}

	for _, format := range preferred {
		if _, ok := available[format]; ok {
			return format
		}
	}

	for _, track := range tracks {
		ext := strings.TrimSpace(strings.ToLower(track.Ext))
		if ext != "" {
			return ext
		}
	}

	return "vtt"
}

func parseTranscriptFile(path string) ([]model.TranscriptSegment, error) {
	ext := strings.ToLower(filepath.Ext(path))
	if ext == ".json3" {
		return parse.ParseJSON3CaptionFile(path)
	}
	return parse.ParseCaptionFile(path)
}

func findCaptionFile(dir, videoID string) (string, error) {
	json3Matches, err := filepath.Glob(filepath.Join(dir, videoID+"*.json3"))
	if err != nil {
		return "", fmt.Errorf("glob json3 files: %w", err)
	}
	if len(json3Matches) > 0 {
		return json3Matches[0], nil
	}

	vttMatches, err := filepath.Glob(filepath.Join(dir, videoID+"*.vtt"))
	if err != nil {
		return "", fmt.Errorf("glob vtt files: %w", err)
	}
	if len(vttMatches) > 0 {
		return vttMatches[0], nil
	}

	srtMatches, err := filepath.Glob(filepath.Join(dir, videoID+"*.srt"))
	if err != nil {
		return "", fmt.Errorf("glob srt files: %w", err)
	}
	if len(srtMatches) > 0 {
		return srtMatches[0], nil
	}

	return "", fmt.Errorf("yt-dlp did not produce a subtitle file")
}
