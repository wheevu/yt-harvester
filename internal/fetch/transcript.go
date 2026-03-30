package fetch

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/parse"
)

var preferredTranscriptLanguages = []string{"en", "en-US", "en-GB", "en-CA", "en-AU"}

var transcriptRetryBackoffs = []time.Duration{0, 2 * time.Second, 5 * time.Second, 10 * time.Second}

var sleepWithContext = func(ctx context.Context, delay time.Duration) error {
	if delay <= 0 {
		return nil
	}
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

type subtitleSelection struct {
	Language  string
	Automatic bool
	Format    string
}

func (s subtitleSelection) label() string {
	typeLabel := "manual"
	if s.Automatic {
		typeLabel = "auto"
	}
	return fmt.Sprintf("%s/%s/%s", typeLabel, s.Language, s.Format)
}

func FetchTranscript(ctx context.Context, runner *Runner, videoID, watchURL string) ([]model.TranscriptSegment, error) {
	info, err := inspectSubtitleTracks(ctx, runner, watchURL)
	if err != nil {
		return nil, err
	}

	selections := buildTranscriptFallbackChain(info)
	if len(selections) == 0 {
		return nil, nil
	}

	attemptOutcomes := make([]transcriptAttemptOutcome, 0, len(selections))
	for _, selection := range selections {
		// Track metadata can advertise subtitles that still fail to download or parse cleanly.
		segments, err := retryTranscriptDownload(ctx, selection, func() ([]model.TranscriptSegment, error) {
			return downloadCaptionTrack(ctx, runner, videoID, watchURL, selection)
		})
		if err != nil {
			attemptOutcomes = append(attemptOutcomes, transcriptAttemptOutcome{selection: selection, err: err})
			continue
		}
		if len(segments) == 0 {
			attemptOutcomes = append(attemptOutcomes, transcriptAttemptOutcome{selection: selection, empty: true})
			continue
		}
		return segments, nil
	}

	if len(attemptOutcomes) == 0 {
		return nil, nil
	}
	return nil, summariseTranscriptFailure(attemptOutcomes)
}

type transcriptAttemptOutcome struct {
	selection subtitleSelection
	err       error
	empty     bool
}

type transcriptFetchError struct {
	summary string
	detail  string
}

func (e *transcriptFetchError) Error() string {
	return e.summary
}

func (e *transcriptFetchError) Detail() string {
	return e.detail
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

func buildTranscriptFallbackChain(info *parse.InfoJSON) []subtitleSelection {
	if info == nil {
		return nil
	}

	chain := make([]subtitleSelection, 0, 8)
	seen := make(map[subtitleSelection]struct{})

	appendSelections := func(automatic bool, tracks map[string][]parse.SubtitleTrack, preferredFormats ...string) {
		for _, candidate := range chooseLanguages(tracks) {
			formats := chooseSubtitleFormats(candidate.tracks, preferredFormats...)
			if len(formats) == 0 {
				continue
			}
			for _, format := range formats {
				selection := subtitleSelection{
					Language:  candidate.language,
					Automatic: automatic,
					Format:    format,
				}
				if _, ok := seen[selection]; ok {
					continue
				}
				seen[selection] = struct{}{}
				chain = append(chain, selection)
			}
		}
	}

	// Manual subtitles are preferred because they are usually cleaner than generated captions.
	appendSelections(false, info.Subtitles, "vtt", "srt")
	appendSelections(true, info.AutomaticCaptions, "json3", "vtt", "srt")
	return chain
}

type subtitleCandidate struct {
	language string
	tracks   []parse.SubtitleTrack
}

func chooseLanguages(tracks map[string][]parse.SubtitleTrack) []subtitleCandidate {
	if len(tracks) == 0 {
		return nil
	}

	candidates := make([]subtitleCandidate, 0, len(tracks))
	seen := make(map[string]struct{}, len(tracks))

	for _, preferred := range preferredTranscriptLanguages {
		if usableTrackList(tracks[preferred]) {
			candidates = append(candidates, subtitleCandidate{language: preferred, tracks: tracks[preferred]})
			seen[preferred] = struct{}{}
		}
	}

	fallbacks := make([]subtitleCandidate, 0, len(tracks))
	for language, list := range tracks {
		if !usableTrackList(list) || !strings.HasPrefix(strings.ToLower(language), "en") {
			continue
		}
		if _, ok := seen[language]; ok {
			continue
		}
		fallbacks = append(fallbacks, subtitleCandidate{language: language, tracks: list})
	}

	sort.Slice(fallbacks, func(i, j int) bool {
		return fallbacks[i].language < fallbacks[j].language
	})

	return append(candidates, fallbacks...)
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

func retryTranscriptDownload(
	ctx context.Context,
	selection subtitleSelection,
	attempt func() ([]model.TranscriptSegment, error),
) ([]model.TranscriptSegment, error) {
	var lastErr error
	for attemptIndex, delay := range transcriptRetryBackoffs {
		if err := sleepWithContext(ctx, delay); err != nil {
			return nil, err
		}

		segments, err := attempt()
		if err == nil {
			return segments, nil
		}
		lastErr = err
		if !isRetryableTranscriptError(err) || attemptIndex == len(transcriptRetryBackoffs)-1 {
			break
		}
	}
	return nil, lastErr
}

func isRetryableTranscriptError(err error) bool {
	if err == nil {
		return false
	}
	message := strings.ToLower(err.Error())
	for _, token := range []string{
		"429",
		"too many requests",
		"timed out",
		"timeout",
		"temporary failure",
		"connection reset",
		"connection aborted",
		"tls handshake timeout",
	} {
		if strings.Contains(message, token) {
			return true
		}
	}
	return false
}

func summariseTranscriptFailure(outcomes []transcriptAttemptOutcome) error {
	if len(outcomes) == 0 {
		return nil
	}

	allRateLimited := true
	allEmpty := true
	details := make([]string, 0, len(outcomes))
	seenAuto := false
	seenManual := false
	seenEnglish := false

	for _, outcome := range outcomes {
		if outcome.selection.Automatic {
			seenAuto = true
		} else {
			seenManual = true
		}
		if strings.HasPrefix(strings.ToLower(outcome.selection.Language), "en") {
			seenEnglish = true
		}

		if outcome.empty {
			details = append(details, outcome.selection.label()+": parsed empty transcript")
			allRateLimited = false
			continue
		}

		details = append(details, outcome.selection.label()+": "+outcome.err.Error())
		allEmpty = false
		if !isRateLimitTranscriptError(outcome.err) {
			allRateLimited = false
		}
	}

	tried := describeTranscriptTargets(seenManual, seenAuto, seenEnglish)
	if allRateLimited {
		return &transcriptFetchError{
			summary: fmt.Sprintf("YouTube rate-limited subtitle downloads (429) after trying %s.", tried),
			detail:  strings.Join(details, "; "),
		}
	}
	if allEmpty {
		return &transcriptFetchError{
			summary: fmt.Sprintf("Transcript tracks were found, but %s parsed empty.", tried),
			detail:  strings.Join(details, "; "),
		}
	}
	return &transcriptFetchError{
		summary: fmt.Sprintf("Transcript unavailable after trying %s.", tried),
		detail:  strings.Join(details, "; "),
	}
}

func isRateLimitTranscriptError(err error) bool {
	if err == nil {
		return false
	}
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "429") || strings.Contains(message, "too many requests")
}

func describeTranscriptTargets(seenManual, seenAuto, seenEnglish bool) string {
	languageLabel := "available transcript tracks"
	if seenEnglish {
		languageLabel = "English transcript tracks"
	}
	switch {
	case seenManual && seenAuto:
		return languageLabel + " (manual subtitles and auto-captions)"
	case seenManual:
		return languageLabel + " (manual subtitles)"
	case seenAuto:
		return languageLabel + " (auto-captions)"
	default:
		return languageLabel
	}
}

func chooseSubtitleFormats(tracks []parse.SubtitleTrack, preferred ...string) []string {
	available := make(map[string]struct{}, len(tracks))
	for _, track := range tracks {
		ext := strings.TrimSpace(strings.ToLower(track.Ext))
		if ext == "" {
			continue
		}
		available[ext] = struct{}{}
	}

	formats := make([]string, 0, len(available))
	seen := make(map[string]struct{}, len(available))
	for _, format := range preferred {
		if _, ok := available[format]; ok {
			formats = append(formats, format)
			seen[format] = struct{}{}
		}
	}

	return formats
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
