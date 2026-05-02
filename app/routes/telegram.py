"""
Telegram webhook route.

Single endpoint: POST /webhook/telegram

Flow:
  1. Parse the incoming Telegram Update
  2. Reject unknown / unauthorized senders
  3. Route to URL handler, PDF handler, or unsupported-input reply
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.telegram import TelegramUpdate
from app.services import auth_service, processor_service, telegram_service
from app.utils.url_utils import extract_url

logger = logging.getLogger("ohpr_bot.routes.telegram")

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/telegram", status_code=200)
async def telegram_webhook(update: TelegramUpdate) -> dict:
    """
    Handle all incoming Telegram updates.

    Telegram expects a 200 OK response quickly — processing errors are
    caught internally and reported to the user via a bot reply rather
    than surfacing as HTTP errors.
    """
    settings = get_settings()

    # edited_message has identical structure; treat it the same as message
    message = update.message or update.edited_message
    if not message:
        # Non-message update (join event, poll, etc.) — acknowledge and ignore
        return {"ok": True}

    chat_id: int = message.chat.id
    user = message.from_user
    user_id: Optional[int] = user.id if user else None
    display: str = user.display_name if user else "unknown"

    # ── Authorization ──────────────────────────────────────────────────────────
    if user_id is None or not auth_service.is_authorized(user_id):
        logger.warning(
            f"Unauthorized access attempt | user_id={user_id} | user={display} | chat_id={chat_id}"
        )
        if user_id is not None:
            await telegram_service.send_message(
                chat_id, "⛔ You are not authorized to use this bot."
            )
        return {"ok": True}

    logger.info(
        f"Authorized request | user_id={user_id} | user={display} | chat_id={chat_id}"
    )

    # ── URL flow ───────────────────────────────────────────────────────────────
    if message.text:
        url = extract_url(message.text)
        if url:
            logger.info(f"URL detected: {url} | user_id={user_id}")
            try:
                result = await asyncio.to_thread(processor_service.process_url, url)
                reply = telegram_service.format_url_reply(result)
                await telegram_service.send_message(chat_id, reply)
                logger.info(f"URL processed successfully | url={url} | user_id={user_id}")
            except Exception as exc:
                logger.error(f"Failed to process URL {url}: {exc}", exc_info=True)
                await telegram_service.send_message(
                    chat_id, "❌ Failed to process the URL. Please try again."
                )
            return {"ok": True}

    # ── PDF flow ───────────────────────────────────────────────────────────────
    if message.document:
        doc = message.document

        if not telegram_service.is_pdf(doc):
            logger.info(
                f"Non-PDF document rejected | file_name={doc.file_name} | user_id={user_id}"
            )
            await telegram_service.send_message(
                chat_id,
                "⚠️ Only PDF files are supported. Please send a <b>.pdf</b> document.",
            )
            return {"ok": True}

        logger.info(f"PDF detected: {doc.file_name} | user_id={user_id}")
        local_path: Optional[str] = None

        try:
            local_path = await telegram_service.download_telegram_file(
                file_id=doc.file_id,
                temp_dir=settings.temp_dir,
                original_name=doc.file_name,
            )
            if not local_path:
                raise RuntimeError("File download returned no path.")

            result = processor_service.process_pdf(local_path, doc.file_name)
            reply = telegram_service.format_pdf_reply(result)
            await telegram_service.send_message(chat_id, reply)
            logger.info(f"PDF processed successfully | file={doc.file_name} | user_id={user_id}")

        except Exception as exc:
            logger.error(
                f"Failed to process PDF {doc.file_name}: {exc}", exc_info=True
            )
            await telegram_service.send_message(
                chat_id, "❌ Failed to process the PDF. Please try again."
            )

        finally:
            # Always clean up — even on error
            if local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    logger.debug(f"Temp file removed: {local_path}")
                except OSError as exc:
                    logger.warning(f"Could not remove temp file {local_path}: {exc}")

        return {"ok": True}

    # ── Unsupported input ──────────────────────────────────────────────────────
    logger.info(f"Unsupported input type | user_id={user_id}")
    await telegram_service.send_message(
        chat_id,
        "ℹ️ <b>How to use this bot:</b>\n\n"
        "• Send me a <b>URL</b> to analyse a news article\n"
        "• Send me a <b>PDF file</b> to process a document\n\n"
        "That's it — I'll reply with a structured summary.",
    )
    return {"ok": True}
