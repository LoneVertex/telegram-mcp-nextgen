"""Comprehensive verification that all 128 MCP tools are registered, tested, and declare complete annotations."""

from __future__ import annotations

import inspect

import pytest

import main
from telegram_mcp.tools import (
    add_chat_to_folder,
    add_contact,
    archive_chat,
    ban_user,
    block_user,
    # cache (3)
    cache_health,
    clear_draft,
    create_channel,
    create_folder,
    create_forum_topic,
    # groups (22)
    create_group,
    create_poll,
    delete_chat_history,
    delete_chat_photo,
    delete_contact,
    delete_contact_alias,
    delete_folder,
    delete_message,
    delete_messages_bulk,
    delete_profile_photo,
    delete_scheduled_message,
    demote_admin,
    disable_incoming_feed,
    download_media,
    edit_admin_rights,
    edit_chat_about,
    edit_chat_photo,
    edit_chat_title,
    edit_message,
    enable_forum_topics,
    enable_incoming_feed,
    export_chat_invite,
    export_contacts,
    forward_message,
    forward_messages,
    get_admins,
    get_banned_users,
    get_blocked_users,
    get_bot_info,
    get_chat,
    # chats (17)
    get_chats,
    get_common_chats,
    get_contact_chats,
    get_contact_ids,
    get_direct_chat_by_contact,
    get_drafts,
    get_folder,
    get_full_chat,
    get_full_user,
    get_gif_search,
    get_history,
    get_invite_link,
    get_last_interaction,
    # profile (11)
    get_me,
    get_media_info,
    get_message_context,
    get_message_link,
    get_message_reactions,
    get_message_read_by,
    # messages (31)
    get_messages,
    get_participants,
    get_photo_sheet,
    get_pinned_messages,
    get_privacy_settings,
    get_recent_actions,
    get_scheduled_messages,
    get_sticker_sets,
    get_user_photos,
    get_user_status,
    import_chat_invite,
    import_contacts,
    incoming_feed_status,
    invite_to_group,
    join_chat_by_link,
    leave_chat,
    # accounts (1)
    list_accounts,
    list_chats,
    list_contact_aliases,
    # contacts (17)
    list_contacts,
    # folders (7)
    list_folders,
    list_inline_buttons,
    list_messages,
    list_photos,
    list_topics,
    mark_as_read,
    mute_chat,
    open_photo,
    pin_message,
    press_inline_button,
    promote_admin,
    remove_chat_from_folder,
    remove_reaction,
    reorder_folders,
    reply_to_message,
    resolve_username,
    save_draft,
    search_cached_messages,
    search_contacts,
    search_global,
    search_messages,
    search_public_chats,
    send_album,
    send_contact,
    # media (13)
    send_file,
    send_gif,
    send_message,
    send_reaction,
    send_scheduled_message,
    send_sticker,
    send_voice,
    set_bot_commands,
    set_contact_alias,
    set_default_chat_permissions,
    set_privacy_settings,
    set_profile_photo,
    subscribe_public_channel,
    sync_chat_cache,
    toggle_slow_mode,
    unarchive_chat,
    unban_user,
    unblock_user,
    unmute_chat,
    unpin_all_messages,
    unpin_message,
    update_profile,
    upload_file,
    # events (5)
    wait_for_new_message,
    wait_for_settled_message,
)

