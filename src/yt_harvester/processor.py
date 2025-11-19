from typing import List, Dict, Any
from textblob import TextBlob

def analyze_sentiment(text: str) -> Dict[str, float]:
    """
    Analyze sentiment of the text using TextBlob.
    Returns polarity (-1.0 to 1.0) and subjectivity (0.0 to 1.0).
    """
    if not text:
        return {"polarity": 0.0, "subjectivity": 0.0}
    
    blob = TextBlob(text)
    return {
        "polarity": blob.sentiment.polarity,
        "subjectivity": blob.sentiment.subjectivity
    }

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract key noun phrases from the text.
    """
    if not text:
        return []
    
    blob = TextBlob(text)
    # Get noun phrases and count frequency
    counts = blob.np_counts
    # Sort by frequency
    sorted_phrases = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [phrase for phrase, count in sorted_phrases[:top_n]]
