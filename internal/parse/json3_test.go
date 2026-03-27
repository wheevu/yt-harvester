package parse

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseJSON3CaptionData(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("testdata", "sample.json3"))
	if err != nil {
		t.Fatalf("read json3 fixture: %v", err)
	}

	segments, err := ParseJSON3CaptionData(data)
	if err != nil {
		t.Fatalf("parse json3 captions: %v", err)
	}

	if len(segments) != 3 {
		t.Fatalf("got %d segments", len(segments))
	}
	if segments[0].Text != "So, in the state of the job market, um, I know whatever I'm going to say is going to sound self-serving, but um." {
		t.Fatalf("got first segment %q", segments[0].Text)
	}
	if segments[1].Text != ">> everybody, it's CJ with getcrack.io, and today I have the pleasure of interviewing Vive." {
		t.Fatalf("got second segment %q", segments[1].Text)
	}
	if segments[2].Text != "Thanks for inviting me to the pod." {
		t.Fatalf("got third segment %q", segments[2].Text)
	}
	if segments[0].Duration <= 0 {
		t.Fatalf("expected positive duration, got %f", segments[0].Duration)
	}
}

func TestParseJSON3CaptionDataPrefersSentenceBoundaryBeforeTimeCutoff(t *testing.T) {
	data := []byte(`{
	  "events": [
	    {"tStartMs": 0, "dDurationMs": 3000, "segs": [{"utf8": "This is a long sentence"}]},
	    {"tStartMs": 2800, "dDurationMs": 3200, "segs": [{"utf8": "that keeps going without"}]},
	    {"tStartMs": 5900, "dDurationMs": 3200, "segs": [{"utf8": "a punctuation cutoff even though"}]},
	    {"tStartMs": 9000, "dDurationMs": 3200, "segs": [{"utf8": "timestamps keep advancing until"}]},
	    {"tStartMs": 12100, "dDurationMs": 3500, "segs": [{"utf8": "the sentence finally ends here."}]},
	    {"tStartMs": 17000, "dDurationMs": 2000, "segs": [{"utf8": "Next sentence."}]}
	  ]
	}`)

	segments, err := ParseJSON3CaptionData(data)
	if err != nil {
		t.Fatalf("parse json3 captions: %v", err)
	}
	if len(segments) != 2 {
		t.Fatalf("got %d segments", len(segments))
	}
	if segments[0].Text != "This is a long sentence that keeps going without a punctuation cutoff even though timestamps keep advancing until the sentence finally ends here." {
		t.Fatalf("got first segment %q", segments[0].Text)
	}
	if segments[0].Duration < 15 {
		t.Fatalf("expected first segment to stay intact until sentence end, got duration %f", segments[0].Duration)
	}
}
