package util

import "testing"

func TestDetectMedia(t *testing.T) {
	tests := []struct {
		name       string
		input      string
		wantSource Source
		wantID     string
		wantURL    string
		wantErr    bool
	}{
		{name: "youtube raw id", input: "dQw4w9WgXcQ", wantSource: SourceYouTube, wantID: "dQw4w9WgXcQ", wantURL: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
		{name: "youtube watch url", input: "https://www.youtube.com/watch?v=dQw4w9WgXcQ", wantSource: SourceYouTube, wantID: "dQw4w9WgXcQ", wantURL: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
		{name: "youtube shorts url", input: "https://www.youtube.com/shorts/dQw4w9WgXcQ", wantSource: SourceYouTube, wantID: "dQw4w9WgXcQ", wantURL: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
		{
			name:       "instagram reel with share token",
			input:      "https://www.instagram.com/reel/DbH3L50RaBS/?stkn=MXRmYW5vbWlrOXNpZQ==",
			wantSource: SourceInstagram,
			wantID:     "DbH3L50RaBS",
			wantURL:    "https://www.instagram.com/reel/DbH3L50RaBS/",
		},
		{
			name:       "instagram post url",
			input:      "https://www.instagram.com/p/aye83DjauH/?foo=bar",
			wantSource: SourceInstagram,
			wantID:     "aye83DjauH",
			wantURL:    "https://www.instagram.com/p/aye83DjauH/",
		},
		{
			name:       "instagram reel with username prefix",
			input:      "https://www.instagram.com/thad.codes/reel/DbH3L50RaBS/",
			wantSource: SourceInstagram,
			wantID:     "DbH3L50RaBS",
			wantURL:    "https://www.instagram.com/reel/DbH3L50RaBS/",
		},
		{name: "instagram url without shortcode", input: "https://www.instagram.com/reel/", wantErr: true},
		{name: "unrelated url", input: "https://example.com/video", wantErr: true},
		{name: "empty", input: "   ", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := DetectMedia(tt.input)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error, got none")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.Source != tt.wantSource || got.ID != tt.wantID || got.URL != tt.wantURL {
				t.Fatalf("got %+v, want source=%q id=%q url=%q", got, tt.wantSource, tt.wantID, tt.wantURL)
			}
		})
	}
}
