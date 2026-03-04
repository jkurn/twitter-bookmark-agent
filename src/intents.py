"""
Regex-based intent classifier.
No LLM needed — simple pattern matching.
"""

import re

# Intent types
SEARCH = "SEARCH"
SUMMARIZE = "SUMMARIZE"
RECOMMEND = "RECOMMEND"
QA = "QA"

# Patterns
_SEARCH_STARTS = re.compile(
    r"^(show|find|list|search|give me|get|look up|pull up)\b", re.IGNORECASE
)
_SUMMARIZE_PATTERNS = re.compile(
    r"(summarize|summarise|summary of|what does @\w+ (say|talk|think|write|post)|"
    r"tell me about @\w+|who is @\w+|what.s @\w+ about)",
    re.IGNORECASE,
)
_RECOMMEND_PATTERNS = re.compile(
    r"(related to|similar to|what else|more like|recommend|suggest|anything like)",
    re.IGNORECASE,
)
_HANDLE_RE = re.compile(r"@(\w+)")


def classify(message: str) -> str:
    """
    Classify a user message into an intent.

    Returns one of: SEARCH, SUMMARIZE, RECOMMEND, QA
    """
    msg = message.strip()

    if _SUMMARIZE_PATTERNS.search(msg):
        return SUMMARIZE

    if _SEARCH_STARTS.match(msg):
        return SEARCH

    if _RECOMMEND_PATTERNS.search(msg):
        return RECOMMEND

    return QA


def extract_handle(message: str) -> str | None:
    """Extract the first @handle from a message, or None."""
    match = _HANDLE_RE.search(message)
    return f"@{match.group(1)}" if match else None
