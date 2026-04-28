"""
Pydantic schemas mirroring the Telegram Bot API Update object.
Only the fields we actually use are declared; extras are ignored.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    """Telegram User / Bot object."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    is_bot: bool = False
    first_name: str = ""
    last_name: Optional[str] = None
    username: Optional[str] = None

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        name = self.first_name
        if self.last_name:
            name = f"{name} {self.last_name}"
        return name or str(self.id)


class TelegramChat(BaseModel):
    """Telegram Chat object."""

    id: int
    type: str = ""


class TelegramDocument(BaseModel):
    """Telegram Document object."""

    file_id: str
    file_unique_id: str = ""
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class TelegramMessage(BaseModel):
    """Telegram Message object (subset of fields)."""

    model_config = ConfigDict(populate_by_name=True)

    message_id: int
    # "from" is a reserved keyword in Python — alias it
    from_user: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    date: int = 0
    text: Optional[str] = None
    document: Optional[TelegramDocument] = None


class TelegramUpdate(BaseModel):
    """
    Telegram Update object.
    Extensible: add callback_query, channel_post, inline_query etc. as needed.
    """

    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
