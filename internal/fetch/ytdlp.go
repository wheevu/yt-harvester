package fetch

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"github.com/wheevu/yt-harvester/internal/util"
)

var ErrYTDLPNotFound = errors.New("yt-dlp not found on PATH")

type Runner struct {
	Path string
}

func NewRunner() (*Runner, error) {
	path, err := exec.LookPath("yt-dlp")
	if err != nil {
		return nil, ErrYTDLPNotFound
	}
	return &Runner{Path: path}, nil
}

func (r *Runner) Run(ctx context.Context, dir string, args ...string) error {
	_, err := r.exec(ctx, dir, args...)
	return err
}

func (r *Runner) Output(ctx context.Context, dir string, args ...string) ([]byte, error) {
	return r.exec(ctx, dir, args...)
}

func (r *Runner) exec(ctx context.Context, dir string, args ...string) ([]byte, error) {
	// Use CommandContext so canceled fetches terminate the yt-dlp subprocess promptly.
	cmd := exec.CommandContext(ctx, r.Path, args...)
	cmd.Dir = dir
	cmd.WaitDelay = 2 * time.Second

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err == nil {
		return stdout.Bytes(), nil
	}

	if ctxErr := ctx.Err(); ctxErr != nil {
		return nil, fmt.Errorf("yt-dlp canceled: %w", ctxErr)
	}

	stderrText := util.CompactWhitespace(stderr.String())
	if len(stderrText) > 300 {
		stderrText = stderrText[:300] + "..."
	}
	if stderrText != "" {
		return nil, fmt.Errorf("yt-dlp %s: %w: %s", summarizeArgs(args), err, stderrText)
	}
	return nil, fmt.Errorf("yt-dlp %s: %w", summarizeArgs(args), err)
}

func summarizeArgs(args []string) string {
	summary := strings.Join(args, " ")
	if len(summary) > 180 {
		return summary[:180] + "..."
	}
	return summary
}
