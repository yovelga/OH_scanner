"""
Orchestration pipeline.

Steps:
  1. Extract content  (extractor.py)
  2. Deterministic metadata  (metadata.py)
  3. LLM classification  (classifier.py)
  4. Merge into validated ArticleResult (models.py)
  5. Return as plain dict (JSON-serialisable)
"""
from __future__ import annotations

from ohpr.classifier import classify
from ohpr.extractor import extract
from ohpr.metadata import extract_metadata
from ohpr.models import ArticleResult


def process_url(url: str) -> dict:
    """
    Full pipeline for a single article URL.
    Always returns a dict with every ArticleResult field present
    (value may be null/None).
    """
    # ── 1. Extract ────────────────────────────────────────────────────────────
    extracted = extract(url)

    text: str = extracted.get("text", "")
    html: str = extracted.get("html", "")
    fc_meta: dict = extracted.get("metadata", {})

    # ── 2. Deterministic metadata ────────────────────────────────────────────
    meta = extract_metadata(
        url=url,
        html=html,
        text=text,
        firecrawl_metadata=fc_meta,
    )

    # ── 3. LLM classification ────────────────────────────────────────────────
    classification = classify(
        url=url,
        platform_name=meta.get("platform_name"),
        title=meta.get("title"),
        language=meta.get("language"),
        text=text,
    )

    # ── 4. Merge & validate ──────────────────────────────────────────────────
    # If extraction completely failed, mark needs_review regardless of LLM output
    if not text.strip():
        classification["needs_review"] = True
        classification["confidence"] = None

    # Prefer LLM-translated title (English); fall back to raw title from metadata
    title = classification.get("title") or meta.get("title")

    result = ArticleResult(
        url=url,
        date=meta.get("date"),
        platform_name=meta.get("platform_name"),
        platform_link=meta.get("platform_link"),
        language=meta.get("language"),
        title=title,
        sentiment=classification.get("sentiment"),
        topic=classification.get("topic"),
        media_type=classification.get("media_type"),
        segment=classification.get("segment"),
        tier=classification.get("tier"),
        organic_paid=classification.get("organic_paid"),
        summary=classification.get("summary"),
        confidence=classification.get("confidence"),
        needs_review=classification.get("needs_review"),
    )

    return result.model_dump()
