package util

import (
	"fmt"
	"net/url"
	"regexp"
	"strings"
)

// Source identifies which platform a harvest input belongs to.
type Source string

const (
	SourceYouTube   Source = "youtube"
	SourceInstagram Source = "instagram"
)

// MediaRef is the canonical reference for one harvestable post.
type MediaRef struct {
	Source Source
	ID     string
	URL    string
}

var instagramShortcodePattern = regexp.MustCompile(`^[A-Za-z0-9_-]{5,64}$`)

// DetectMedia routes raw CLI input to a platform, ID, and canonical page URL.
// Bare 11-character IDs stay YouTube so existing usage keeps working;
// Instagram requires a URL because shortcodes alone collide with YouTube IDs.
func DetectMedia(value string) (MediaRef, error) {
	candidate := strings.TrimSpace(value)
	if candidate == "" {
		return MediaRef{}, fmt.Errorf("no video identifier provided")
	}

	if ref, ok := detectInstagramURL(candidate); ok {
		return ref, nil
	}

	if videoID, err := ExtractVideoID(candidate); err == nil {
		return MediaRef{Source: SourceYouTube, ID: videoID, URL: BuildWatchURL(videoID)}, nil
	}

	lowered := strings.ToLower(candidate)
	if strings.Contains(lowered, "instagram.com") {
		return MediaRef{}, fmt.Errorf("unable to extract an Instagram shortcode from the input (expected /reel/<code>, /p/<code> or /tv/<code>)")
	}
	return MediaRef{}, fmt.Errorf("unable to extract a valid YouTube video ID or Instagram reel URL from the input")
}

func detectInstagramURL(value string) (MediaRef, bool) {
	parsed, err := url.Parse(value)
	if err != nil {
		return MediaRef{}, false
	}
	host := strings.ToLower(parsed.Hostname())
	if host != "instagram.com" && host != "www.instagram.com" && host != "m.instagram.com" {
		return MediaRef{}, false
	}

	segments := pathSegments(parsed.Path)
	for index, segment := range segments {
		kind := strings.ToLower(segment)
		if kind != "reel" && kind != "reels" && kind != "p" && kind != "tv" {
			continue
		}
		if index+1 >= len(segments) {
			return MediaRef{}, false
		}
		code := strings.TrimSpace(segments[index+1])
		if !instagramShortcodePattern.MatchString(code) {
			return MediaRef{}, false
		}
		if kind == "reels" {
			kind = "reel"
		}
		return MediaRef{Source: SourceInstagram, ID: code, URL: BuildInstagramURL(kind, code)}, true
	}
	return MediaRef{}, false
}

// BuildInstagramURL returns the canonical page URL for an Instagram post.
func BuildInstagramURL(kind, shortcode string) string {
	kind = strings.ToLower(strings.TrimSpace(kind))
	switch kind {
	case "p", "tv", "reel":
	default:
		kind = "reel"
	}
	return fmt.Sprintf("https://www.instagram.com/%s/%s/", kind, strings.TrimSpace(shortcode))
}
