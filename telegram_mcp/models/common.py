"""Shared typed model aliases."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class ChatRecord(TypedDict):
    chat_id: int
    title: str
    chat_type: str
    access_hash: int | None
    updated_at: str


class MessageRecord(TypedDict, total=False):
    chat_id: int
    message_id: int
    sender_id: int | None
    sender_name: str | None
    message_date: str | None
    edit_date: str | None
    text: str
    topic_id: int | None
    deleted_remotely: bool
    media_type: str | None


class MediaRecord(TypedDict):
    message_id: int
    media_type: str
    mime_type: str | None
    size_bytes: int | None
    file_name: str | None


def isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
