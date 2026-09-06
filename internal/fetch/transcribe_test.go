package fetch

import (
	"os"
	"path/filepath"
	"testing"
)

func TestResolveWhisperModelHonoursEnv(t *testing.T) {
	dir := t.TempDir()
	model := filepath.Join(dir, "ggml-base.en.bin")
	if err := os.WriteFile(model, []byte("fake"), 0o644); err != nil {
		t.Fatalf("write fake model: %v", err)
	}
	t.Setenv("WHISPER_MODEL", model)

	got, err := ResolveWhisperModel()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != model {
		t.Fatalf("got %q, want %q", got, model)
	}
}

func TestResolveWhisperModelMissingEnvPath(t *testing.T) {
	t.Setenv("WHISPER_MODEL", filepath.Join(t.TempDir(), "missing.bin"))
	if _, err := ResolveWhisperModel(); err == nil {
		t.Fatalf("expected error for missing model path")
	}
}

func TestRunnerGlobalArgsForwardsCookies(t *testing.T) {
	runner := &Runner{Path: "yt-dlp", CookiesFile: "cookies.txt", CookiesFromBrowser: "chrome"}
	args := runner.globalArgs()
	joined := ""
	for _, arg := range args {
		joined += arg + " "
	}
	for _, want := range []string{"--cookies", "cookies.txt", "--cookies-from-browser", "chrome"} {
		found := false
		for _, arg := range args {
			if arg == want {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("expected %q in %q", want, joined)
		}
	}

	plain := &Runner{Path: "yt-dlp"}
	if len(plain.globalArgs()) != 0 {
		t.Fatalf("expected no global args without cookies")
	}
}
