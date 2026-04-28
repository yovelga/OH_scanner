"""
Processor service — URL and PDF processing.

PDF processing is still mocked (see TODO in process_pdf).
"""
from __future__ import annotations

import logging
from typing import Optional

from ohpr.pipeline import process_url as _ohpr_process_url

logger = logging.getLogger("ohpr_bot.processor")


def process_url(url: str) -> dict:
    """
    Process a URL and return structured media-monitoring data.

    Delegates to the real ohpr pipeline and reshapes the result so the
    keys expected by telegram_service.format_url_reply() are always present:
    source, status, title, topic, sentiment, language, summary.

    Raises on pipeline failure — the caller (telegram route) catches and
    sends a user-friendly error message.
    """
    logger.info(f"Processing URL: {url}")
    try:
        raw = _ohpr_process_url(url)
    except Exception:
        logger.exception(f"ohpr pipeline failed for URL: {url}")
        raise

    # Remap pipeline keys to the shape the Telegram route consumes.
    # All .get() calls are safe — ArticleResult fields are all Optional.
    return {
        # Keys the route / format_url_reply reads
        "source": raw.get("url") or url,
        "status": "ok",
        "title": raw.get("title"),
        "topic": raw.get("topic"),
        "sentiment": raw.get("sentiment"),
        "language": raw.get("language"),
        "summary": raw.get("summary"),
        # Pass-through of all extra pipeline fields for future use
        "input_type": "url",
        "date": raw.get("date"),
        "platform_name": raw.get("platform_name"),
        "platform_link": raw.get("platform_link"),
        "media_type": raw.get("media_type"),
        "segment": raw.get("segment"),
        "tier": raw.get("tier"),
        "organic_paid": raw.get("organic_paid"),
        "confidence": raw.get("confidence"),
        "needs_review": raw.get("needs_review"),
    }


def process_pdf(file_path: str, file_name: Optional[str] = None) -> dict:
    """
    Process a locally downloaded PDF and return structured data.

    Args:
        file_path:  Absolute path to the downloaded temp file.
        file_name:  Original filename from Telegram (for display only).

    Returns:
        A dict with at minimum: input_type, file_name, status.
    """
    name = file_name or "document.pdf"
    logger.info(f"Processing PDF: {name} (path={file_path})")

    # ── MOCK — replace with real OCR / extraction implementation ─────────────
    return {
        "input_type": "pdf",
        "file_name": name,
        "status": "processed",
        "title": "Mock PDF Title",
        "document_type": "News Clip",
        "language": "HE",
        "pages": 1,
        "summary": "This is a mock PDF summary. Replace process_pdf() with real OCR logic.",
    }
