"""
LLM-based classification — runs AFTER deterministic metadata extraction.

Returns:
  sentiment, topic, media_type, segment, tier, organic_paid,
  summary, confidence, needs_review

If OPENAI_API_KEY is not set, all fields are returned as None
(except needs_review which defaults to True).

The system prompt enforces strict JSON-only output and prohibits
fabricating information not present in the article.
"""
from __future__ import annotations

import json
import sys
from typing import Optional

from ohpr.config import settings

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a media-monitoring analyst that classifies news articles.
Return ONLY a single valid JSON object — no markdown fences, no prose.
Set any field to null if you cannot determine it with reasonable confidence.
Do NOT fabricate information that is not present in the article.

CRITICAL for non-English articles:
- Read and understand content in any language.
- ALL output fields must be in English — including `title`, `topic`, and `summary`.
- If the title is in another language, translate it accurately to English.
"""

_USER_TEMPLATE = """\
Classify the article below and return JSON matching this exact schema:

{{
  "sentiment":    "positive" | "negative" | "neutral" | null,
  "title":        "<English translation of the article title>" | null,
  "topic":        "<3-5 words in English describing the main topic>" | null,
  "media_type":   "news" | "blog" | "press_release" | "social" | "forum" | "podcast" | "video" | "other" | null,
  "segment":      "technology" | "finance" | "health" | "politics" | "entertainment" | "sports" | "business" | "other" | null,
  "tier":         "tier1" | "tier2" | "tier3" | null,
  "organic_paid": "organic" | "paid" | "unknown" | null,
  "summary":      "<2-3 sentence factual summary in English>" | null,
  "confidence":   <float 0.0-1.0>,
  "needs_review": <true if confidence < 0.65 or content is ambiguous, else false>
}}

Tier guidance (judge by reach within the outlet's PRIMARY market, not globally):
  tier1 = dominant national or major international outlet in its country/region
          (e.g. BBC, NYT, Reuters globally; Ynet, Mako, Calcalist in Israel;
           Le Monde in France; El País in Spain; Folha in Brazil)
  tier2 = regional, industry-specific, or mid-size outlet
  tier3 = niche, small blog, startup publication, or unknown outlet

If the article is in a non-English language, still classify it accurately —
read the content, understand it, and produce ALL output in English.

---
Platform : {platform_name}
URL      : {url}
Title    : {title}  (original — translate this to English in your output)
Language : {language}  (ISO 639-1 source language of the article)

Article text (truncated to 8 000 chars):
{text}
"""

# ---------------------------------------------------------------------------
# Null result (returned when LLM is unavailable or fails)
# ---------------------------------------------------------------------------

_NULL_CLASSIFICATION: dict = {
    "title": None,
    "sentiment": None,
    "topic": None,
    "media_type": None,
    "segment": None,
    "tier": None,
    "organic_paid": None,
    "summary": None,
    "confidence": None,
    "needs_review": True,
}

# Fields expected in the LLM response
_EXPECTED_FIELDS = set(_NULL_CLASSIFICATION.keys())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_prompt(
    url: str,
    platform_name: Optional[str],
    title: Optional[str],
    language: Optional[str],
    text: str,
) -> str:
    return _USER_TEMPLATE.format(
        platform_name=platform_name or "unknown",
        url=url,
        title=title or "",
        language=language or "unknown",
        text=text[:8000],
    )


def _parse_response(raw: str) -> dict:
    """
    Parse the LLM JSON response.  Returns _NULL_CLASSIFICATION on any error.
    Accepts bare JSON or JSON wrapped in a markdown code fence.
    """
    # Strip optional markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"[classifier] JSON parse error: {exc}", file=sys.stderr)
        return dict(_NULL_CLASSIFICATION)

    if not isinstance(data, dict):
        return dict(_NULL_CLASSIFICATION)

    # Keep only expected keys; fill missing ones with None
    result: dict = {}
    for field in _EXPECTED_FIELDS:
        result[field] = data.get(field)

    # Ensure needs_review is always bool
    nr = result.get("needs_review")
    if not isinstance(nr, bool):
        result["needs_review"] = True

    return result


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def classify(
    url: str,
    platform_name: Optional[str],
    title: Optional[str],
    language: Optional[str],
    text: str,
) -> dict:
    """
    Call the LLM and return classification fields.
    Falls back to _NULL_CLASSIFICATION if LLM is unavailable or errors out.
    """
    if not settings.OPENAI_API_KEY:
        print("[classifier] OPENAI_API_KEY not set — skipping LLM classification", file=sys.stderr)
        return dict(_NULL_CLASSIFICATION)

    if not text.strip():
        print("[classifier] empty text — skipping LLM classification", file=sys.stderr)
        return dict(_NULL_CLASSIFICATION)

    try:
        from openai import OpenAI  # imported lazily to avoid hard dep at import time

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = _build_prompt(url, platform_name, title, language, text)

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=600,
        )

        raw = response.choices[0].message.content or ""
        result = _parse_response(raw)

        # Auto-flag low confidence
        confidence = result.get("confidence")
        if confidence is not None:
            try:
                if float(confidence) < 0.65:
                    result["needs_review"] = True
            except (ValueError, TypeError):
                pass

        return result

    except Exception as exc:
        print(f"[classifier] LLM error: {exc}", file=sys.stderr)
        return dict(_NULL_CLASSIFICATION)
