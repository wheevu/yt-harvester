package util

import "testing"

func TestSafePathName(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{name: "normal", input: "Hello World", want: "Hello World"},
		{name: "invalid chars", input: "Hello:/\\*?\"<>|World", want: "Hello World"},
		{name: "empty", input: "   ", want: "untitled"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := SafePathName(tt.input)
			if got != tt.want {
				t.Fatalf("got %q, want %q", got, tt.want)
			}
		})
	}
}

func TestResolveOutputPath(t *testing.T) {
	if got := ResolveOutputPath("report.md", "Ignored", "dQw4w9WgXcQ"); got != "report.txt" {
		t.Fatalf("got %q", got)
	}

	got := ResolveOutputPath("", "Example Title", "dQw4w9WgXcQ")
	want := "output/Example Title [dQw4w9WgXcQ].txt"
	if got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
}
