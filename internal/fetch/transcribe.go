package fetch

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/parse"
)

// TranscribeInstagramAudio downloads the best audio track of an Instagram post
// and transcribes it locally with whisper-cli (whisper.cpp). It returns the
// parsed transcript segments and the media duration in whole seconds (-1 when
// the duration could not be determined).
func TranscribeInstagramAudio(ctx context.Context, runner *Runner, videoID, pageURL string) ([]model.TranscriptSegment, int, error) {
	whisperPath, err := exec.LookPath("whisper-cli")
	if err != nil {
		return nil, -1, fmt.Errorf("whisper-cli is required for Instagram transcription and must be available on PATH (brew install whisper-cpp)")
	}
	modelPath, err := ResolveWhisperModel()
	if err != nil {
		return nil, -1, err
	}

	dir, err := os.MkdirTemp("", "yt-harvester-")
	if err != nil {
		return nil, -1, fmt.Errorf("create temp dir: %w", err)
	}
	defer os.RemoveAll(dir)

	audioArgs := []string{
		"--quiet",
		"--no-warnings",
		"-f", "bestaudio/best",
		"--extract-audio",
		"--audio-format", "wav",
		"--audio-quality", "0",
		"--no-write-playlist-metafiles",
		"-o", "audio.%(ext)s",
		pageURL,
	}
	if err := runner.Run(ctx, dir, audioArgs...); err != nil {
		return nil, -1, maybeLoginHint(err)
	}

	audioPath, err := findAudioFile(dir)
	if err != nil {
		return nil, -1, err
	}
	duration := audioDurationSec(ctx, audioPath)

	vttBase := filepath.Join(dir, "transcript")
	whisperArgs := []string{
		"-m", modelPath,
		"-f", audioPath,
		"-l", "auto",
		"-ovtt",
		"-of", vttBase,
		"--no-prints",
	}
	cmd := exec.CommandContext(ctx, whisperPath, whisperArgs...)
	if output, err := cmd.CombinedOutput(); err != nil {
		detail := strings.TrimSpace(string(output))
		if len(detail) > 300 {
			detail = detail[:300] + "..."
		}
		if ctx.Err() != nil {
			return nil, duration, fmt.Errorf("whisper-cli canceled: %w", ctx.Err())
		}
		if detail != "" {
			return nil, duration, fmt.Errorf("whisper-cli: %w: %s", err, detail)
		}
		return nil, duration, fmt.Errorf("whisper-cli: %w", err)
	}

	segments, err := parse.ParseCaptionFile(vttBase + ".vtt")
	if err != nil {
		return nil, duration, fmt.Errorf("parse whisper transcript: %w", err)
	}
	return segments, duration, nil
}

// ResolveWhisperModel locates a whisper.cpp model file. $WHISPER_MODEL wins,
// then the harvester cache, then common install locations.
func ResolveWhisperModel() (string, error) {
	if env := strings.TrimSpace(os.Getenv("WHISPER_MODEL")); env != "" {
		if _, err := os.Stat(env); err != nil {
			return "", fmt.Errorf("whisper model %q not found: %w", env, err)
		}
		return env, nil
	}

	candidates := make([]string, 0, 8)
	if home, err := os.UserHomeDir(); err == nil {
		matches, _ := filepath.Glob(filepath.Join(home, ".cache", "yt-harvester", "ggml-*.bin"))
		candidates = append(candidates, prioritiseModels(matches)...)
		matches, _ = filepath.Glob(filepath.Join(home, ".cache", "whisper", "ggml-*.bin"))
		candidates = append(candidates, prioritiseModels(matches)...)
	}
	matches, _ := filepath.Glob("/opt/homebrew/share/whisper-cpp/ggml-*.bin")
	candidates = append(candidates, prioritiseModels(matches)...)
	matches, _ = filepath.Glob("models/ggml-*.bin")
	candidates = append(candidates, prioritiseModels(matches)...)

	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("no whisper model found: download one, e.g. mkdir -p ~/.cache/yt-harvester && curl -sSL -o ~/.cache/yt-harvester/ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin (or point $WHISPER_MODEL at a ggml-*.bin file)")
}

// prioritiseModels prefers base/small English models over tiny ones.
func prioritiseModels(paths []string) []string {
	rank := func(path string) int {
		base := strings.ToLower(filepath.Base(path))
		switch {
		case strings.Contains(base, "base.en"):
			return 0
		case strings.Contains(base, "small.en"):
			return 1
		case strings.Contains(base, "base"):
			return 2
		case strings.Contains(base, "small"):
			return 3
		default:
			return 4
		}
	}
	ordered := append([]string(nil), paths...)
	for i := 1; i < len(ordered); i++ {
		for j := i; j > 0 && rank(ordered[j]) < rank(ordered[j-1]); j-- {
			ordered[j], ordered[j-1] = ordered[j-1], ordered[j]
		}
	}
	return ordered
}

func findAudioFile(dir string) (string, error) {
	for _, pattern := range []string{"audio.wav", "audio.*"} {
		matches, err := filepath.Glob(filepath.Join(dir, pattern))
		if err != nil {
			return "", fmt.Errorf("glob audio files: %w", err)
		}
		for _, match := range matches {
			if info, err := os.Stat(match); err == nil && !info.IsDir() && info.Size() > 0 {
				return match, nil
			}
		}
	}
	return "", fmt.Errorf("yt-dlp did not produce an audio file")
}

// audioDurationSec reads media duration via ffprobe. Missing ffprobe is not
// fatal; the report renders duration as unknown instead.
func audioDurationSec(ctx context.Context, path string) int {
	ffprobe, err := exec.LookPath("ffprobe")
	if err != nil {
		return -1
	}
	cmd := exec.CommandContext(ctx, ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path)
	output, err := cmd.Output()
	if err != nil {
		return -1
	}
	seconds, err := strconv.ParseFloat(strings.TrimSpace(string(output)), 64)
	if err != nil || seconds < 0 {
		return -1
	}
	return int(seconds)
}

// maybeLoginHint rewrites Instagram auth failures into an actionable message.
func maybeLoginHint(err error) error {
	if err == nil {
		return nil
	}
	message := strings.ToLower(err.Error())
	for _, token := range []string{"login required", "log in", "rate-limit", "rate limit", "429"} {
		if strings.Contains(message, token) {
			return fmt.Errorf("%w (Instagram asked for a login or rate-limited the request; retry with --cookies FILE or --cookies-from-browser chrome)", err)
		}
	}
	return err
}
