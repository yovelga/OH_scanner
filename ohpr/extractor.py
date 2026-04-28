"""
Content extraction pipeline.

Priority order:
  1. Firecrawl API  – richest output, includes cleaned markdown + metadata
  2. trafilatura    – fast, high-quality main-content extraction
  3. requests + bs4 – last-resort fallback

Every extractor returns the same dict shape:
  {
      "text":     str,   # plain-text article body
      "html":     str,   # raw HTML (for metadata parsing)
      "metadata": dict,  # key/value from the source (Firecrawl only, else {})
      "source":   str,   # "firecrawl" | "trafilatura" | "bs4" | "none"
  }
"""
from __future__ import annotations

import sys

import requests
import trafilatura
from bs4 import BeautifulSoup

from ohpr.config import settings

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; OHPRBot/1.0; media-monitoring)"
    )
}


# ---------------------------------------------------------------------------
# Firecrawl
# ---------------------------------------------------------------------------

def _extract_firecrawl(url: str) -> dict | None:
    if not settings.FIRECRAWL_API_KEY:
        return None

    try:
        resp = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={
                "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "url": url,
                "formats": ["markdown", "html"],
                "onlyMainContent": True,
            },
            timeout=settings.FIRECRAWL_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as exc:
        print(f"[extractor] Firecrawl error: {exc}", file=sys.stderr)
        return None

    if not body.get("success"):
        return None

    data = body.get("data", {})
    text = data.get("markdown") or ""
    html = data.get("html") or ""
    meta = data.get("metadata") or {}

    if not text.strip():
        return None

    return {"text": text, "html": html, "metadata": meta, "source": "firecrawl"}


# ---------------------------------------------------------------------------
# trafilatura
# ---------------------------------------------------------------------------

def _extract_trafilatura(url: str) -> dict | None:
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        if not text or not text.strip():
            return None
        return {"text": text, "html": downloaded, "metadata": {}, "source": "trafilatura"}
    except Exception as exc:
        print(f"[extractor] trafilatura error: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# requests + BeautifulSoup
# ---------------------------------------------------------------------------

def _extract_bs4(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            return None
        return {"text": text, "html": html, "metadata": {}, "source": "bs4"}
    except Exception as exc:
        print(f"[extractor] bs4 error: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def extract(url: str) -> dict:
    """
    Extract article content from *url*.
    Returns a normalised dict; 'text' may be empty string if all extractors fail.
    """
    for extractor in (_extract_firecrawl, _extract_trafilatura, _extract_bs4):
        result = extractor(url)
        if result and result.get("text", "").strip():
            print(f"[extractor] used {result['source']}", file=sys.stderr)
            return result

    print("[extractor] all extractors failed", file=sys.stderr)
    return {"text": "", "html": "", "metadata": {}, "source": "none"}
