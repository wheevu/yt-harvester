package cli

import "testing"

func TestParseCookieFlags(t *testing.T) {
	opts, err := Parse([]string{"https://www.instagram.com/reel/DbH3L50RaBS/", "--cookies", "cookies.txt", "--cookies-from-browser", "chrome"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if opts.Input != "https://www.instagram.com/reel/DbH3L50RaBS/" {
		t.Fatalf("got input %q", opts.Input)
	}
	if opts.CookiesFile != "cookies.txt" {
		t.Fatalf("got cookies file %q", opts.CookiesFile)
	}
	if opts.CookiesFromBrowser != "chrome" {
		t.Fatalf("got cookies browser %q", opts.CookiesFromBrowser)
	}
}

func TestParseCookieFlagsEqualsForm(t *testing.T) {
	opts, err := Parse([]string{"--cookies=cookies.txt", "dQw4w9WgXcQ"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if opts.CookiesFile != "cookies.txt" {
		t.Fatalf("got cookies file %q", opts.CookiesFile)
	}
}

func TestParseMissingCookiesValue(t *testing.T) {
	if _, err := Parse([]string{"dQw4w9WgXcQ", "--cookies"}); err == nil {
		t.Fatalf("expected error for missing cookies value")
	}
}
