package util

import (
	"fmt"
	"strconv"
	"strings"
	"time"
)

func FormatLikeCount(count int) string {
	if count >= 1_000_000 {
		if count%1_000_000 == 0 {
			return fmt.Sprintf("%dM", count/1_000_000)
		}
		formatted := fmt.Sprintf("%.1fM", float64(count)/1_000_000)
		return strings.TrimRight(strings.TrimRight(formatted, "0"), ".")
	}

	if count >= 1_000 {
		if count%1_000 == 0 {
			return fmt.Sprintf("%dk", count/1_000)
		}
		formatted := fmt.Sprintf("%.1fk", float64(count)/1_000)
		return strings.TrimRight(strings.TrimRight(formatted, "0"), ".")
	}

	return strconv.Itoa(count)
}

func FormatIntWithCommas(value int64) string {
	negative := value < 0
	if negative {
		value = -value
	}

	s := strconv.FormatInt(value, 10)
	if len(s) <= 3 {
		if negative {
			return "-" + s
		}
		return s
	}

	var builder strings.Builder
	if negative {
		builder.WriteByte('-')
	}

	prefix := len(s) % 3
	if prefix == 0 {
		prefix = 3
	}
	builder.WriteString(s[:prefix])
	for index := prefix; index < len(s); index += 3 {
		builder.WriteByte(',')
		builder.WriteString(s[index : index+3])
	}

	return builder.String()
}

func FormatTimestamp(timestamp any) string {
	if timestamp == nil {
		return ""
	}

	switch value := timestamp.(type) {
	case int:
		return time.Unix(int64(value), 0).Format("2006-01-02")
	case int32:
		return time.Unix(int64(value), 0).Format("2006-01-02")
	case int64:
		return time.Unix(value, 0).Format("2006-01-02")
	case float32:
		return time.Unix(int64(value), 0).Format("2006-01-02")
	case float64:
		return time.Unix(int64(value), 0).Format("2006-01-02")
	case string:
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			return ""
		}
		if unixValue, err := strconv.ParseInt(trimmed, 10, 64); err == nil {
			return time.Unix(unixValue, 0).Format("2006-01-02")
		}
		if parsed, err := time.Parse(time.RFC3339, strings.ReplaceAll(trimmed, "Z", "+00:00")); err == nil {
			return parsed.Format("2006-01-02")
		}
		return trimmed
	default:
		return fmt.Sprint(timestamp)
	}
}

func FormatUploadDate(raw string) string {
	value := CompactWhitespace(raw)
	if len(value) == 8 {
		if _, err := strconv.Atoi(value); err == nil {
			return fmt.Sprintf("%s-%s-%s", value[:4], value[4:6], value[6:8])
		}
	}
	if value == "" {
		return "(Unknown date)"
	}
	return value
}

func FormatDuration(durationSeconds int) string {
	if durationSeconds < 0 {
		return "(Unknown duration)"
	}

	hours := durationSeconds / 3600
	minutes := (durationSeconds % 3600) / 60
	seconds := durationSeconds % 60

	if hours > 0 {
		return fmt.Sprintf("%dh %dm %ds", hours, minutes, seconds)
	}
	if minutes > 0 {
		return fmt.Sprintf("%dm %ds", minutes, seconds)
	}
	return fmt.Sprintf("%ds", seconds)
}

func Timecode(seconds float64) string {
	total := int(seconds)
	if total < 0 {
		total = 0
	}

	hours := total / 3600
	minutes := (total % 3600) / 60
	secs := total % 60
	if hours > 0 {
		return fmt.Sprintf("%02d:%02d:%02d", hours, minutes, secs)
	}
	return fmt.Sprintf("%02d:%02d", minutes, secs)
}
