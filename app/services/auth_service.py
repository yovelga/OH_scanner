"""
Authorization service — allowlist-based user validation.

The authorized set is loaded once from settings.
To add/remove users, update AUTHORIZED_USER_IDS in .env and restart.
"""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger("ohpr_bot.auth")


def is_authorized(user_id: int) -> bool:
    """
    Return True if *user_id* is in the authorized allowlist.

    If AUTHORIZED_USER_IDS is not configured (empty), all users are blocked
    and a warning is emitted so the misconfiguration is obvious in logs.

    Args:
        user_id: Telegram user ID to check.
    """
    allowed = get_settings().authorized_user_ids_set
    if not allowed:
        logger.warning(
            "AUTHORIZED_USER_IDS is empty — all requests are blocked. "
            "Add user IDs to .env to enable access."
        )
        return False
    return user_id in allowed
