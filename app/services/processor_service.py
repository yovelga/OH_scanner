"""
Processor service — URL and PDF processing.

Currently returns MOCKED data so the full pipeline runs end-to-end
without real scraping or OCR.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TO ENABLE REAL URL PROCESSING:
  Replace the body of process_url() with:

      from ohpr.pipeline import process_url as _ohpr_process_url
      return _ohpr_process_url(url)

TO ENABLE REAL PDF PROCESSING:
  Replace the body of process_pdf() with your OCR / extraction logic.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("ohpr_bot.processor")


def process_url(url: str) -> dict:
    """
    Process a URL and return structured media-monitoring data.

    Args:
        url: The article URL to analyse.

    Returns:
        A dict with at minimum: input_type, source, status.
    """
    logger.info(f"Processing URL: {url}")

    # ── MOCK — replace with real implementation ───────────────────────────────
    return {
        "input_type": "url",
        "source": url,
        "status": "processed",
        "title": "Mock Article Title",
        "sentiment": "Neutral",
        "topic": "Example Topic",
        "summary": "This is a mock summary. Replace process_url() with the real OHPR pipeline.",
        "platform": url.split("/")[2] if url.count("/") >= 2 else "unknown",
        "language": "en",
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
