"""Context-efficient MCP tool-tier registration."""

from __future__ import annotations

from typing import Any

CORE_TOOL_NAMES = frozenset(
    {
        "list_accounts", "get_me", "get_chats", "list_chats", "get_chat", "get_full_chat",
        "search_public_chats", "resolve_username", "get_messages", "list_messages",
        "get_message_context", "search_messages", "search_global", "get_history",
        "get_pinned_messages", "get_media_info", "list_photos", "open_photo", "get_photo_sheet",
        "list_contacts", "search_contacts", "get_contact_ids", "get_contact_chats",
        "get_last_interaction", "get_privacy_settings", "get_user_status", "get_bot_info",
        "list_folders", "get_folder", "get_admins", "get_banned_users", "get_recent_actions",
        "cache_health", "search_cached_messages", "sync_chat_cache",
    }
)

STANDARD_ADDITIONS = frozenset(
    {
        "send_message", "reply_to_message", "forward_message", "forward_messages", "edit_message",
        "pin_message", "unpin_message", "mark_as_read", "send_reaction", "remove_reaction",
        "save_draft", "get_drafts", "clear_draft", "send_file", "send_album", "download_media",
        "upload_file", "send_voice", "send_sticker", "send_gif", "set_contact_alias",
        "list_contact_aliases", "delete_contact_alias", "add_contact", "get_direct_chat_by_contact",
        "get_common_chats", "get_message_link", "list_inline_buttons", "press_inline_button",
        "list_topics", "wait_for_new_message", "wait_for_settled_message", "incoming_feed_status",
    }
)

VALID_TIERS = frozenset({"core", "standard", "full"})


def allowed_tool_names(tier: str) -> frozenset[str] | None:
    """Return the allowlist, or ``None`` for full upstream compatibility."""
    normalized = tier.strip().lower()
    if normalized not in VALID_TIERS:
        raise ValueError("TELEGRAM_MCP_TIER must be one of: core, standard, full")
    if normalized == "full":
        return None
    if normalized == "standard":
        return CORE_TOOL_NAMES | STANDARD_ADDITIONS
    return CORE_TOOL_NAMES


def apply_tool_tier(server: Any, tier: str) -> list[str]:
    """Remove unselected tools after all modules have registered their decorators."""
    allowed = allowed_tool_names(tier)
    if allowed is None:
        return []
    registered = list(server._tool_manager.list_tools())
    removed: list[str] = []
    for tool in registered:
        if tool.name not in allowed:
            server._tool_manager.remove_tool(tool.name)
            removed.append(tool.name)
    return sorted(removed)
