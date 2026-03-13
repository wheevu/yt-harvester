import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "against",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "even",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

GENERIC_THEME_TERMS = {
    "video",
    "people",
    "everyone",
    "thing",
    "stuff",
    "really",
    "today",
    "still",
    "new",
    "got",
    "one",
    "link",
    "like",
    "time",
}

PRO_STANCE_WORDS = {
    "accurate",
    "agree",
    "awesome",
    "correct",
    "facts",
    "good",
    "great",
    "helpful",
    "insightful",
    "love",
    "right",
    "true",
    "valid",
    "yes",
    "timeless",
    "classic",
    "enjoy",
}
CON_STANCE_WORDS = {
    "bad",
    "biased",
    "bs",
    "bullshit",
    "disagree",
    "fake",
    "false",
    "hate",
    "misleading",
    "nonsense",
    "overrated",
    "problem",
    "wrong",
    "annoying",
    "arrogant",
    "ego",
    "condescending",
}

HOST_TERMS = {"host", "interviewer", "podcast", "moderator"}
GUEST_TERMS = {"guest", "interviewee"}

HUMOR_TERMS = {
    "lol",
    "lmao",
    "meme",
    "joke",
    "funny",
    "rickroll",
    "rickrolled",
    "prank",
    "haha",
}

MILESTONE_TERMS = {"billion", "million", "views", "600m", "milestone"}
APPRECIATION_TERMS = {
    "actually",
    "enjoy",
    "love",
    "great",
    "banger",
    "banging",
    "classic",
    "song",
}
SPREAD_TERMS = {
    "link",
    "sent",
    "clicked",
    "professor",
    "friend",
    "recommended",
    "recommend",
}

JOKE_CONTEXT_TERMS = {
    "rickroll",
    "rickrolled",
    "prank",
    "link",
    "sent",
    "clicked",
    "bait",
    "meme",
}

TECH_CRIT_TERMS = {
    "technical",
    "depth",
    "code",
    "coding",
    "engineer",
    "engineering",
    "architecture",
    "system",
    "scalable",
    "complexity",
    "vague",
    "surface",
    "shallow",
}

THEME_LABEL_PATTERNS: List[Tuple[str, Set[str]]] = [
    (
        "Disillusionment with big tech",
        {
            "big",
            "tech",
            "corporate",
            "faang",
            "layoff",
            "burnout",
            "startup",
            "industry",
            "rat",
            "race",
        },
    ),
    (
        "Guest lacks technical depth",
        {
            "guest",
            "technical",
            "depth",
            "surface",
            "vague",
            "generic",
            "shallow",
        },
    ),
    (
        "Criticism of host arrogance",
        {
            "host",
            "arrogant",
            "ego",
            "interrupt",
            "condescending",
            "talks",
            "over",
        },
    ),
    (
        "Career confusion and poor fit",
        {
            "career",
            "fit",
            "job",
            "switch",
            "path",
            "confused",
            "direction",
            "quit",
        },
    ),
    (
        "Playful rickroll reactions",
        {"rickroll", "rickrolled", "prank", "tricked", "discord", "tumblr"},
    ),
    (
        "People getting sent the link",
        {
            "link",
            "sent",
            "clicked",
            "professor",
            "friend",
            "exam",
            "recommend",
            "recommended",
        },
    ),
    (
        "Meme longevity and internet nostalgia",
        {
            "meme",
            "never",
            "die",
            "still",
            "exists",
            "legacy",
            "classic",
            "years",
        },
    ),
    (
        "View milestones and lasting reach",
        {"billion", "million", "views", "numbers", "600m", "hit"},
    ),
    (
        "Genuine appreciation of the song",
        {"song", "music", "enjoy", "love", "actually", "unironically", "great"},
    ),
    (
        "Artist look and voice reactions",
        {"voice", "looks", "young", "deep", "appearance"},
    ),
    (
        "Platform and algorithm jokes",
        {"youtube", "algorithm", "recommended", "staff", "flag", "nudity"},
    ),
]

_THEME_INTERPRETATION_MAP = {
    "Disillusionment with big tech": "Commenters frame the discussion as a broader frustration with corporate tech culture, not just an isolated personal story.",
    "Guest lacks technical depth": "The thread questions whether the guest offers concrete technical insight, with many viewers calling the points too surface-level.",
    "Criticism of host arrogance": "This cluster pushes back on the host's tone and delivery, saying style got in the way of substance.",
    "Career confusion and poor fit": "Commenters interpret the situation as a mismatch between expectations, role fit, and career direction.",
    "Playful rickroll reactions": "This cluster is mostly quick meme reactions and side jokes that keep the rickroll format alive.",
    "People getting sent the link": "A large share of replies are story-style comments about being tricked, baited, or unexpectedly sent this video.",
    "Meme longevity and internet nostalgia": "Viewers treat the moment as internet history and celebrate how long the meme has survived.",
    "View milestones and lasting reach": "This theme centers on scale and longevity, with people highlighting major view-count milestones.",
    "Genuine appreciation of the song": "Beyond the meme, commenters explicitly say they enjoy the track on its own musical merit.",
    "Artist look and voice reactions": "The focus here shifts to Rick Astley's persona, especially the contrast between his appearance and voice.",
    "Platform and algorithm jokes": "These comments make meta jokes about recommendation systems, moderation, or platform behavior.",
}

