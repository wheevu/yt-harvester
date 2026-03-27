package fetch

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"github.com/wheevu/yt-harvester/internal/model"
	"github.com/wheevu/yt-harvester/internal/parse"
)

func FetchMetadataAndComments(ctx context.Context, runner *Runner, videoID, watchURL string) (model.Metadata, []model.CommentThread, error) {
	metadata := parse.ExtractMetadata(nil, videoID, watchURL)

	dir, err := os.MkdirTemp("", "yt-harvester-")
	if err != nil {
		return metadata, nil, fmt.Errorf("create temp dir: %w", err)
	}
	defer os.RemoveAll(dir)

	extractorArgs := fmt.Sprintf(
		"youtube:max_comments=%d,%d,%d,%d,%d;comment_sort=top;player_client=default",
		parse.MaxCommentsTotal,
		parse.MaxCommentParents,
		parse.MaxCommentRepliesTotal,
		parse.MaxRepliesPerThread,
		parse.MaxCommentDepth,
	)

	args := []string{
		"--quiet",
		"--no-warnings",
		"--skip-download",
		"--write-comments",
		"--write-info-json",
		"--extractor-args", extractorArgs,
		"--no-write-playlist-metafiles",
		"-o", videoID + ".%(ext)s",
		watchURL,
	}

	// yt-dlp sidecars vary across extractors, so the whole run stays inside one temp directory.
	if err := runner.Run(ctx, dir, args...); err != nil {
		return metadata, nil, err
	}

	info, err := loadInfoJSONFromDir(dir, videoID)
	if err != nil {
		return metadata, nil, err
	}

	metadata = parse.ExtractMetadata(info, videoID, watchURL)
	comments := parse.ExtractCommentThreads(info)
	return metadata, comments, nil
}

func loadInfoJSONFromDir(dir, videoID string) (*parse.InfoJSON, error) {
	primary := filepath.Join(dir, videoID+".info.json")
	candidates := []string{}
	if _, err := os.Stat(primary); err == nil {
		candidates = append(candidates, primary)
	}
	if len(candidates) == 0 {
		matches, err := filepath.Glob(filepath.Join(dir, "*.info.json"))
		if err != nil {
			return nil, fmt.Errorf("glob info json: %w", err)
		}
		candidates = matches
	}
	if len(candidates) == 0 {
		return nil, fmt.Errorf("yt-dlp did not produce an info.json file")
	}

	data, err := os.ReadFile(candidates[0])
	if err != nil {
		return nil, fmt.Errorf("read info json: %w", err)
	}

	info, err := parse.DecodeInfoJSON(data)
	if err != nil {
		return nil, fmt.Errorf("decode info json: %w", err)
	}
	return info, nil
}
