"""
Deterministic metadata extraction — no LLM, no guessing.

Extracts:
  - platform_name  (from URL netloc)
  - platform_link  (scheme + netloc)
  - date           (ISO 8601, best-effort from meta tags / JSON-LD / <time>)
  - title          (OG > <title> > <h1>)
  - language       (Firecrawl meta > HTML lang attr > langdetect)
"""
from __future__ import annotations

import json
import re
import sys
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
from langdetect import detect, LangDetectException


# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------

def _platform_info(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    netloc = parsed.netloc or ""
    platform_link = f"{parsed.scheme}://{netloc}" if parsed.scheme else url
    # Strip www. and take the first label as a readable name
    clean = re.sub(r"^www\.", "", netloc)
    platform_name = clean.split(".")[0].capitalize() if clean else netloc
    return platform_name, platform_link


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_DATE_META_NAMES = {
    "article:published_time",
    "og:published_time",
    "datepublished",
    "dc.date",
    "date",
    "pubdate",
    "publishdate",
    "article:modified_time",
    "last-modified",
}

_DATE_LD_KEYS = ("datePublished", "dateCreated", "dateModified")

_FIRECRAWL_DATE_KEYS = (
    "publishedTime",
    "published_time",
    "datePublished",
    "date",
    "pubDate",
    "article:published_time",
)


def _parse_date(raw: str) -> Optional[str]:
    """Normalise any date string to YYYY-MM-DD, or return None."""
    if not raw:
        return None
    raw = raw.strip()
    # Fast path: already ISO YYYY-MM-DD
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    try:
        dt = dateutil_parser.parse(raw, fuzzy=True)
        return dt.date().isoformat()
    except Exception:
        return None


def _date_from_firecrawl(fc_meta: dict) -> Optional[str]:
    for key in _FIRECRAWL_DATE_KEYS:
        val = fc_meta.get(key)
        if val:
            parsed = _parse_date(str(val))
            if parsed:
                return parsed
    return None


def _date_from_html(soup: BeautifulSoup) -> Optional[str]:
    # 1. <meta> tags
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        if prop in _DATE_META_NAMES:
            content = meta.get("content") or meta.get("datetime") or ""
            parsed = _parse_date(content)
            if parsed:
                return parsed

    # 2. JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw_json = script.string or ""
            data = json.loads(raw_json)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                for key in _DATE_LD_KEYS:
                    val = item.get(key)
                    if val:
                        parsed = _parse_date(str(val))
                        if parsed:
                            return parsed
        except Exception:
            pass

    # 3. <time datetime="...">
    time_tag = soup.find("time")
    if time_tag:
        dt_attr = time_tag.get("datetime") or time_tag.get_text(strip=True)
        parsed = _parse_date(dt_attr)
        if parsed:
            return parsed

    return None


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

def _title_from_firecrawl(fc_meta: dict) -> Optional[str]:
    for key in ("ogTitle", "title", "og:title"):
        val = fc_meta.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return None


def _title_from_html(soup: BeautifulSoup) -> Optional[str]:
    # OG title
    og = soup.find("meta", property="og:title")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    # Twitter title
    tw = soup.find("meta", attrs={"name": "twitter:title"})
    if tw and tw.get("content", "").strip():
        return tw["content"].strip()

    # <title>
    if soup.title and soup.title.string and soup.title.string.strip():
        return soup.title.string.strip()

    # <h1>
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return None


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------

# Legacy / non-standard codes → current ISO 639-1
_LANG_ALIASES: dict[str, str] = {
    "iw": "he",   # old Hebrew code (still used by Google/some HTML)
    "in": "id",   # old Indonesian code
    "ji": "yi",   # old Yiddish code
    "mo": "ro",   # Moldavian → Romanian
    "sh": "sr",   # Serbo-Croatian → Serbian
    "no": "nb",   # generic Norwegian → Bokmål
}

# Locale suffixes that langdetect returns which need remapping
_LANGDETECT_ALIASES: dict[str, str] = {
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh-hans": "zh",
    "zh-hant": "zh",
    "pt-br": "pt",
    "pt-pt": "pt",
}


def _normalise_lang(raw: str) -> Optional[str]:
    """
    Take any raw language tag and return a clean ISO 639-1 code.
    E.g. "iw", "he-IL", "HE_il", "zh-Hans" → canonical form.
    Returns None if the input is blank.
    """
    if not raw:
        return None
    lower = raw.strip().lower()
    # Check full tag aliases first (e.g. "zh-cn")
    if lower in _LANGDETECT_ALIASES:
        return _LANGDETECT_ALIASES[lower]
    # Strip region/script subtags: "he-IL" → "he", "zh_Hans" → "zh"
    base = re.split(r"[-_]", lower)[0]
    # Map legacy codes
    return _LANG_ALIASES.get(base, base)


def _language_from_firecrawl(fc_meta: dict) -> Optional[str]:
    raw = fc_meta.get("language") or fc_meta.get("og:locale") or ""
    return _normalise_lang(str(raw)) if raw else None


def _language_from_html(soup: BeautifulSoup) -> Optional[str]:
    html_tag = soup.find("html")
    if html_tag:
        raw = html_tag.get("lang") or html_tag.get("xml:lang") or ""
        return _normalise_lang(str(raw)) if raw else None
    return None


def _language_from_text(text: str) -> Optional[str]:
    if not text or len(text.strip()) < 30:
        return None
    try:
        detected = detect(text[:2000])
        return _normalise_lang(detected)
    except LangDetectException:
        return None
    except Exception as exc:
        print(f"[metadata] langdetect error: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def extract_metadata(
    url: str,
    html: str,
    text: str,
    firecrawl_metadata: dict,
) -> dict:
    """
    Return deterministic metadata for the given article.
    All values are either a string/bool/None — never fabricated.
    """
    platform_name, platform_link = _platform_info(url)

    soup: Optional[BeautifulSoup] = None
    if html:
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = None

    # Date: Firecrawl meta → HTML → None
    date = _date_from_firecrawl(firecrawl_metadata)
    if not date and soup:
        date = _date_from_html(soup)

    # Title: Firecrawl meta → HTML → None
    title = _title_from_firecrawl(firecrawl_metadata)
    if not title and soup:
        title = _title_from_html(soup)

    # Language: Firecrawl meta → HTML lang attr → langdetect on text
    language = _language_from_firecrawl(firecrawl_metadata)
    if not language and soup:
        language = _language_from_html(soup)
    if not language:
        language = _language_from_text(text)

    return {
        "platform_name": platform_name or None,
        "platform_link": platform_link or None,
        "date": date,
        "title": title,
        "language": language,
    }