_NON_SPEECH_BRACKET_RE = re.compile(r"\[(?:[^\]]{0,40})\]")
_NON_SPEECH_PAREN_RE = re.compile(
    r"\((?:[^)]*(music|applause|laughter|laughs|cheering|crowd|silence|sigh|breath)[^)]*)\)",
    re.IGNORECASE,
)

_FIRSTHAND_PATTERNS = [
    re.compile(r"\bas someone who\b", re.IGNORECASE),
    re.compile(r"\bi work(?:ed)? in\b", re.IGNORECASE),
    re.compile(r"\bfrom my experience\b", re.IGNORECASE),
    re.compile(r"\bin my (?:company|team|industry|field)\b", re.IGNORECASE),
]


@dataclass
class TranscriptChunk:
    index: int
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class ScoredComment:
    comment_id: str
    author: str
    text: str
    timestamp: Any
    like_count: int
    replies: List[Dict[str, Any]] = field(default_factory=list)
    reply_count: int = 0
    total_reply_likes: int = 0
    unique_repliers: int = 0
    signal_score: float = 0.0
    token_set: Set[str] = field(default_factory=set)
    assigned_theme_id: Optional[str] = None
    why_it_matters: str = ""


@dataclass
class ThemeCluster:
    theme_id: str
    name: str
    interpretation: str
    comment_ids: List[str] = field(default_factory=list)
    representative_comment_ids: List[str] = field(default_factory=list)
    evidence_terms: List[str] = field(default_factory=list)


@dataclass
class Controversy:
    issue: str
    level: str
    summary: str
    representative_comment_ids: List[str] = field(default_factory=list)


@dataclass
class Outlier:
    comment_id: str
    reason: str


