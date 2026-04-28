"""
Integration smoke test for processor_service.process_url().

Requires real API keys — skipped automatically when they are absent.
Run manually with:
    pytest tests/test_processor_real_url.py -v -m integration
"""
from __future__ import annotations

import os

import pytest

from app.services import processor_service

# Keys consumed by telegram_service.format_url_reply()
REQUIRED_KEYS = {"source", "status", "title", "topic", "sentiment", "language", "summary"}


@pytest.mark.integration
def test_process_url_returns_required_keys():
    if not os.getenv("FIRECRAWL_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        pytest.skip("FIRECRAWL_API_KEY and OPENAI_API_KEY must be set to run integration tests")

    result = processor_service.process_url("https://example.com")

    assert isinstance(result, dict), "process_url must return a dict"
    missing = REQUIRED_KEYS - result.keys()
    assert not missing, f"Result is missing required keys: {missing}"
