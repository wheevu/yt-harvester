package fetch

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/parse"
)

func TestBuildTranscriptFallbackChainPrefersManualThenAuto(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("testdata", "subtitles_inspect.json"))
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}

	info, err := parse.DecodeInfoJSON(data)
	if err != nil {
		t.Fatalf("decode fixture: %v", err)
	}

	chain := buildTranscriptFallbackChain(info)
	if len(chain) != 4 {
		t.Fatalf("got %d fallback candidates", len(chain))
	}
	if chain[0].Automatic {
		t.Fatalf("expected manual subtitles first")
	}
	if chain[0].Language != "en" || chain[0].Format != "vtt" {
		t.Fatalf("got first selection %+v", chain[0])
	}
	if chain[0].URL != "https://example.com/manual-en.vtt" {
		t.Fatalf("got first subtitle URL %q", chain[0].URL)
	}
	if chain[1].Automatic || chain[1].Format != "srt" {
		t.Fatalf("got second selection %+v", chain[1])
	}
	if !chain[2].Automatic || chain[2].Format != "json3" {
		t.Fatalf("got third selection %+v", chain[2])
	}
	if !chain[3].Automatic || chain[3].Format != "vtt" {
		t.Fatalf("got fourth selection %+v", chain[3])
	}
}

func TestBuildTranscriptFallbackChainFallsBackToAutomatic(t *testing.T) {
	info := &parse.InfoJSON{
		AutomaticCaptions: map[string][]parse.SubtitleTrack{
			"en-US": {{Ext: "json3"}, {Ext: "vtt"}, {Ext: "srt"}},
		},
	}

	chain := buildTranscriptFallbackChain(info)
	if len(chain) != 3 {
		t.Fatalf("got %d fallback candidates", len(chain))
	}
	for _, selection := range chain {
		if !selection.Automatic {
			t.Fatalf("expected only automatic captions, got %+v", selection)
		}
	}
	if chain[0].Language != "en-US" || chain[0].Format != "json3" {
		t.Fatalf("got first selection %+v", chain[0])
	}
	if chain[1].Format != "vtt" || chain[2].Format != "srt" {
		t.Fatalf("got trailing fallback chain %+v", chain)
	}
}

func TestBuildTranscriptFallbackChainKeepsEnglishOrderDeterministic(t *testing.T) {
	info := &parse.InfoJSON{
		Subtitles: map[string][]parse.SubtitleTrack{
			"en-AU": {{Ext: "vtt"}},
			"en-GB": {{Ext: "vtt"}},
			"en":    {{Ext: "vtt"}},
		},
	}

	chain := buildTranscriptFallbackChain(info)
	if len(chain) != 3 {
		t.Fatalf("got %d fallback candidates", len(chain))
	}
	if chain[0].Language != "en" || chain[1].Language != "en-GB" || chain[2].Language != "en-AU" {
		t.Fatalf("unexpected language order: %+v", chain)
	}
}

