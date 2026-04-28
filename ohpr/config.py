from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    FIRECRAWL_TIMEOUT: int = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))


settings = Settings()
