package parse

import (
	"path/filepath"
	"testing"
)

func TestParseCaptionFile(t *testing.T) {
	segments, err := ParseCaptionFile(filepath.Join("testdata", "sample.vtt"))
	if err != nil {
		t.Fatalf("parse caption file: %v", err)
	}
	if len(segments) != 5 {
		t.Fatalf("got %d segments", len(segments))
	}
	if segments[0].Text != "Hello" {
		t.Fatalf("got first text %q", segments[0].Text)
	}
	if segments[1].Text != "world" {
		t.Fatalf("got second text %q", segments[1].Text)
	}
	if segments[2].Text != ">> Second line" {
		t.Fatalf("got third text %q", segments[2].Text)
	}
	if segments[3].Text != "continues" {
		t.Fatalf("got fourth text %q", segments[3].Text)
	}
	if segments[4].Text != "Same line" {
		t.Fatalf("got last text %q", segments[4].Text)
	}
}
