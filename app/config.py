"""
Application settings loaded from environment variables / .env file.
All configuration for the bot lives here — one import, one source of truth.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Bot configuration.

    All fields map directly to environment variable names (case-insensitive).
    See .env.example for descriptions and defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # silently ignore unrecognised env vars (e.g. OHPR pipeline vars)
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    authorized_user_ids: str = ""          # comma-separated integers
    base_telegram_api_url: str = "https://api.telegram.org"

    # ── File handling ─────────────────────────────────────────────────────────
    temp_dir: str = "tmp"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def authorized_user_ids_set(self) -> set[int]:
        """
        Parse the comma-separated AUTHORIZED_USER_IDS env var into a set of ints.

        Example env value: "123456,7891011"
        Returns an empty set if the variable is missing or blank.
        """
        if not self.authorized_user_ids.strip():
            return set()
        result: set[int] = set()
        for part in self.authorized_user_ids.split(","):
            part = part.strip()
            if part.isdigit():
                result.add(int(part))
        return result

    @property
    def telegram_api_base(self) -> str:
        """Fully-qualified Telegram Bot API base URL."""
        return f"{self.base_telegram_api_url}/bot{self.telegram_bot_token}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (safe to call anywhere)."""
    return Settings()
