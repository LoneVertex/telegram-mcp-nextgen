"""Typed data models for Telegram cache and adapter boundaries."""

from .chats import ChatRecord
from .media import MediaRecord
from .messages import (
    LINK_DOMAIN,
    MessageRecord,
    format_message_line,
    get_media_label,
    get_reply_quote,
    message_to_dict,
)

__all__ = [
    "LINK_DOMAIN",
    "ChatRecord",
    "MediaRecord",
    "MessageRecord",
    "format_message_line",
    "get_media_label",
    "get_reply_quote",
    "message_to_dict",
]