@dataclass
class VideoDiscussionPack:
    metadata: Dict[str, Any]
    thesis: List[str]
    transcript_chunks: List[TranscriptChunk]
    threaded_comments: List[Dict[str, Any]]
    scored_comments: List[ScoredComment]
    theme_clusters: List[ThemeCluster]
    controversies: List[Controversy]
    outliers: List[Outlier]
    audience_read: List[str]
    split_level: str


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _tokenize(value: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9']+", (value or "").lower())
    return [
        tok
        for tok in tokens
        if len(tok) >= 3 and tok not in STOPWORDS and not tok.isdigit()
    ]


def _safe_int(value: Any) -> int:
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _timestamp_to_epoch(timestamp: Any) -> Optional[float]:
    if isinstance(timestamp, (int, float)):
        if timestamp > 0:
            return float(timestamp)
        return None

    if isinstance(timestamp, str) and timestamp.strip():
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None

    return None


def _jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    overlap = len(a.intersection(b))
    union = len(a.union(b))
    if union == 0:
        return 0.0
    return overlap / float(union)


def _clean_transcript_text(text: str) -> str:
    cleaned = _normalise_text(text)
    if not cleaned:
        return ""

    cleaned = _NON_SPEECH_BRACKET_RE.sub(" ", cleaned)
    cleaned = _NON_SPEECH_PAREN_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("♪", " ")
    cleaned = re.sub(r"\b(uh+|um+|erm+)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—")
    return cleaned


def _is_refrain_like(text: str) -> bool:
    tokens = [tok for tok in re.findall(r"[a-zA-Z']+", text.lower()) if tok]
    if len(tokens) < 20:
        return False

    ngram_counts = Counter()
    for i in range(len(tokens) - 4):
        ngram = tuple(tokens[i : i + 5])
        ngram_counts[ngram] += 1

    repeated = [count for count in ngram_counts.values() if count >= 3]
    return bool(repeated)


def _extract_short_excerpt(text: str, max_chars: int = 220) -> str:
    words = text.split()
    if len(words) > 24:
        text = " ".join(words[:24]).rstrip(" ,.;:!?") + "..."

    if len(text) <= max_chars:
        return text

    sentences = [
        part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()
    ]
    if sentences:
        selected: List[str] = []
        size = 0
        for sentence in sentences:
            projected = size + len(sentence) + (1 if selected else 0)
            if projected > max_chars and selected:
                break
            selected.append(sentence)
            size = projected
            if size >= int(max_chars * 0.75):
                break
        result = " ".join(selected)
        return (
            result
            if len(result) <= max_chars
            else f"{result[: max_chars - 3].rstrip()}..."
        )

    return f"{text[: max_chars - 3].rstrip()}..."


def _percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(max(int(round((len(ordered) - 1) * pct)), 0), len(ordered) - 1)
    return ordered[index]


def _is_official_author(author: str, metadata: Dict[str, Any]) -> bool:
    raw_author = (author or "").strip().lower().lstrip("@")
    if not raw_author:
        return False

    channel = str(metadata.get("Channel") or "").strip().lower()
    channel = re.sub(r"\s+", "", channel)
    compact_author = re.sub(r"\s+", "", raw_author)

    if raw_author == "youtube":
        return True
    if channel and (compact_author == channel or channel in compact_author):
        return True
    return False


def _looks_firsthand(text: str) -> bool:
    candidate = text or ""
    return any(pattern.search(candidate) for pattern in _FIRSTHAND_PATTERNS)


def _contains_negative(text: str) -> bool:
    tokens = set(_tokenize(text))
    return bool(tokens.intersection(CON_STANCE_WORDS))


def _contains_positive(text: str) -> bool:
    tokens = set(_tokenize(text))
    return bool(tokens.intersection(PRO_STANCE_WORDS))


def _contains_technical_criticism(text: str) -> bool:
    tokens = set(_tokenize(text))
    return bool(
        tokens.intersection(TECH_CRIT_TERMS) and tokens.intersection(CON_STANCE_WORDS)
    )


def _mentions_any(text: str, terms: Set[str]) -> bool:
    tokens = set(_tokenize(text))
    return bool(tokens.intersection(terms))


def _is_joke_context(text: str) -> bool:
    tokens = set(_tokenize(text))
    if not tokens:
        return False
    if not tokens.intersection(JOKE_CONTEXT_TERMS):
        return False
    if tokens.intersection(HOST_TERMS) or tokens.intersection(GUEST_TERMS):
        return False
    return True


def chunk_transcript_segments(
    transcript_segments: List[Dict[str, Any]],
    chunk_window_seconds: float = 28.0,
    max_chars_per_chunk: int = 280,
) -> List[TranscriptChunk]:
    if not transcript_segments:
        return []

    sorted_segments = sorted(
        transcript_segments, key=lambda seg: float(seg.get("start", 0.0) or 0.0)
    )

    chunks: List[TranscriptChunk] = []
    active_texts: List[str] = []
    active_start = 0.0
    active_end = 0.0

    def flush_chunk() -> None:
        nonlocal active_texts, active_start, active_end
        if not active_texts:
            return

        merged_text = _normalise_text(" ".join(active_texts))
        merged_text = _clean_transcript_text(merged_text)
        if not merged_text:
            active_texts = []
            return

        chunk = TranscriptChunk(
            index=len(chunks) + 1,
            start_seconds=active_start,
            end_seconds=max(active_end, active_start),
            text=merged_text,
        )
        chunks.append(chunk)
        active_texts = []

    for segment in sorted_segments:
        text = _clean_transcript_text(str(segment.get("text", "")))
        if not text:
            continue

        start_seconds = float(segment.get("start", 0.0) or 0.0)
        duration = float(segment.get("duration", 0.0) or 0.0)
        end_seconds = max(start_seconds + duration, start_seconds)

        if not active_texts:
            active_start = start_seconds
            active_end = end_seconds
            active_texts = [text]
            continue

        current_len = len(" ".join(active_texts))
        exceeds_window = (end_seconds - active_start) > chunk_window_seconds
        exceeds_chars = (current_len + len(text) + 1) > max_chars_per_chunk

        if exceeds_window or exceeds_chars:
            flush_chunk()
            active_start = start_seconds
            active_end = end_seconds
            active_texts = [text]
            continue

        active_texts.append(text)
        active_end = max(active_end, end_seconds)

    flush_chunk()
    return chunks


def score_comment_threads(
    structured_comments: List[Dict[str, Any]],
) -> List[ScoredComment]:
    if not structured_comments:
        return []

    now_epoch = datetime.now(timezone.utc).timestamp()
    scored: List[ScoredComment] = []

    for index, root in enumerate(structured_comments, start=1):
        root_text = _normalise_text(str(root.get("text", "")))
        root_likes = _safe_int(root.get("like_count"))
        replies = (
            root.get("replies", []) if isinstance(root.get("replies"), list) else []
        )

        reply_count = len(replies)
        total_reply_likes = sum(_safe_int(reply.get("like_count")) for reply in replies)
        unique_repliers = len(
            {
                _normalise_text(str(reply.get("author", "")).lower())
                for reply in replies
                if _normalise_text(str(reply.get("author", "")))
            }
        )

        combined_text = root_text
        if replies:
            reply_text = " ".join(
                _normalise_text(str(reply.get("text", ""))) for reply in replies[:15]
            )
            combined_text = _normalise_text(f"{root_text} {reply_text}")

        tokens = set(_tokenize(combined_text))

        recency_score = 0.0
        epoch = _timestamp_to_epoch(root.get("timestamp"))
        if epoch is not None and epoch > 0:
            age_days = max((now_epoch - epoch) / 86400.0, 0.0)
            recency_score = max(0.0, 1.2 - min(age_days / 365.0, 1.2))

        length_bonus = min(len(tokens) / 20.0, 1.0)
        short_penalty = 1.3 if len(root_text) < 20 or len(tokens) < 4 else 0.0

        signal_score = (
            2.4 * math.log1p(root_likes)
            + 2.2 * math.log1p(reply_count)
            + 1.6 * math.log1p(total_reply_likes)
            + 1.2 * math.log1p(unique_repliers)
            + 0.7 * length_bonus
            + 0.4 * recency_score
            - short_penalty
        )

        comment_id = str(root.get("id") or f"root-{index}")
        scored.append(
            ScoredComment(
                comment_id=comment_id,
                author=str(root.get("author", "") or ""),
                text=root_text,
                timestamp=root.get("timestamp"),
                like_count=root_likes,
                replies=replies,
                reply_count=reply_count,
                total_reply_likes=total_reply_likes,
                unique_repliers=unique_repliers,
                signal_score=max(signal_score, 0.0),
                token_set=tokens,
            )
        )

    scored.sort(key=lambda item: item.signal_score, reverse=True)
    return scored


def _select_representatives(
    members: List[ScoredComment], max_items: int = 4
) -> List[ScoredComment]:
    if not members:
        return []

    ranked = sorted(members, key=lambda item: item.signal_score, reverse=True)
    selected: List[ScoredComment] = []

    for comment in ranked:
        if not selected:
            selected.append(comment)
            if len(selected) >= max_items:
                break
            continue

        too_similar = any(
            _jaccard_similarity(comment.token_set, picked.token_set) > 0.62
            for picked in selected
            if comment.token_set and picked.token_set
        )
        if too_similar:
            continue
        selected.append(comment)
        if len(selected) >= max_items:
            break

    if len(selected) < 2 and len(ranked) >= 2:
        selected = ranked[: min(max_items, len(ranked))]

    return selected


def _infer_theme_label(
    terms: List[str], members: List[ScoredComment], used_labels: Set[str]
) -> str:
    lower_terms = [term.lower() for term in terms]
    corpus = " ".join(comment.text.lower() for comment in members[:8])
    term_set = set(lower_terms)

    best_label = ""
    best_score = 0
    for label, keywords in THEME_LABEL_PATTERNS:
        score = 0
        for keyword in keywords:
            if keyword in term_set:
                score += 2
            elif keyword in corpus:
                score += 1
        if score > best_score:
            best_score = score
            best_label = label

    if best_label and best_score >= 2:
        label = best_label
    else:
        term_set_fallback = set(lower_terms)
        if term_set_fallback.intersection(HUMOR_TERMS):
            label = "Playful side reactions"
        elif term_set_fallback.intersection(APPRECIATION_TERMS):
            label = "Sincere appreciation"
        elif term_set_fallback.intersection(SPREAD_TERMS):
            label = "Sharing and prank anecdotes"
        else:
            label = "Secondary audience reactions"

    used_labels.add(label)
    return label


def _infer_theme_interpretation(
    label: str, members: List[ScoredComment], terms: List[str]
) -> str:
    if label in _THEME_INTERPRETATION_MAP:
        return _THEME_INTERPRETATION_MAP[label]

    combined = " ".join(comment.text.lower() for comment in members[:10])
    humor_hits = sum(1 for term in HUMOR_TERMS if term in combined)
    critique_hits = sum(1 for term in CON_STANCE_WORDS if term in combined)
    praise_hits = sum(1 for term in PRO_STANCE_WORDS if term in combined)

    if humor_hits >= max(critique_hits, praise_hits):
        intent = "playful or meme-driven"
    elif critique_hits > praise_hits:
        intent = "mostly critical"
    elif praise_hits > 0:
        intent = "mostly supportive"
    else:
        intent = "mixed"

    if intent == "playful or meme-driven":
        return "Commenters treat this as a shared inside joke and build on each other with playful variations."
    if intent == "mostly critical":
        return "The thread is mainly critical, with commenters reinforcing the same complaint from different angles."
    if intent == "mostly supportive":
        return "Most comments are affirming and reinforce a similar positive read of the video."
    return "This theme reflects a mixed reaction, but still revolves around a consistent discussion angle."


def _merge_theme_clusters_by_label(
    clusters: List[ThemeCluster],
    lookup: Dict[str, ScoredComment],
) -> List[ThemeCluster]:
    if not clusters:
        return []

    grouped: Dict[str, ThemeCluster] = {}
    for cluster in clusters:
        if cluster.name not in grouped:
            grouped[cluster.name] = ThemeCluster(
                theme_id=cluster.theme_id,
                name=cluster.name,
                interpretation=cluster.interpretation,
                comment_ids=list(cluster.comment_ids),
                representative_comment_ids=[],
                evidence_terms=list(cluster.evidence_terms),
            )
            continue

        existing = grouped[cluster.name]
        existing.comment_ids.extend(cluster.comment_ids)
        for term in cluster.evidence_terms:
            if term not in existing.evidence_terms:
                existing.evidence_terms.append(term)

    merged: List[ThemeCluster] = []
    for cluster in grouped.values():
        unique_ids = []
        seen_ids: Set[str] = set()
        for cid in cluster.comment_ids:
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            unique_ids.append(cid)
        cluster.comment_ids = unique_ids

        members = [lookup[cid] for cid in cluster.comment_ids if cid in lookup]
        representatives = _select_representatives(members, max_items=4)
        cluster.representative_comment_ids = [
            item.comment_id for item in representatives
        ]
        merged.append(cluster)

    return merged


def group_comment_themes(
    scored_comments: List[ScoredComment],
    max_themes: int = 5,
    min_similarity: float = 0.22,
) -> List[ThemeCluster]:
    if not scored_comments:
        return []

    working: List[Dict[str, Any]] = []
    lookup = {comment.comment_id: comment for comment in scored_comments}

    for comment in scored_comments[:90]:
        if not comment.token_set:
            continue

        best_idx = -1
        best_similarity = 0.0
        for idx, theme in enumerate(working):
            theme_terms = set(term for term, _ in theme["counter"].most_common(45))
            similarity = _jaccard_similarity(comment.token_set, theme_terms)
            if similarity > best_similarity:
                best_similarity = similarity
                best_idx = idx

        if best_idx >= 0 and (
            best_similarity >= min_similarity or len(working) >= max_themes
        ):
            theme = working[best_idx]
            theme["comment_ids"].append(comment.comment_id)
            theme["counter"].update(comment.token_set)
            comment.assigned_theme_id = theme["theme_id"]
            continue

        theme_id = f"theme-{len(working) + 1}"
        working.append(
            {
                "theme_id": theme_id,
                "comment_ids": [comment.comment_id],
                "counter": Counter(comment.token_set),
            }
        )
        comment.assigned_theme_id = theme_id

    clusters: List[ThemeCluster] = []
    used_labels: Set[str] = set()

    for theme in working:
        theme_id = theme["theme_id"]
        comment_ids = list(theme["comment_ids"])
        members = [lookup[cid] for cid in comment_ids if cid in lookup]
        if not members:
            continue

        weighted_counter: Counter = Counter()
        for member in members:
            weight = max(member.signal_score, 1.0)
            for token in member.token_set:
                weighted_counter[token] += weight

        top_terms = [
            term
            for term, _ in weighted_counter.most_common(12)
            if term not in GENERIC_THEME_TERMS
        ]

        label = _infer_theme_label(top_terms, members, used_labels)
        interpretation = _infer_theme_interpretation(label, members, top_terms)

        representatives = _select_representatives(members, max_items=4)

        clusters.append(
            ThemeCluster(
                theme_id=theme_id,
                name=label,
                interpretation=interpretation,
                comment_ids=comment_ids,
                representative_comment_ids=[
                    item.comment_id for item in representatives
                ],
                evidence_terms=top_terms[:5],
            )
        )

    clusters = _merge_theme_clusters_by_label(clusters, lookup)

    clusters.sort(
        key=lambda cluster: sum(
            lookup[cid].signal_score for cid in cluster.comment_ids if cid in lookup
        ),
        reverse=True,
    )

    min_cluster_size = 3 if len(scored_comments) >= 20 else 1
    filtered = [
        cluster for cluster in clusters if len(cluster.comment_ids) >= min_cluster_size
    ]
    if not filtered:
        filtered = clusters[:1]

    return filtered[:max_themes]


def _stance_signal(text: str) -> int:
    tokens = set(_tokenize(text))
    if not tokens:
        return 0

    if _is_joke_context(text):
        return 0

    pro_hits = len(tokens.intersection(PRO_STANCE_WORDS))
    con_hits = len(tokens.intersection(CON_STANCE_WORDS))

    if "actually good" in text.lower() or "still holds up" in text.lower():
        pro_hits += 2
    if "sick of" in text.lower() or "overused" in text.lower():
        con_hits += 2

    if pro_hits > con_hits and pro_hits > 0:
        return 1
    if con_hits > pro_hits and con_hits > 0:
        return -1
    return 0


def _split_level_from_balance(minority_count: int, balance: float) -> str:
    if minority_count >= 3 and balance >= 0.55:
        return "strong split"
    if minority_count >= 2 and balance >= 0.32:
        return "weak split"
    return "mostly aligned"


def detect_controversies(
    scored_comments: List[ScoredComment],
    themes: List[ThemeCluster],
    limit: int = 3,
) -> List[Controversy]:
    if not scored_comments or not themes:
        return []

    lookup = {comment.comment_id: comment for comment in scored_comments}
    controversies: List[Tuple[float, Controversy]] = []

    for theme in themes:
        members = [lookup[cid] for cid in theme.comment_ids if cid in lookup]
        if len(members) < 4:
            continue

        pro = [comment for comment in members if _stance_signal(comment.text) > 0]
        con = [comment for comment in members if _stance_signal(comment.text) < 0]

        if not pro or not con:
            # still look for host-vs-guest pushback shape
            host_crit = [
                comment
                for comment in members
                if _mentions_any(comment.text, HOST_TERMS)
                and _contains_negative(comment.text)
            ]
            guest_crit = [
                comment
                for comment in members
                if _mentions_any(comment.text, GUEST_TERMS)
                and _contains_negative(comment.text)
            ]

            if len(guest_crit) >= 3 and len(host_crit) >= 1:
                level = "weak split" if len(host_crit) < 3 else "strong split"
                representatives = (
                    sorted(host_crit, key=lambda c: c.signal_score, reverse=True)[:1]
                    + sorted(guest_crit, key=lambda c: c.signal_score, reverse=True)[:1]
                )
                summary = "Most criticism targets the guest, but a smaller cluster redirects blame toward the host."
                weight = len(host_crit) + len(guest_crit)
                controversies.append(
                    (
                        float(weight),
                        Controversy(
                            issue=theme.name,
                            level=level,
                            summary=summary,
                            representative_comment_ids=[
                                item.comment_id for item in representatives
                            ],
                        ),
                    )
                )
            continue

        pro_signal = sum(item.signal_score for item in pro)
        con_signal = sum(item.signal_score for item in con)
        dominant = max(pro_signal, con_signal)
        minority = min(pro_signal, con_signal)
        balance = (minority / dominant) if dominant > 0 else 0.0
        minority_count = min(len(pro), len(con))

        level = _split_level_from_balance(minority_count, balance)
        if level == "mostly aligned":
            continue

        dominant_side = "supportive" if pro_signal >= con_signal else "critical"
        minority_side = "critical" if dominant_side == "supportive" else "supportive"

        if level == "strong split":
            summary = f"Strong split: both {dominant_side} and {minority_side} takes attract meaningful engagement."
        else:
            summary = f"Weak split: reaction is mostly {dominant_side}, with noticeable {minority_side} pushback."

        pro_top = sorted(pro, key=lambda item: item.signal_score, reverse=True)[:1]
        con_top = sorted(con, key=lambda item: item.signal_score, reverse=True)[:1]

        controversies.append(
            (
                minority + minority_count,
                Controversy(
                    issue=theme.name,
                    level=level,
                    summary=summary,
                    representative_comment_ids=[
                        item.comment_id for item in (pro_top + con_top)
                    ],
                ),
            )
        )

    controversies.sort(key=lambda pair: pair[0], reverse=True)
    return [pair[1] for pair in controversies[:limit]]


def _outlier_reason(comment: ScoredComment, metadata: Dict[str, Any]) -> str:
    text = (comment.text or "").lower()
    tokens = set(_tokenize(comment.text))

    if _is_official_author(comment.author, metadata):
        return "Official/platform voice that reframes the discussion."

    if tokens.intersection(MILESTONE_TERMS):
        return "Adds a macro view-count/longevity angle instead of the usual thread framing."

    if tokens.intersection(SPREAD_TERMS):
        return "Adds a concrete anecdote about how the video gets shared or discovered."

    if tokens.intersection(APPRECIATION_TERMS) and tokens.intersection(HUMOR_TERMS):
        return "Shifts from pure meme framing toward sincere appreciation."

    if _looks_firsthand(comment.text):
        return "Adds firsthand industry experience instead of generic hot takes."

    if _mentions_any(comment.text, HOST_TERMS) and _contains_negative(comment.text):
        return "Critiques the host rather than the main target of the thread."

    if any(
        term in text for term in ["government", "politics", "left", "right", "policy"]
    ):
        return "Shifts the discussion into a political angle."

    if any(
        term in text for term in ["algorithm", "recommended", "staff", "flag", "report"]
    ):
        return "Meta comment about platform behavior rather than the video itself."

    if any(term in text for term in HUMOR_TERMS):
        return "Unusually blunt or humorous angle that shifts the tone of the thread."

    return "Introduces an unexpected angle compared with the dominant comment themes."


def detect_outliers(
    scored_comments: List[ScoredComment],
    themes: List[ThemeCluster],
    metadata: Dict[str, Any],
    limit: int = 5,
) -> List[Outlier]:
    if not scored_comments:
        return []

    score_values = sorted(comment.signal_score for comment in scored_comments)
    median_score = score_values[len(score_values) // 2] if score_values else 0.0

    theme_terms_map = {
        theme.theme_id: set(theme.evidence_terms[:5])
        for theme in themes
        if theme.evidence_terms
    }

    outlier_scored: List[Tuple[float, Outlier]] = []
    for comment in scored_comments:
        if not comment.token_set or comment.signal_score < (median_score * 0.75):
            continue

        if comment.assigned_theme_id and comment.assigned_theme_id in theme_terms_map:
            max_theme_similarity = _jaccard_similarity(
                comment.token_set, theme_terms_map[comment.assigned_theme_id]
            )
        else:
            max_theme_similarity = 0.0
            for terms in theme_terms_map.values():
                max_theme_similarity = max(
                    max_theme_similarity, _jaccard_similarity(comment.token_set, terms)
                )

        if max_theme_similarity > 0.18:
            continue

        novelty = (1.0 - max_theme_similarity) + (comment.signal_score / 20.0)
        outlier_scored.append(
            (
                novelty,
                Outlier(
                    comment_id=comment.comment_id,
                    reason=_outlier_reason(comment, metadata),
                ),
            )
        )

    outlier_scored.sort(key=lambda pair: pair[0], reverse=True)

    unique_reasons: Set[str] = set()
    selected: List[Outlier] = []
    for _, outlier in outlier_scored:
        if outlier.reason in unique_reasons and len(selected) >= 3:
            continue
        selected.append(outlier)
        unique_reasons.add(outlier.reason)
        if len(selected) >= limit:
            break

    return selected


def _select_key_transcript_excerpts(
    transcript_chunks: List[TranscriptChunk],
    scored_comments: List[ScoredComment],
    max_excerpts: int = 3,
) -> List[TranscriptChunk]:
    if not transcript_chunks:
        return []

    top_comment_tokens: Set[str] = set()
    for comment in scored_comments[:20]:
        top_comment_tokens.update(list(comment.token_set)[:12])

    scored_chunks: List[Tuple[float, TranscriptChunk]] = []
    for chunk in transcript_chunks:
        tokens = _tokenize(chunk.text)
        if not tokens:
            continue

        unique_ratio = len(set(tokens)) / float(len(tokens))
        overlap = len(set(tokens).intersection(top_comment_tokens))
        overlap_ratio = overlap / float(max(len(set(tokens)), 1))
        refrain_penalty = 0.45 if "(refrain repeats)" in chunk.text else 0.0
        length_bonus = min(len(chunk.text) / 220.0, 1.0)

        score = (
            (unique_ratio * 1.5)
            + (overlap_ratio * 1.7)
            + (length_bonus * 0.4)
            - refrain_penalty
        )
        scored_chunks.append((score, chunk))

    if not scored_chunks:
        return transcript_chunks[: min(4, len(transcript_chunks))]

    scored_chunks.sort(key=lambda pair: pair[0], reverse=True)

    picked: List[TranscriptChunk] = []
    for _, chunk in scored_chunks:
        if any(
            abs(chunk.start_seconds - chosen.start_seconds) < 16 for chosen in picked
        ):
            continue
        chunk_tokens = set(_tokenize(chunk.text))
        if any(
            _jaccard_similarity(chunk_tokens, set(_tokenize(chosen.text))) > 0.72
            for chosen in picked
        ):
            continue
        picked.append(chunk)
        if len(picked) >= max_excerpts:
            break

    if len(picked) < min(3, len(transcript_chunks)):
        for chunk in transcript_chunks:
            if chunk in picked:
                continue
            picked.append(chunk)
            if len(picked) >= min(3, len(transcript_chunks)):
                break

    picked.sort(key=lambda chunk: chunk.start_seconds)
    return picked


def _derive_split_level(controversies: List[Controversy]) -> str:
    if any(item.level == "strong split" for item in controversies):
        return "strongly split"
    if any(item.level == "weak split" for item in controversies):
        return "weakly split"
    return "mostly aligned"


def _derive_audience_read(
    scored_comments: List[ScoredComment],
    themes: List[ThemeCluster],
    split_level: str,
) -> List[str]:
    if not scored_comments:
        return ["Audience reaction is limited because few comments were available."]

    pro = sum(1 for comment in scored_comments[:60] if _stance_signal(comment.text) > 0)
    con = sum(1 for comment in scored_comments[:60] if _stance_signal(comment.text) < 0)

    if con >= max(3, int(pro * 1.6)):
        tone = "Dominant reaction is critical."
    elif pro >= max(3, int(con * 1.6)):
        tone = "Dominant reaction is supportive."
    else:
        humor_hits = sum(
            1
            for comment in scored_comments[:40]
            if any(term in comment.text.lower() for term in HUMOR_TERMS)
        )
        if humor_hits >= max(4, len(scored_comments[:40]) // 4):
            tone = "Dominant reaction is playful and meme-driven."
        else:
            tone = "Dominant reaction is mixed but converges on a few repeated talking points."

    split_line = f"Audience is {split_level}."

    if themes:
        top = themes[0].name
        theme_line = f"Most comments cluster around: {top}."
    else:
        theme_line = "No strong theme clusters emerged from available comments."

    return [tone, split_line, theme_line]


def _is_refrain_heavy(chunks: List[TranscriptChunk]) -> bool:
    if not chunks:
        return False
    repeated = sum(1 for chunk in chunks if "(refrain repeats)" in chunk.text)
    chorus_hits = sum(1 for chunk in chunks if "never gonna" in chunk.text.lower())
    return repeated >= max(1, len(chunks) // 2) or chorus_hits >= max(
        2, len(chunks) // 2
    )


def generate_video_core(
    metadata: Dict[str, Any],
    transcript_chunks: List[TranscriptChunk],
    themes: List[ThemeCluster],
    split_level: str,
    controversies: List[Controversy],
) -> List[str]:
    channel = str(metadata.get("Channel") or "The creator")
    title = str(metadata.get("Title") or "this video")

    bullets: List[str] = []

    if transcript_chunks:
        if _is_refrain_heavy(transcript_chunks):
            bullets.append(
                "The transcript is dominated by repeated hook/chorus lines, so the strongest discussion signal comes from comments rather than plot detail."
            )
        else:
            bullets.append(
                f"{channel} uses {title} as a focused narrative with limited topic drift across the key excerpts."
            )

    if themes:
        if len(themes) >= 2:
            bullets.append(
                f"Audience discussion is led by {themes[0].name.lower()} and {themes[1].name.lower()}."
            )
        else:
            bullets.append(f"Audience discussion is led by {themes[0].name.lower()}.")

    bullets.append(f"Overall reaction is {split_level}.")

    if controversies and controversies[0].level == "strong split":
        bullets.append(
            f"Biggest disagreement centers on {controversies[0].issue.lower()}, where both sides attract real support."
        )

    if not bullets:
        bullets.append(
            "Transcript and comment signals were limited, so the core discussion remains sparse."
        )

    return bullets[:4]


def annotate_comment_significance(
    scored_comments: List[ScoredComment],
    themes: List[ThemeCluster],
    controversies: List[Controversy],
    metadata: Dict[str, Any],
) -> None:
    if not scored_comments:
        return

    likes_threshold = _percentile([item.like_count for item in scored_comments], 0.9)
    replies_threshold = _percentile(
        [item.reply_count for item in scored_comments], 0.85
    )
    most_replied = max(scored_comments, key=lambda item: item.reply_count)

    top_theme_id = themes[0].theme_id if themes else None
    controversy_ids = {
        comment_id
        for controversy in controversies
        for comment_id in controversy.representative_comment_ids
    }

    for comment in scored_comments:
        tokens = set(_tokenize(comment.text))

        if _is_official_author(comment.author, metadata):
            comment.why_it_matters = (
                "Creator/platform comment that anchors the thread's tone."
            )
            continue

        if tokens.intersection(MILESTONE_TERMS):
            comment.why_it_matters = (
                "Captures the longevity/view-milestone narrative around this video."
            )
            continue

        if _mentions_any(comment.text, HOST_TERMS) and _contains_negative(comment.text):
            comment.why_it_matters = "Strongest host pushback in the discussion sample."
            continue

        if _contains_technical_criticism(comment.text):
            comment.why_it_matters = (
                "Strongest technical criticism in the high-signal set."
            )
            continue

        if tokens.intersection(APPRECIATION_TERMS) and not _contains_negative(
            comment.text
        ):
            comment.why_it_matters = (
                "Strongest non-ironic defense/nuance in an otherwise meme-heavy thread."
            )
            continue

        if tokens.intersection(SPREAD_TERMS):
            comment.why_it_matters = (
                "Corroborating anecdote about how viewers encounter/share the content."
            )
            continue

        if comment.comment_id == most_replied.comment_id and comment.reply_count >= 3:
            comment.why_it_matters = (
                "Largest reply thread; strongest conversation magnet."
            )
            continue

        if _looks_firsthand(comment.text):
            comment.why_it_matters = (
                "Corroborating firsthand experience rather than secondhand opinion."
            )
            continue

        if comment.comment_id in controversy_ids:
            if _mentions_any(comment.text, HOST_TERMS) and _contains_negative(
                comment.text
            ):
                comment.why_it_matters = (
                    "Strongest host pushback in the minority viewpoint."
                )
            elif _contains_positive(comment.text):
                comment.why_it_matters = (
                    "Strongest defense/nuance against the dominant criticism."
                )
            else:
                comment.why_it_matters = (
                    "Key minority pushback that creates visible split signal."
                )
            continue

        if _contains_technical_criticism(comment.text):
            comment.why_it_matters = (
                "Strongest technical criticism in the high-signal set."
            )
            continue

        if top_theme_id and comment.assigned_theme_id == top_theme_id:
            comment.why_it_matters = (
                "Representative dominant reaction in the main theme cluster."
            )
            continue

        if comment.like_count >= likes_threshold and likes_threshold > 0:
            comment.why_it_matters = (
                "One of the most endorsed comments, signaling broad agreement."
            )
            continue

        if comment.reply_count >= max(3, replies_threshold):
            comment.why_it_matters = (
                "High reply traction suggests this point shaped follow-up discussion."
            )
            continue

        comment.why_it_matters = (
            "Useful signal of how viewers are framing the conversation."
        )


def build_video_discussion_pack(
    metadata: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    threaded_comments: List[Dict[str, Any]],
) -> VideoDiscussionPack:
    raw_chunks = chunk_transcript_segments(transcript_segments)
    scored_comments = score_comment_threads(threaded_comments)
    themes = group_comment_themes(scored_comments)
    controversies = detect_controversies(scored_comments, themes)
    split_level = _derive_split_level(controversies)

    annotate_comment_significance(scored_comments, themes, controversies, metadata)

    outliers = detect_outliers(scored_comments, themes, metadata)
    audience_read = _derive_audience_read(scored_comments, themes, split_level)
    video_core = generate_video_core(
        metadata,
        raw_chunks,
        themes,
        split_level,
        controversies,
    )

    return VideoDiscussionPack(
        metadata=metadata,
        thesis=video_core,
        transcript_chunks=raw_chunks,
        threaded_comments=threaded_comments,
        scored_comments=scored_comments,
        theme_clusters=themes,
        controversies=controversies,
        outliers=outliers,
        audience_read=audience_read,
        split_level=split_level,
    )


def comment_lookup(
    scored_comments: Iterable[ScoredComment],
) -> Dict[str, ScoredComment]:
    return {
        comment.comment_id: comment for comment in scored_comments if comment.comment_id
    }
