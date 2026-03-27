package fetch

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/wheevu/yt-harvester/internal/parse"
)

func TestChoosePreferredTrack(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("testdata", "subtitles_inspect.json"))
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}

	info, err := parse.DecodeInfoJSON(data)
	if err != nil {
		t.Fatalf("decode fixture: %v", err)
	}

	selection, ok := choosePreferredTrack(info)
	if !ok {
		t.Fatalf("expected a preferred track")
	}
	if selection.Automatic {
		t.Fatalf("expected manual subtitles to win")
	}
	if selection.Language != "en" {
		t.Fatalf("got language %q", selection.Language)
	}
	if selection.Format != "vtt" {
		t.Fatalf("got format %q", selection.Format)
	}
}

func TestChoosePreferredTrackFallsBackToAutomatic(t *testing.T) {
	info := &parse.InfoJSON{
		AutomaticCaptions: map[string][]parse.SubtitleTrack{
			"en-US": {{Ext: "json3"}, {Ext: "vtt"}},
		},
	}

	selection, ok := choosePreferredTrack(info)
	if !ok {
		t.Fatalf("expected fallback track")
	}
	if !selection.Automatic {
		t.Fatalf("expected automatic captions")
	}
	if selection.Language != "en-US" {
		t.Fatalf("got language %q", selection.Language)
	}
	if selection.Format != "json3" {
		t.Fatalf("got format %q", selection.Format)
	}
}
