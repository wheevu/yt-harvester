package parse

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDecodeInfoJSONAndExtract(t *testing.T) {
	path := filepath.Join("testdata", "sample.info.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}

	info, err := DecodeInfoJSON(data)
	if err != nil {
		t.Fatalf("decode info json: %v", err)
	}

	metadata := ExtractMetadata(info, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
	if metadata.Title != "Example Title" {
		t.Fatalf("got title %q", metadata.Title)
	}
	if metadata.ViewCount != 1234567 {
		t.Fatalf("got view count %d", metadata.ViewCount)
	}

	threads := ExtractCommentThreads(info)
	if len(threads) != 2 {
		t.Fatalf("got %d threads", len(threads))
	}
	if threads[0].Root.ID != "root1" {
		t.Fatalf("expected root1 first, got %q", threads[0].Root.ID)
	}
	if len(threads[0].Replies) != 2 {
		t.Fatalf("got %d replies", len(threads[0].Replies))
	}
	if threads[0].Replies[0].ID != "reply3" {
		t.Fatalf("expected highest-liked reply first, got %q", threads[0].Replies[0].ID)
	}
}

func TestExtractInstagramMetadata(t *testing.T) {
	path := filepath.Join("testdata", "instagram_info.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}

	info, err := DecodeInfoJSON(data)
	if err != nil {
		t.Fatalf("decode info json: %v", err)
	}

	metadata := ExtractMetadata(info, "DbH3L50RaBS", "https://www.instagram.com/reel/DbH3L50RaBS/")
	if metadata.Title != "Video by thad.codes" {
		t.Fatalf("got title %q", metadata.Title)
	}
	if metadata.Channel != "thad.codes" {
		t.Fatalf("got channel %q", metadata.Channel)
	}
	if metadata.URL != "https://www.instagram.com/reel/DbH3L50RaBS/" {
		t.Fatalf("got url %q", metadata.URL)
	}
	if metadata.ViewCount != -1 {
		t.Fatalf("missing Instagram view count should stay unknown, got %d", metadata.ViewCount)
	}
	if metadata.Duration != -1 {
		t.Fatalf("missing Instagram duration should stay unknown, got %d", metadata.Duration)
	}
	if metadata.UploadDate != "20260723" {
		t.Fatalf("got upload date %q", metadata.UploadDate)
	}

	threads := ExtractCommentThreads(info)
	if len(threads) != 2 {
		t.Fatalf("got %d threads", len(threads))
	}
	if threads[0].Root.ID != "18128054707765007" {
		t.Fatalf("expected highest-liked comment first, got %q", threads[0].Root.ID)
	}
}
