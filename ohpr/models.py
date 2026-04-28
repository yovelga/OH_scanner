from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class ArticleResult(BaseModel):
    url: Optional[str] = None
    date: Optional[str] = None          # ISO 8601 (YYYY-MM-DD)
    platform_name: Optional[str] = None
    platform_link: Optional[str] = None
    sentiment: Optional[str] = None     # positive | negative | neutral
    topic: Optional[str] = None         # short, 3-5 words
    media_type: Optional[str] = None    # news | blog | press_release | social | forum | podcast | video | other
    segment: Optional[str] = None       # technology | finance | health | politics | entertainment | sports | business | other
    tier: Optional[str] = None          # tier1 | tier2 | tier3
    organic_paid: Optional[str] = None  # organic | paid | unknown
    language: Optional[str] = None      # ISO 639-1 (e.g. "en")
    title: Optional[str] = None
    summary: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 – 1.0
    needs_review: Optional[bool] = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: object) -> Optional[float]:
        if v is None:
            return None
        try:
            f = float(v)
            return round(max(0.0, min(1.0, f)), 3)
        except (ValueError, TypeError):
            return None

    @field_validator("sentiment", mode="before")
    @classmethod
    def validate_sentiment(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        allowed = {"positive", "negative", "neutral"}
        s = str(v).lower().strip()
        return s if s in allowed else None

    @field_validator("tier", mode="before")
    @classmethod
    def validate_tier(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        allowed = {"tier1", "tier2", "tier3"}
        s = str(v).lower().strip()
        return s if s in allowed else None

    @field_validator("organic_paid", mode="before")
    @classmethod
    def validate_organic_paid(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        allowed = {"organic", "paid", "unknown"}
        s = str(v).lower().strip()
        return s if s in allowed else None
