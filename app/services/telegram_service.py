"""
Telegram service — all direct communication with the Telegram Bot API.

Responsibilities:
  - Sending messages
  - Fetching file metadata (getFile)
  - Downloading files to the local temp directory
  - Validating document types
  - Formatting bot reply text
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings
from app.schemas.telegram import TelegramDocument

logger = logging.getLogger("ohpr_bot.telegram")

# Shared timeout config — generous for file downloads, tight for messages
_MSG_TIMEOUT = httpx.Timeout(10.0)
_FILE_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


# ── Messaging ─────────────────────────────────────────────────────────────────


async def send_message(chat_id: int, text: str) -> bool:
    """
    Send a text message to a Telegram chat.

    Args:
        chat_id: Target chat or user ID.
        text:    Message body (HTML formatting supported).

    Returns:
        True on success, False on any HTTP or API error.
    """
    settings = get_settings()
    url = f"{settings.telegram_api_base}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    try:
        async with httpx.AsyncClient(timeout=_MSG_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"Telegram sendMessage HTTP error {exc.response.status_code} "
            f"for chat_id={chat_id}: {exc.response.text}"
        )
    except httpx.RequestError as exc:
        logger.error(f"Telegram sendMessage request error for chat_id={chat_id}: {exc}")
    return False


# ── File operations ───────────────────────────────────────────────────────────


async def get_file_path(file_id: str) -> Optional[str]:
    """
    Call Telegram getFile to resolve a file_id to a server-side path.

    Args:
        file_id: Telegram file_id from the Document object.

    Returns:
        The file_path string, or None on failure.
    """
    settings = get_settings()
    url = f"{settings.telegram_api_base}/getFile"

    try:
        async with httpx.AsyncClient(timeout=_MSG_TIMEOUT) as client:
            response = await client.post(url, json={"file_id": file_id})
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data["result"].get("file_path")
            logger.error(f"Telegram getFile not ok: {data}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Telegram getFile HTTP error {exc.response.status_code}: {exc.response.text}")
    except httpx.RequestError as exc:
        logger.error(f"Telegram getFile request error: {exc}")

    return None


async def download_file(tg_file_path: str, local_path: str) -> bool:
    """
    Download a file from Telegram's CDN to a local path.

    Args:
        tg_file_path: Server-side path returned by getFile (e.g. "documents/file_0.pdf").
        local_path:   Absolute local destination path.

    Returns:
        True on success, False on failure.
    """
    settings = get_settings()
    download_url = (
        f"{settings.base_telegram_api_url}"
        f"/file/bot{settings.telegram_bot_token}"
        f"/{tg_file_path}"
    )

    try:
        async with httpx.AsyncClient(timeout=_FILE_TIMEOUT) as client:
            async with client.stream("GET", download_url) as response:
                response.raise_for_status()
                with open(local_path, "wb") as fh:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        fh.write(chunk)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(f"Telegram file download HTTP error {exc.response.status_code}")
    except httpx.RequestError as exc:
        logger.error(f"Telegram file download request error: {exc}")
    except OSError as exc:
        logger.error(f"Failed to write downloaded file to {local_path}: {exc}")

    return False


async def download_telegram_file(
    file_id: str,
    temp_dir: str,
    original_name: Optional[str] = None,
) -> Optional[str]:
    """
    Full pipeline: resolve file_id → download → return local temp path.

    Creates a UUID-named file inside *temp_dir* so concurrent downloads
    never collide.

    Args:
        file_id:       Telegram file_id.
        temp_dir:      Directory to write the temp file into.
        original_name: Original filename from Telegram (used only for the extension).

    Returns:
        Absolute local path of the downloaded file, or None on failure.
    """
    Path(temp_dir).mkdir(parents=True, exist_ok=True)

    tg_file_path = await get_file_path(file_id)
    if not tg_file_path:
        logger.error(f"Could not resolve file path for file_id={file_id}")
        return None

    extension = Path(original_name).suffix.lower() if original_name else ".pdf"
    local_filename = f"{uuid.uuid4().hex}{extension}"
    local_path = str(Path(temp_dir) / local_filename)

    success = await download_file(tg_file_path, local_path)
    return local_path if success else None


# ── Validation ────────────────────────────────────────────────────────────────


def is_pdf(document: TelegramDocument) -> bool:
    """
    Return True if the Telegram document is a PDF.

    Checks both MIME type and filename extension so the validation
    works even when one of the two is missing.

    Args:
        document: TelegramDocument from the incoming message.
    """
    if document.mime_type and document.mime_type.lower() == "application/pdf":
        return True
    if document.file_name and document.file_name.lower().endswith(".pdf"):
        return True
    return False


# ── Reply formatting ──────────────────────────────────────────────────────────


def format_url_reply(result: dict) -> str:
    """
    Render a URL processing result as a readable HTML Telegram message.

    Args:
        result: Dict returned by processor_service.process_url().
    """
    lines = [
        "📰 <b>Article Processed</b>",
        "",
        f"• <b>Input type:</b> URL",
        f"• <b>Source:</b> {result.get('source', '—')}",
        f"• <b>Status:</b> {result.get('status', '—')}",
        f"• <b>Title:</b> {result.get('title', '—')}",
        f"• <b>Topic:</b> {result.get('topic', '—')}",
        f"• <b>Sentiment:</b> {result.get('sentiment', '—')}",
        f"• <b>Language:</b> {result.get('language', '—')}",
    ]
    summary = result.get("summary")
    if summary:
        lines += ["", f"📋 <b>Summary:</b> {summary}"]
    return "\n".join(lines)


def format_pdf_reply(result: dict) -> str:
    """
    Render a PDF processing result as a readable HTML Telegram message.

    Args:
        result: Dict returned by processor_service.process_pdf().
    """
    lines = [
        "📄 <b>PDF Processed</b>",
        "",
        f"• <b>Input type:</b> PDF",
        f"• <b>File name:</b> {result.get('file_name', '—')}",
        f"• <b>Status:</b> {result.get('status', '—')}",
        f"• <b>Title:</b> {result.get('title', '—')}",
        f"• <b>Document type:</b> {result.get('document_type', '—')}",
        f"• <b>Language:</b> {result.get('language', '—')}",
    ]
    summary = result.get("summary")
    if summary:
        lines += ["", f"📋 <b>Summary:</b> {summary}"]
    return "\n".join(lines)
