package model

type Metadata struct {
	Title      string
	Channel    string
	URL        string
	ViewCount  int64
	Duration   int
	UploadDate string
	VideoID    string
}

type TranscriptSegment struct {
	Start    float64
	Duration float64
	Text     string
}

type Comment struct {
	Author    string
	Text      string
	LikeCount int
	Timestamp any
	ID        string
}

type CommentThread struct {
	Root    Comment
	Replies []Comment
}

type ReportInput struct {
	Metadata   Metadata
	Transcript []TranscriptSegment
	Comments   []CommentThread
}