func TestRetryTranscriptDownloadRetriesOnRateLimit(t *testing.T) {
	originalBackoffs := transcriptRetryBackoffs
	originalSleep := sleepWithContext
	transcriptRetryBackoffs = []time.Duration{0, 0, 0}
	sleepWithContext = func(context.Context, time.Duration) error { return nil }
	defer func() {
		transcriptRetryBackoffs = originalBackoffs
		sleepWithContext = originalSleep
	}()

	selection := subtitleSelection{Language: "en", Automatic: true, Format: "json3"}
	attempts := 0
	segments, err := retryTranscriptDownload(context.Background(), selection, func() ([]model.TranscriptSegment, error) {
		attempts++
		if attempts < 3 {
			return nil, errors.New("HTTP Error 429: Too Many Requests")
		}
		return []model.TranscriptSegment{{Start: 0, Duration: 1, Text: "ok"}}, nil
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if attempts != 3 {
		t.Fatalf("got %d attempts", attempts)
	}
	if len(segments) != 1 {
		t.Fatalf("got %d segments", len(segments))
	}
}

func TestRetryTranscriptDownloadDoesNotRetryPermanentFailure(t *testing.T) {
	originalBackoffs := transcriptRetryBackoffs
	originalSleep := sleepWithContext
	transcriptRetryBackoffs = []time.Duration{0, 0, 0}
	sleepWithContext = func(context.Context, time.Duration) error { return nil }
	defer func() {
		transcriptRetryBackoffs = originalBackoffs
		sleepWithContext = originalSleep
	}()

	attempts := 0
	_, err := retryTranscriptDownload(context.Background(), subtitleSelection{Language: "en", Automatic: true, Format: "json3"}, func() ([]model.TranscriptSegment, error) {
		attempts++
		return nil, errors.New("unsupported subtitle format")
	})
	if err == nil {
		t.Fatalf("expected error")
	}
	if attempts != 1 {
		t.Fatalf("got %d attempts", attempts)
	}
}

func TestDownloadCaptionTrackUsesSelectedSubtitleURL(t *testing.T) {
	requestPath := ""
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestPath = r.URL.Path
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"events": [{
				"tStartMs": 100,
				"dDurationMs": 900,
				"segs": [{"utf8": "Hello from the selected track"}]
			}]
		}`))
	}))
	defer server.Close()

	segments, err := downloadCaptionTrack(
		context.Background(),
		nil,
		"r-uUUMxt390",
		"https://www.youtube.com/watch?v=r-uUUMxt390",
		subtitleSelection{Language: "en", Automatic: true, Format: "json3", URL: server.URL + "/caption.json3"},
	)
	if err != nil {
		t.Fatalf("download caption track: %v", err)
	}
	if requestPath != "/caption.json3" {
		t.Fatalf("got request path %q", requestPath)
	}
	if len(segments) != 1 || segments[0].Text != "Hello from the selected track" {
		t.Fatalf("got segments %+v", segments)
	}
}

func TestSubtitleInspectionArgsAvoidFormatChecks(t *testing.T) {
	args := strings.Join(subtitleInspectionArgs("https://www.youtube.com/watch?v=r-uUUMxt390", "android_vr"), " ")
	if !strings.Contains(args, "--no-check-formats") {
		t.Fatalf("expected no format checks, got %q", args)
	}
	if !strings.Contains(args, "youtube:player_client=android_vr") {
		t.Fatalf("expected android_vr client, got %q", args)
	}
}

func TestInspectInfoJSONFallsBackAfterClientFailure(t *testing.T) {
	var calls []string
	output := func(_ context.Context, _ string, args ...string) ([]byte, error) {
		call := strings.Join(args, " ")
		calls = append(calls, call)
		if strings.Contains(call, "player_client=default") {
			return nil, errors.New("sign in to confirm you are not a bot")
		}
		return []byte(`{
			"title": "Fallback title",
			"uploader": "Fallback channel",
			"automatic_captions": {
				"en": [{"ext": "json3", "url": "https://example.com/caption.json3"}]
			}
		}`), nil
	}

	info, err := inspectInfoJSONWithOutput(
		context.Background(),
		"https://www.youtube.com/watch?v=r-uUUMxt390",
		output,
		false,
	)
	if err != nil {
		t.Fatalf("inspect info json: %v", err)
	}
	if info.Title != "Fallback title" {
		t.Fatalf("got title %q", info.Title)
	}
	if len(calls) != 2 || !strings.Contains(calls[1], "player_client=android_vr") {
		t.Fatalf("unexpected client calls: %v", calls)
	}
}

func TestSummariseTranscriptFailureRateLimitSummary(t *testing.T) {
	err := summariseTranscriptFailure([]transcriptAttemptOutcome{
		{selection: subtitleSelection{Language: "en", Automatic: true, Format: "json3"}, err: errors.New("HTTP Error 429: Too Many Requests")},
		{selection: subtitleSelection{Language: "en", Automatic: true, Format: "vtt"}, err: errors.New("HTTP Error 429: Too Many Requests")},
	})
	if err == nil {
		t.Fatalf("expected error")
	}
	if !strings.Contains(err.Error(), "rate-limited") {
		t.Fatalf("unexpected summary: %v", err)
	}
	if !strings.Contains(err.Error(), "English transcript tracks") {
		t.Fatalf("unexpected summary: %v", err)
	}
}