ALL_TOOL_FUNCTIONS = [
    # accounts
    list_accounts,
    # cache
    cache_health,
    search_cached_messages,
    sync_chat_cache,
    # chats
    get_chats,
    subscribe_public_channel,
    list_topics,
    enable_forum_topics,
    create_forum_topic,
    list_chats,
    get_chat,
    search_public_chats,
    resolve_username,
    get_full_chat,
    mute_chat,
    unmute_chat,
    archive_chat,
    unarchive_chat,
    get_common_chats,
    get_message_read_by,
    get_message_link,
    # contacts
    list_contacts,
    search_contacts,
    get_contact_ids,
    get_direct_chat_by_contact,
    get_contact_chats,
    get_last_interaction,
    add_contact,
    delete_contact,
    block_user,
    unblock_user,
    import_contacts,
    export_contacts,
    get_blocked_users,
    send_contact,
    set_contact_alias,
    list_contact_aliases,
    delete_contact_alias,
    # events
    wait_for_new_message,
    wait_for_settled_message,
    enable_incoming_feed,
    disable_incoming_feed,
    incoming_feed_status,
    # folders
    list_folders,
    get_folder,
    create_folder,
    add_chat_to_folder,
    remove_chat_from_folder,
    delete_folder,
    reorder_folders,
    # groups
    create_group,
    invite_to_group,
    leave_chat,
    create_channel,
    edit_chat_title,
    edit_chat_photo,
    edit_chat_about,
    delete_chat_photo,
    promote_admin,
    demote_admin,
    ban_user,
    unban_user,
    set_default_chat_permissions,
    toggle_slow_mode,
    edit_admin_rights,
    get_admins,
    get_banned_users,
    get_invite_link,
    join_chat_by_link,
    export_chat_invite,
    import_chat_invite,
    get_recent_actions,
    get_participants,
    # media
    send_file,
    send_album,
    download_media,
    send_voice,
    upload_file,
    get_media_info,
    get_sticker_sets,
    send_sticker,
    get_gif_search,
    send_gif,
    list_photos,
    open_photo,
    get_photo_sheet,
    # messages
    get_messages,
    send_message,
    send_scheduled_message,
    get_scheduled_messages,
    delete_scheduled_message,
    list_inline_buttons,
    press_inline_button,
    list_messages,
    get_message_context,
    forward_message,
    forward_messages,
    edit_message,
    delete_message,
    delete_chat_history,
    delete_messages_bulk,
    pin_message,
    unpin_message,
    unpin_all_messages,
    mark_as_read,
    reply_to_message,
    search_messages,
    search_global,
    get_history,
    get_pinned_messages,
    create_poll,
    send_reaction,
    remove_reaction,
    get_message_reactions,
    save_draft,
    get_drafts,
    clear_draft,
    # profile
    get_me,
    update_profile,
    set_profile_photo,
    delete_profile_photo,
    get_privacy_settings,
    set_privacy_settings,
    get_full_user,
    get_bot_info,
    set_bot_commands,
    get_user_photos,
    get_user_status,
]


def test_tool_count_is_exactly_128():
    """Verify that exactly 128 tools are registered in total."""
    assert len(ALL_TOOL_FUNCTIONS) == 128
    registered_tools = main.mcp._tool_manager._tools
    assert len(registered_tools) == 128


@pytest.mark.parametrize("fn", ALL_TOOL_FUNCTIONS, ids=lambda f: f.__name__)
def test_each_tool_is_registered_with_complete_hints(fn):
    """Verify that every tool function is registered and declares all four boolean hints."""
    name = fn.__name__
    registered = main.mcp._tool_manager._tools.get(name)
    assert registered is not None, f"Tool '{name}' is not registered on the MCP server."

    annotations = getattr(registered, "annotations", None)
    assert annotations is not None, f"Tool '{name}' has no annotations."

    # Validate title
    assert annotations.title and isinstance(annotations.title, str), f"Tool '{name}' missing title."

    # Validate all 4 hints are strict booleans
    assert isinstance(
        annotations.readOnlyHint, bool
    ), f"Tool '{name}' readOnlyHint must be bool, got {type(annotations.readOnlyHint)}"
    assert isinstance(
        annotations.destructiveHint, bool
    ), f"Tool '{name}' destructiveHint must be bool, got {type(annotations.destructiveHint)}"
    assert isinstance(
        annotations.idempotentHint, bool
    ), f"Tool '{name}' idempotentHint must be bool, got {type(annotations.idempotentHint)}"
    assert isinstance(
        annotations.openWorldHint, bool
    ), f"Tool '{name}' openWorldHint must be bool, got {type(annotations.openWorldHint)}"

    # Read-only tools must not be destructive
    if annotations.readOnlyHint is True:
        assert annotations.destructiveHint is False, f"Read-only tool '{name}' cannot be destructive."
        assert annotations.idempotentHint is True, f"Read-only tool '{name}' must be idempotent."

    # Verify docstring exists
    doc = inspect.getdoc(fn)
    assert doc and len(doc.strip()) > 0, f"Tool '{name}' has no docstring."
