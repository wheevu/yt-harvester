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
	media, err := util.DetectMedia(opts.Input)
	if err != nil {
		return "", err
	}

	runner, err := fetch.NewRunnerWithCookies(opts.CookiesFile, opts.CookiesFromBrowser)
	if err != nil {
		return "", fmt.Errorf("yt-dlp is required and must be available on PATH")
	}

	videoID := media.ID
	pageURL := media.URL
	metadata := parse.ExtractMetadata(nil, videoID, pageURL)
	comments := []model.CommentThread(nil)
	transcript := []model.TranscriptSegment(nil)

	if progress != nil {
		if media.Source == util.SourceInstagram {
			progress("Fetching Instagram reel metadata/comments + transcribing audio...")
		} else {
			progress("Fetching transcript + metadata/comments...")
		}
	}

	group, groupCtx := errgroup.WithContext(ctx)
	var transcriptErr error
	var metadataErr error
	audioDuration := -1

	group.Go(func() error {
		if media.Source == util.SourceInstagram {
			var duration int
			transcript, duration, transcriptErr = fetch.TranscribeInstagramAudio(groupCtx, runner, videoID, pageURL)
			audioDuration = duration
			return nil
		}
		transcript, transcriptErr = fetch.FetchTranscript(groupCtx, runner, videoID, pageURL)
		return nil
	})

	group.Go(func() error {
		metadata, comments, metadataErr = fetch.FetchMetadataAndComments(groupCtx, runner, videoID, pageURL, media.Source)
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

	// Instagram info-json carries no duration; fall back to the audio length.
	if metadata.Duration < 0 && audioDuration >= 0 {
		metadata.Duration = audioDuration
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
