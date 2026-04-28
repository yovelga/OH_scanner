"""
Basic end-to-end tests for the webhook routes.
Run with: pytest tests/ -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Utility endpoints ─────────────────────────────────────────────────────────


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()


# ── Webhook — edge cases ──────────────────────────────────────────────────────


def test_telegram_webhook_no_message():
    """Update with no message should be silently acknowledged."""
    payload = {"update_id": 1}
    response = client.post("/webhook/telegram", json=payload)
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_telegram_webhook_unauthorized_user():
    """User not in AUTHORIZED_USER_IDS receives a rejection message."""
    payload = {
        "update_id": 2,
        "message": {
            "message_id": 1,
            "from": {"id": 99999999, "is_bot": False, "first_name": "Stranger"},
            "chat": {"id": 99999999, "type": "private"},
            "date": 1700000000,
            "text": "https://example.com/article",
        },
    }
    with patch(
        "app.services.telegram_service.send_message", new_callable=AsyncMock
    ) as mock_send:
        response = client.post("/webhook/telegram", json=payload)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_send.assert_called_once()
    sent_text: str = mock_send.call_args[0][1]
    assert "not authorized" in sent_text.lower()


def test_telegram_webhook_url_message():
    """Authorized user sending a URL triggers process_url and a reply."""
    payload = {
        "update_id": 3,
        "message": {
            "message_id": 2,
            "from": {"id": 111111111, "is_bot": False, "first_name": "Test"},
            "chat": {"id": 111111111, "type": "private"},
            "date": 1700000000,
            "text": "Check this out: https://example.com/article",
        },
    }
    with (
        patch("app.services.auth_service.is_authorized", return_value=True),
        patch(
            "app.services.processor_service.process_url",
            return_value={
                "input_type": "url",
                "source": "https://example.com/article",
                "status": "processed",
                "title": "Test",
                "sentiment": "Neutral",
                "topic": "Test",
                "language": "en",
            },
        ),
        patch(
            "app.services.telegram_service.send_message", new_callable=AsyncMock
        ) as mock_send,
    ):
        response = client.post("/webhook/telegram", json=payload)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_send.assert_called_once()
    sent_text: str = mock_send.call_args[0][1]
    assert "Article Processed" in sent_text


def test_telegram_webhook_unsupported_input():
    """Authorized user sending a non-URL text gets a usage hint."""
    payload = {
        "update_id": 4,
        "message": {
            "message_id": 3,
            "from": {"id": 111111111, "is_bot": False, "first_name": "Test"},
            "chat": {"id": 111111111, "type": "private"},
            "date": 1700000000,
            "text": "Hello there",
        },
    }
    with (
        patch("app.services.auth_service.is_authorized", return_value=True),
        patch(
            "app.services.telegram_service.send_message", new_callable=AsyncMock
        ) as mock_send,
    ):
        response = client.post("/webhook/telegram", json=payload)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_send.assert_called_once()
    sent_text: str = mock_send.call_args[0][1]
    assert "URL" in sent_text


def test_url_extractor():
    """Verify regex URL extraction works correctly."""
    from app.utils.url_utils import extract_url, is_valid_url

    assert extract_url("Visit https://example.com now") == "https://example.com"
    assert extract_url("no url here") is None
    assert is_valid_url("https://example.com/path?q=1") is True
    assert is_valid_url("not-a-url") is False
