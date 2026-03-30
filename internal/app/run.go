package app

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"golang.org/x/sync/errgroup"

	"github.com/wheevu/yt-harvester/internal/cli"
	"github.com/wheevu/yt-harvester/internal/fetch"
	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/parse"
	"github.com/wheevu/yt-harvester/internal/render"
	"github.com/wheevu/yt-harvester/internal/util"
)

func Run(ctx context.Context, opts cli.Options, progress func(string)) (string, error) {
	videoID, err := util.ExtractVideoID(opts.Input)
	if err != nil {
		return "", err
	}

	runner, err := fetch.NewRunner()
	if err != nil {
		return "", fmt.Errorf("yt-dlp is required and must be available on PATH")
	}

	watchURL := util.BuildWatchURL(videoID)
	metadata := parse.ExtractMetadata(nil, videoID, watchURL)
	comments := []model.CommentThread(nil)
	transcript := []model.TranscriptSegment(nil)

	if progress != nil {
		progress("Fetching transcript + metadata/comments...")
	}

	group, groupCtx := errgroup.WithContext(ctx)
	var transcriptErr error
	var metadataErr error

	group.Go(func() error {
		transcript, transcriptErr = fetch.FetchTranscript(groupCtx, runner, videoID, watchURL)
		return nil
	})

	group.Go(func() error {
		metadata, comments, metadataErr = fetch.FetchMetadataAndComments(groupCtx, runner, videoID, watchURL)
		return nil
	})

	if err := group.Wait(); err != nil {
		return "", err
	}
	if ctx.Err() != nil {
		return "", ctx.Err()
	}

	if progress != nil {
		if transcriptErr != nil && len(transcript) == 0 {
			progress("Transcript unavailable: " + transcriptErr.Error())
		}
		if metadataErr != nil && metadata.Title == "(Unknown title)" && len(comments) == 0 {
			progress("Metadata/comments unavailable: " + metadataErr.Error())
		}
	}

	if progress != nil {
		progress("Rendering report...")
	}

	report := render.Render(model.ReportInput{
		Metadata:   metadata,
		Transcript: transcript,
		Comments:   comments,
	})

	outputPath := util.ResolveOutputPath(opts.Output, metadata.Title, videoID)
	if err := os.MkdirAll(filepath.Dir(outputPath), 0o755); err != nil {
		return "", fmt.Errorf("create output directory: %w", err)
	}
	if err := os.WriteFile(outputPath, []byte(report), 0o644); err != nil {
		return "", fmt.Errorf("write report: %w", err)
	}

	return outputPath, nil
}
