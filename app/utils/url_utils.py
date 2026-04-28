"""
URL extraction utilities using regex.
No external HTTP calls — purely string-based detection.
"""
from __future__ import annotations

import re
from typing import Optional

# Matches http and https URLs (covers most real-world formats)
_URL_PATTERN = re.compile(
    r"https?://"
    r"(?:[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)",
    re.IGNORECASE,
)


def extract_url(text: str) -> Optional[str]:
    """
    Extract the first valid HTTP/HTTPS URL from a text string.

    Args:
        text: Raw text (e.g. a Telegram message body).

    Returns:
        The first URL found, or None if no URL is present.
    """
    if not text:
        return None
    match = _URL_PATTERN.search(text)
    return match.group(0) if match else None


def is_valid_url(url: str) -> bool:
    """
    Return True if the string is a valid HTTP/HTTPS URL.

    Args:
        url: String to validate.
    """
    if not url:
        return False
    return bool(_URL_PATTERN.fullmatch(url))
