package fetch

import (
	"context"
	"errors"
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
