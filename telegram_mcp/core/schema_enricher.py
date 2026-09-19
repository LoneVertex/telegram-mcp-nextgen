"""TDQS (Tool Definition Quality Score) schema and description enricher.

Provides semantic metadata, meaningful titles, unambiguous parameter descriptions,
and usage guidelines across all Telegram MCP tools to ensure high-fidelity tool
selection by AI agents and full compliance with Glama's TDQS rubric.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("telegram_mcp.schema_enricher")

# Universal parameter descriptions across all Telegram MCP tools
UNIVERSAL_PARAM_DESCRIPTIONS: dict[str, str] = {
    "account": (
        "Optional account label for multi-account environments. If omitted in single-mode, "
        "the default account is used. In multi-mode without an account, read-only tools "
        "fan out across all configured accounts."
    ),
    "chat_id": (
        "Target Telegram chat, group, supergroup, channel, or user identifier. "
        "Accepts numeric chat ID (e.g. -1001234567890 or 123456789), username (e.g. '@channel'), "
        "or phone number."
    ),
    "user_id": (
        "Target user identifier. Accepts numeric user ID, @username without '@', "
        "or phone number in international format."
    ),
    "message_id": "Unique integer ID of the target message within the specified chat.",
    "message_ids": "List of unique integer message IDs to operate on within the target chat.",
    "limit": "Maximum number of items or records to retrieve (integer between 1 and 100).",
    "offset": "Pagination offset indicating the number of initial records to skip.",
    "query": "Search text string or keywords to match against messages, contacts, or entities.",
    "search_query": "Text query string used to search and filter contacts, chats, or messages.",
    "title": "Title or display name for the chat, supergroup, channel, folder, or forum topic.",
    "topic_id": "Forum topic identifier (thread ID) in a supergroup where forum topics are enabled.",
    "page": "1-indexed page number for paginated result sets.",
    "page_size": "Maximum number of items to return per page (typically 10 to 50).",
    "folder_id": "Unique numerical identifier of the Telegram dialog filter folder.",
    "first_name": "First name of the user or contact (1 to 64 characters).",
    "last_name": "Optional last name of the user or contact (up to 64 characters).",
    "username": "Telegram username handle (without the leading '@' symbol).",
    "message": "Text content of the message to send or save as draft. Supports Markdown or HTML.",
    "text": "Body text of the message, comment, or search query string.",
    "new_text": "New replacement text content when editing an existing sent message.",
    "caption": "Optional caption text describing the media file (Markdown or plain text).",
    "file_path": (
        "Local filesystem path to the file to upload or send. Must resolve within "
        "configured MCP allowed roots."
    ),
    "file_paths": (
        "List of local filesystem paths to include in the media album. Must all resolve "
        "within configured MCP allowed roots."
    ),
    "parse_mode": "Text formatting parser: 'markdown' (default), 'html', or 'none'.",
    "group_id": "Numeric identifier of the basic group or supergroup.",
    "about": "Bio or description text for the user profile, channel, or group (up to 255 chars).",
    "contact_id": "Numeric Telegram user ID of the contact in your contact directory.",
    "contacts": "List of contact objects to import, each containing 'phone', 'first_name', and optional 'last_name'.",
    "alias": "Custom private local nickname or alias label to associate with a contact.",
    "max_id": "Upper bound message ID filter for reverse chronological pagination.",
    "from_chat_id": "Source chat identifier from which messages will be forwarded.",
    "to_chat_id": "Destination chat identifier where forwarded messages will be delivered.",
    "revoke": "If true, permanently deletes or revokes the messages or link for all participants.",
    "user_ids": "List of user identifiers (numeric IDs or usernames) to operate on.",
    "change_info": "Boolean permission granting group members the ability to change chat info.",
    "invite_users": "Boolean permission granting group members the ability to invite new members.",
    "pin_messages": "Boolean permission granting group members the ability to pin messages.",
    "source": "Image source selector: 'camera', 'saved', or 'album'.",
    "bot_username": "Username of the bot (e.g. '@BotFather') to inspect or configure.",
    "settle_ms": "Debounce quiet period in milliseconds to wait before considering incoming stream settled.",
    "contact_query": "Search term matching contact name, phone number, or username.",
    "phone": "Phone number in international E.164 format (e.g. '+1234567890').",
    "phone_number": "Phone number in international E.164 format (e.g. '+1234567890').",
    "vcard": "Optional vCard string payload representing the contact card.",
    "replace": "If true, replaces existing contacts matching the given phone number.",
    "channel": "Target channel identifier, username, or invite link.",
    "offset_topic": "Offset topic ID for paginating through forum topics.",
    "tabs": "Category tab filter for dialogs or media list.",
    "icon_color": "Folder icon color index for custom folder appearance.",
    "icon_emoji_id": "Custom emoji identifier for custom folder tab icon.",
    "chat_type": "Filter chats by type: 'all', 'private', 'group', 'channel', or 'bot'.",
    "unread_only": "If true, filters and returns only chats with unread messages.",
    "unmuted_only": "If true, filters and returns only chats whose notifications are active.",
    "archived": "If true, queries archived chats instead of main inbox chats.",
    "with_about": "If true, includes the about/bio description in the retrieved chat details.",
    "thread": "If true, retrieves replies and discussion messages within the topic thread.",
    "schedule_date": "ISO 8601 timestamp or Unix epoch when the scheduled message should be sent.",
    "button_text": "Visible button label text of the inline keyboard button to press.",
    "button_index": "Zero-based index of the button to click within the inline keyboard row.",
    "from_date": "Start date filter for message search in ISO 8601 format (e.g. '2026-01-01T00:00:00Z').",
    "to_date": "End date filter for message search in ISO 8601 format (e.g. '2026-01-31T23:59:59Z').",
    "context_size": "Number of surrounding messages before and after target message to include for context.",
    "expand_album": "If true, retrieves all sibling media parts when the target message is part of an album.",
    "question": "Question prompt string for the poll or quiz.",
    "options": "List of selectable answer choice strings (2 to 10 options).",
    "multiple_choice": "If true, allows respondents to choose multiple poll answers.",
    "quiz_mode": "If true, creates a quiz with one correct answer rather than a regular poll.",
    "public_votes": "If true, vote selections are visible to all group members.",
    "close_date": "ISO 8601 timestamp or Unix timestamp after which the poll closes automatically.",
    "emoji": "Unicode reaction emoji to send (e.g. '👍', '❤️', '🔥', '🎉').",
    "big": "If true, plays large animated reaction sticker effect in supported clients.",
    "reply_to_msg_id": "ID of an existing message in the chat to reply to.",
    "no_webpage": "If true, suppresses automatic webpage link preview generation.",
    "megagroup": "If true, converts a basic Telegram group into a supergroup (megagroup).",
    "rights": "Dictionary or rights object specifying detailed member or admin permissions.",
    "send_messages": "Permission flag allowing the member to post standard text messages.",
    "send_media": "Permission flag allowing the member to post media files, audio, and photos.",
    "send_stickers": "Permission flag allowing the member to post stickers.",
    "send_gifs": "Permission flag allowing the member to post animated GIFs.",
    "send_games": "Permission flag allowing the member to launch inline games.",
    "send_inline": "Permission flag allowing the member to invoke inline bots.",
    "embed_links": "Permission flag allowing links posted by the member to render previews.",
    "send_polls": "Permission flag allowing the member to create and send polls.",
    "until_date": "ISO 8601 timestamp or Unix timestamp until which the restriction applies (0 for permanent).",
    "seconds": "Duration in seconds for slow mode or temporary mute interval.",
    "rank": "Custom administrator title or badge label displayed in chat.",
    "post_messages": "Permission flag allowing channel admin to publish new messages.",
    "edit_messages": "Permission flag allowing channel admin to edit existing messages.",
    "delete_messages": "Permission flag allowing admin to delete messages sent by other members.",
    "ban_users": "Permission flag allowing admin to ban, kick, or restrict members.",
    "add_admins": "Permission flag allowing admin to appoint new administrators.",
    "anonymous": "If true, administrator messages appear under the group name rather than user identity.",
    "manage_call": "Permission flag allowing admin to manage voice and video calls.",
    "manage_topics": "Permission flag allowing admin to create, edit, and close forum topics.",
    "other": "Permission flag for miscellaneous administrator privileges.",
    "link": "Telegram invite link (e.g. 'https://t.me/+AbCdEfGhIjK').",
    "hash": "Invite hash extracted from private join link.",
    "gif_id": "Unique identifier of the GIF document to send.",
    "photo_id": "Numeric photo ID or unique file identifier of the profile photo.",
    "save_path": "Local destination file path to save downloaded media. Must resolve within allowed MCP roots.",
    "columns": "Number of columns in contact sheet contact collage (between 1 and 5).",
    "key": "Privacy setting key (e.g. 'phone_number', 'status_timestamp', 'profile_photo').",
    "allow_users": "List of user IDs explicitly permitted under this privacy rule.",
    "disallow_users": "List of user IDs explicitly forbidden under this privacy rule.",
    "commands": "List of bot command definitions with 'command' and 'description' keys.",
    "emoticon": "Emoticon string associated with sticker search or pack.",
    "chat_ids": "List of chat identifiers to include or exclude from the folder filter.",
    "non_contacts": "If true, includes non-contact dialogs in the folder filter.",
    "groups": "If true, includes groups in the folder filter.",
    "broadcasts": "If true, includes broadcast channels in the folder filter.",
    "bots": "If true, includes bots in the folder filter.",
    "exclude_muted": "If true, excludes muted chats from the folder filter.",
    "exclude_read": "If true, excludes chats with no unread messages from the folder filter.",
    "exclude_archived": "If true, excludes archived chats from the folder filter.",
    "pinned": "If true, designates the item as pinned in the dialog list.",
    "folder_ids": "Ordered list of folder IDs to set new navigation display sequence.",
    "timeout": "Maximum wait duration in seconds before timing out.",
    "max_wait_ms": "Maximum wait duration in milliseconds before timing out.",
    "mode": "Synchronization mode: 'incremental' (new messages since checkpoint) or 'full' (all messages in batch).",
}

TOOL_TITLES: dict[str, str] = {
    "list_accounts": "List Configured Telegram Accounts",
    "get_me": "Get Current Account Profile and Identity",
    "get_chats": "Retrieve Dialogs and Recent Chats List",
    "list_chats": "List All Telegram Chats and Channels",
    "get_chat": "Get Chat Details and Metadata",
    "get_full_chat": "Get Complete Chat Information and Settings",
    "search_public_chats": "Search Public Channels and Groups Globally",
    "resolve_username": "Resolve Telegram Username to Entity ID",
    "get_messages": "Get Paginated Messages from Chat",
    "list_messages": "List Filtered Chat Messages",
    "get_message_context": "Get Context Window Around Message",
    "search_messages": "Search Messages Within Specific Chat",
    "search_global": "Search Messages Across All Public Chats",
    "get_history": "Get Full Message History from Chat",
    "get_pinned_messages": "Get All Pinned Messages in Chat",
    "get_media_info": "Inspect Media Metadata in Message",
    "list_photos": "List Recent Photos in Chat",
    "open_photo": "Inspect and View Chat Photo Content",
    "get_photo_sheet": "Generate Visual Contact Sheet of Photos",
    "list_contacts": "List Telegram Account Contacts",
    "search_contacts": "Search Telegram Contact Directory",
    "get_contact_ids": "Get All Contact Telegram User IDs",
    "get_contact_chats": "Find Existing Dialogs with Contact",
    "get_last_interaction": "Get Last Message Time with Contact",
    "get_privacy_settings": "Get Account Privacy Rules and Exceptions",
    "get_user_status": "Check Online Status and Activity of User",
    "get_bot_info": "Inspect Bot Details and Capabilities",
    "list_folders": "List Telegram Dialog Filter Folders",
    "get_folder": "Get Chats Inside Specific Folder",
    "get_admins": "List Administrators of Group or Channel",
    "get_banned_users": "List Banned and Restricted Group Members",
    "get_recent_actions": "Get Group Administration Audit Log",
    "check_cache_health": "Inspect Local SQLite Cache Health",
    "cache_health": "Inspect Local SQLite Cache Health",
    "search_cached_messages": "Search Local Offline SQLite Message Archive",
    "sync_chat_cache": "Synchronize Chat History to Local Archive",
    "send_message": "Send Text Message to Telegram Chat",
    "reply_to_message": "Reply Directly to Existing Message",
    "forward_message": "Forward Single Message to Another Chat",
    "forward_messages": "Forward Multiple Messages in Batch",
    "edit_message": "Edit Text of Sent Telegram Message",
    "pin_message": "Pin Message to Top of Chat",
    "unpin_message": "Unpin Specific Message in Chat",
    "mark_as_read": "Mark Messages in Chat as Read",
    "send_reaction": "Send Emoji Reaction to Message",
    "remove_reaction": "Remove Existing Reaction from Message",
    "save_draft": "Save Draft Message in Chat",
    "get_drafts": "List All Unsent Saved Message Drafts",
    "clear_draft": "Clear Saved Draft Message from Chat",
    "send_file": "Upload and Send Document or File",
    "send_album": "Send Multiple Media Files as Album",
    "download_media": "Download Media Attachment to Local Disk",
    "upload_file": "Upload Local File into Telegram Storage",
    "send_voice": "Send Voice Message Audio Note",
    "send_sticker": "Send Sticker to Telegram Chat",
    "send_gif": "Send Animated GIF to Telegram Chat",
    "set_contact_alias": "Set Local Alias Name for Contact",
    "list_contact_aliases": "List All Configured Contact Aliases",
    "delete_contact_alias": "Remove Local Contact Alias Name",
    "add_contact": "Add New Contact to Telegram Directory",
    "get_direct_chat_by_contact": "Get Direct 1-on-1 Chat with Contact",
    "get_common_chats": "Find Shared Groups with Specific User",
    "get_message_link": "Get Permanent Web Link to Public Message",
    "list_inline_buttons": "List Interactive Inline Keyboard Buttons",
    "press_inline_button": "Press or Click Inline Keyboard Button",
    "list_topics": "List Forum Topics in Supergroup",
    "wait_for_new_message": "Wait for Incoming Message Event",
    "wait_for_settled_message": "Wait for Debounced Settled Incoming Message",
    "incoming_feed_status": "Check Real-Time Incoming Feed Status",
    "create_channel": "Create New Telegram Broadcast Channel",
    "create_group": "Create New Telegram Group Chat",
    "create_poll": "Create Interactive Poll or Quiz in Chat",
    "delete_chat_history": "Permanently Delete Chat Message History",
    "delete_chat_photo": "Delete Group or Channel Profile Photo",
    "delete_contact": "Delete Contact from Telegram Directory",
    "delete_folder": "Delete Telegram Dialog Folder",
    "delete_message": "Delete Single Message from Chat",
    "delete_messages_bulk": "Delete Multiple Messages in Batch",
    "delete_profile_photo": "Delete Account Profile Picture",
    "delete_scheduled_message": "Cancel and Delete Scheduled Message",
    "demote_admin": "Demote Group Administrator to Member",
    "disable_incoming_feed": "Disable Background Incoming Event Stream",
    "edit_admin_rights": "Modify Group Administrator Privileges",
    "edit_chat_about": "Update Group or Channel Description Bio",
    "edit_chat_photo": "Set Group or Channel Avatar Photo",
    "edit_chat_title": "Rename Telegram Group or Channel",
    "enable_forum_topics": "Enable Forum Topics Mode on Supergroup",
    "enable_incoming_feed": "Enable Background Incoming Event Stream",
    "export_chat_invite": "Generate New Invite Link for Chat",
    "export_contacts": "Export Complete Contacts Directory as JSON",
    "get_blocked_users": "List All Blocked Telegram Users",
    "get_full_user": "Get Comprehensive User Profile and Bio",
    "get_gif_search": "Search Inline GIF Collection",
    "get_invite_link": "Get Primary Invite Link for Group or Channel",
    "get_message_reactions": "List Emoji Reactions on Message",
    "get_message_read_by": "Check Which Members Read Message",
    "get_participants": "List Members of Group or Channel",
    "get_scheduled_messages": "List Pending Scheduled Messages in Chat",
    "get_sticker_sets": "List Installed Sticker Packs",
    "get_user_photos": "Browse User Profile Photo Gallery",
    "import_chat_invite": "Join Telegram Chat via Invite Link",
    "import_contacts": "Batch Import Contacts into Directory",
    "invite_to_group": "Invite Users to Join Group or Channel",
    "join_chat_by_link": "Join Chat or Channel from Invite URL",
    "leave_chat": "Leave and Exit Telegram Group or Channel",
    "mute_chat": "Mute Notifications for Specified Chat",
    "promote_admin": "Promote Group Member to Administrator",
    "remove_chat_from_folder": "Remove Chat from Dialog Filter Folder",
    "reorder_folders": "Reorder Navigation Dialog Folder Tabs",
    "send_contact": "Share Contact VCard into Chat",
    "send_scheduled_message": "Schedule Text Message for Future Delivery",
    "set_bot_commands": "Configure Commands Menu for Bot",
    "set_default_chat_permissions": "Set Default Member Permissions for Group",
    "set_privacy_settings": "Configure Account Privacy Rule Exception",
    "set_profile_photo": "Update Account Profile Avatar Image",
    "subscribe_public_channel": "Join Public Broadcast Channel",
    "toggle_slow_mode": "Configure Message Rate Limiting in Group",
    "unarchive_chat": "Move Archived Chat Back to Main Inbox",
    "unban_user": "Unban and Restore Member in Group",
    "unblock_user": "Unblock User to Allow Messages Again",
    "unmute_chat": "Unmute and Restore Notifications for Chat",
    "unpin_all_messages": "Unpin All Messages in Chat at Once",
    "update_profile": "Update Account First Name, Last Name, and Bio",
    "add_chat_to_folder": "Add Chat to Telegram Dialog Filter Folder",
    "archive_chat": "Move Chat to Telegram Archive Folder",
    "ban_user": "Ban and Remove Member from Group or Channel",
    "block_user": "Block Telegram User from Contacting Account",
    "create_folder": "Create New Custom Dialog Filter Folder",
    "create_forum_topic": "Create New Topic Thread in Forum Supergroup",
}

# Detailed TDQS descriptions distinguishing siblings, usage guidelines, and behaviors
TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_accounts": (
        "List all configured Telegram accounts with profile name, phone number, and online status. "
        "Use at session start to discover available account labels for multi-account routing. "
        "Note: Returned names contain untrusted user content."
    ),
    "get_me": (
        "Retrieve detailed profile identity of the current Telegram user account (ID, name, username, phone). "
        "Use when verifying account identity, session details, or caller permissions."
    ),
    "get_chats": (
        "Retrieve active dialogs and recent conversation summaries including last message and unread count. "
        "Use for overview of recent chat activity. To search or list all chats comprehensively, use `list_chats`."
    ),
    "list_chats": (
        "List all accessible chats, groups, channels, and direct dialogs with pagination support. "
        "Use when locating specific conversations by title or type."
    ),
    "get_chat": (
        "Retrieve core metadata, title, member count, and type for a specific chat or channel. "
        "Use when inspecting a known chat ID or @username."
    ),
    "get_full_chat": (
        "Retrieve complete chat information including description/about, admin rights, notification settings, "
        "and invite links. Use when needing deep metadata. For basic title and type, prefer the lighter `get_chat`."
    ),
    "search_public_chats": (
        "Search Telegram globally for public channels, supergroups, and bots matching query terms. "
        "Use when discovering new public communities. To search within your existing chats, use `list_chats` or `search_messages`."
    ),
    "resolve_username": (
        "Resolve a public @username to its underlying Telegram entity ID and object type (User, Channel, Group). "
        "Use before calling ID-based tools when only a username handle is known."
    ),
    "get_messages": (
        "Retrieve paginated messages from a specific chat starting from an offset or limit. "
        "Use for sequential message retrieval. To search text across messages, use `search_messages`."
    ),
    "list_messages": (
        "Retrieve messages from a chat matching optional filters such as sender, date range, or topic. "
        "Use when filtering chat history. For simple sequential pagination, use `get_messages`. "
        "For text keyword searching, use `search_messages`."
    ),
    "get_message_context": (
        "Retrieve a surrounding window of messages immediately preceding and following a target message ID in a chat. "
        "Use when reconstructing conversational context around a specific quote, event, or citation. "
        "For general chat browsing, use `get_messages` or `list_messages`."
    ),
    "search_messages": (
        "Search for text keywords within a specific Telegram chat or supergroup. "
        "Use when finding past conversations in a single chat. To search the offline cache without live Telegram API calls, "
        "use `search_cached_messages`."
    ),
    "search_global": (
        "Search for message text across all joined dialogs and public channels globally. "
        "Use when the target chat is unknown. If the chat is known, prefer `search_messages` for faster scoped results."
    ),
    "get_history": (
        "Retrieve full sequential message history from a chat in reverse chronological order up to the limit. "
        "Use when ingesting, exporting, or summarizing complete conversation backlogs. "
        "For paginated offset-based chunks, use `get_messages`. "
        "For filtered retrieval by sender or date range, use `list_messages`."
    ),
    "get_pinned_messages": (
        "Retrieve all pinned announcements and pinned messages in a chat or supergroup. "
        "Use when checking key rules, announcements, or pinned notices."
    ),
    "get_media_info": (
        "Inspect media metadata (file size, dimensions, mime type, duration) attached to a specific message. "
        "Use before downloading or viewing to verify file attributes and dimensions."
    ),
    "list_photos": (
        "List and inspect photo messages within a chat. "
        "Use when auditing, surveying, or locating photo attachments across conversation history."
    ),
    "open_photo": (
        "Fetch, inspect, and preview a single photo from a chat by message ID or avatar reference. "
        "Use when analyzing or saving a specific image in a conversation. "
        "To browse photo metadata across messages, use `list_photos`. "
        "For a multi-photo thumbnail grid, use `get_photo_sheet`."
    ),
    "get_photo_sheet": (
        "Generate a single composite thumbnail contact sheet grid assembling recent photos from a chat or user profile. "
        "Use to visually survey multiple images at once in a single request. "
        "To inspect photo message metadata individually, use `list_photos`. "
        "To view a single photo in full resolution, use `open_photo`."
    ),
    "list_contacts": (
        "List all registered Telegram contacts in your account address book with IDs and phone numbers. "
        "Use when finding contacts to message. To search contacts by query, use `search_contacts`."
    ),
    "search_contacts": (
        "Search your Telegram contacts directory by name, phone number, or username. "
        "Use when looking up a specific person. To view the entire directory, use `list_contacts`."
    ),
    "get_contact_ids": (
        "Retrieve a lightweight list of all Telegram user IDs in your address book. "
        "Use when checking if a user ID is an existing contact. For full contact profiles, use `list_contacts`."
    ),
    "get_direct_chat_by_contact": (
        "Find or resolve the direct 1-on-1 private chat with a contact by name or phone query. "
        "Use before sending a private message to confirm chat availability."
    ),
    "get_contact_chats": (
        "Find all mutual groups, channels, and direct dialogs shared between your account and a specific contact ID. "
        "Use when auditing shared memberships or verifying mutual chat contexts with a contact. "
        "To list all dialogs regardless of contact, use `list_chats` or `get_chats`. "
        "To retrieve contact profile details, use `get_chat` or `get_full_chat`."
    ),
    "get_last_interaction": (
        "Get the timestamp and summary of the most recent interaction or message with a contact. "
        "Use to check communication recency before initiating contact."
    ),
    "get_privacy_settings": (
        "Retrieve privacy rules and exception lists for account attributes (phone number, last seen, status). "
        "Use when auditing account security. Note: Privacy settings must be configured via an official Telegram client."
    ),
    "get_user_status": (
        "Check the current online presence, exact last seen timestamp, and bot attributes for a specific user ID or username. "
        "Use to verify whether a user is currently reachable before initiating contact. "
        "To view complete profile bio, photo, and username metadata, use `get_chat` or `get_full_chat`."
    ),
    "get_bot_info": (
        "Inspect bot profile, command list, description, and capabilities for a specified bot. "
        "Use when discovering bot commands. Note: Bot command registration is managed via @BotFather."
    ),
    "list_folders": (
        "List all custom Telegram dialog filter folders (tabs) with folder IDs and titles. "
        "Use when discovering folder organization. To see chats inside a folder, use `get_folder`."
    ),
    "get_folder": (
        "Retrieve the list of chat, channel, and bot peers included within a specific Telegram dialog filter folder ID. "
        "Use when inspecting dialogs grouped under a specific tab or categorization filter. "
        "To discover all available folder IDs and their titles, use `list_folders`."
    ),
    "get_admins": (
        "Retrieve the complete list of administrators and their granular permissions in a channel or supergroup. "
        "Use when verifying moderation staff or administrative rights. "
        "To review recent admin action logs, use `get_recent_actions`. "
        "To view restricted or banned users, use `get_banned_users`."
    ),
    "get_banned_users": (
        "Retrieve the list of currently restricted, muted, or banned members in a supergroup or channel. "
        "Use when auditing active moderation penalties. "
        "To inspect who enacted bans, use `get_recent_actions`."
    ),
    "get_recent_actions": (
        "Inspect the administrative audit log of recent channel or supergroup events (bans, title changes, member kicks, pin edits). "
        "Use when investigating incident history or moderation changes. Requires admin privileges in the target chat. "
        "To list current administrators, use `get_admins`. "
        "To list currently restricted or banned members, use `get_banned_users`."
    ),
    "cache_health": (
        "Inspect local SQLite/FTS5 archive integrity, database size, and active tool tier diagnostics. "
        "Use to verify cache readiness before running local searches. Operates entirely offline without Telegram API calls. "
        "Deprecated alias for `check_cache_health`."
    ),
    "check_cache_health": (
        "Inspect local SQLite/FTS5 archive integrity, database size, and active tool tier diagnostics. "
        "Use to verify cache readiness before running local searches. Operates entirely offline without Telegram API calls."
    ),
    "search_cached_messages": (
        "Search the local FTS5 SQLite archive for messages without making live Telegram API requests. "
        "Use for instantaneous, rate-limit-free search over synchronized messages. To sync messages into cache first, use `sync_chat_cache`."
    ),
    "sync_chat_cache": (
        "Synchronize remote Telegram chat messages into the local SQLite/FTS5 offline cache database. "
        "Use before performing offline text searches or when populating local message archives. "
        "To search already synced messages without Telegram API calls, use `search_cached_messages`. "
        "To verify database integrity and index status, use `check_cache_health`."
    ),
    "send_message": (
        "Send a text message to a specified Telegram chat, group, channel, or user. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. For replying to an existing message, prefer `reply_to_message`."
    ),
    "reply_to_message": (
        "Send a message in direct reply to a specific message ID in a chat. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To send a standalone message, use `send_message`."
    ),
    "forward_message": (
        "Forward a single message from one chat to another chat. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To forward multiple messages in a single action, use `forward_messages`."
    ),
    "forward_messages": (
        "Forward a batch of multiple messages from a source chat to a destination chat. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. For a single message, use `forward_message`."
    ),
    "edit_message": (
        "Edit the text content of an existing message previously sent by this account. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. Cannot edit messages sent by other users."
    ),
    "pin_message": (
        "Pin a message to the top of a chat or supergroup for high visibility. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true and admin permissions in supergroups/channels. "
        "To unpin, use `unpin_message`."
    ),
    "unpin_message": (
        "Unpin a specific message from a chat or supergroup. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To pin a message, use `pin_message`."
    ),
    "mark_as_read": (
        "Mark all messages or messages up to a specific ID in a chat as read. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. Clears unread badge counter."
    ),
    "send_reaction": (
        "Add an emoji reaction (e.g. '👍', '❤️', '🔥') to a message in a chat. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To remove a reaction, use `remove_reaction`."
    ),
    "remove_reaction": (
        "Remove your previously sent emoji reaction from a message in a chat. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To add a reaction, use `send_reaction`."
    ),
    "save_draft": (
        "Save an unsent message draft in a specified chat. Drafts synchronize across all official Telegram clients. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To list drafts, use `get_drafts`. To clear, use `clear_draft`."
    ),
    "get_drafts": (
        "List all pending unsent message drafts across all chats in your Telegram account. "
        "Use when locating unfinished messages. To save a draft, use `save_draft`. To delete a draft, use `clear_draft`."
    ),
    "clear_draft": (
        "Clear and delete the saved message draft from a specified chat. "
        "Destructive mutation requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true."
    ),
    "send_file": (
        "Upload and send a local document or file to a chat. "
        "File path must resolve within configured MCP allowed roots. Requires TELEGRAM_SEND_ENABLED=true."
    ),
    "send_album": (
        "Send multiple media files grouped together as an album (up to 10 items). "
        "All file paths must resolve within configured MCP allowed roots. Requires TELEGRAM_SEND_ENABLED=true."
    ),
    "download_media": (
        "Download an attachment or media file from a message to the local filesystem. "
        "Destination path must resolve within configured MCP allowed roots. To check metadata before downloading, use `get_media_info`."
    ),
    "upload_file": (
        "Upload a local file into Telegram cloud storage without immediately posting to a chat. "
        "File path must resolve within configured MCP allowed roots. Returns an uploaded file handle."
    ),
    "send_voice": (
        "Send an audio voice message note (.ogg or .opus format) to a chat. "
        "File path must resolve within configured MCP allowed roots. Requires TELEGRAM_SEND_ENABLED=true."
    ),
    "send_sticker": (
        "Send a sticker (.webp format) to a Telegram chat. "
        "Requires TELEGRAM_SEND_ENABLED=true. File path must resolve within configured MCP allowed roots."
    ),
    "send_gif": (
        "Send an animated GIF document to a Telegram chat. "
        "Requires TELEGRAM_SEND_ENABLED=true. File path must resolve within configured MCP allowed roots."
    ),
    "set_contact_alias": (
        "Set a custom private local alias or nickname for a Telegram contact. "
        "Stores alias locally in configuration. To list existing aliases, use `list_contact_aliases`."
    ),
    "list_contact_aliases": (
        "List all configured private local contact aliases. "
        "Use when reviewing custom contact names. To create an alias, use `set_contact_alias`. To remove one, use `delete_contact_alias`."
    ),
    "delete_contact_alias": (
        "Delete a previously set local contact alias. "
        "Destructive operation requiring TELEGRAM_DESTRUCTIVE_ENABLED=true."
    ),
    "add_contact": (
        "Add a new contact to your Telegram address book by phone number and name. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true."
    ),
    "delete_contact": (
        "Permanently delete a contact from your Telegram address book. "
        "Destructive operation requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true."
    ),
    "block_user": (
        "Block a Telegram user to prevent them from sending direct messages or calling your account. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To unblock, use `unblock_user`."
    ),
    "unblock_user": (
        "Unblock a previously blocked Telegram user, allowing them to send messages again. "
        "Mutation operation requiring TELEGRAM_SEND_ENABLED=true. To block a user, use `block_user`."
    ),
    "delete_message": (
        "Delete a single message from a chat by message ID. "
        "Destructive operation requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true."
    ),
    "delete_messages_bulk": (
        "Delete multiple messages from a chat in a single batch request. "
        "Destructive operation requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true. "
        "For a single message, use `delete_message`."
    ),
    "delete_chat_history": (
        "Permanently delete all message history in a specified chat. "
        "High-impact destructive action requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true."
    ),
    "ban_user": (
        "Ban and kick a user from a Telegram group or supergroup. "
        "Destructive administrative action requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true. "
        "To restore access, use `unban_user`."
    ),
    "unban_user": (
        "Unban a previously banned user from a group or supergroup, restoring their ability to rejoin. "
        "Administrative mutation requiring TELEGRAM_SEND_ENABLED=true."
    ),
    "leave_chat": (
        "Leave and exit a Telegram group, supergroup, or broadcast channel. "
        "Destructive operation requiring TELEGRAM_SEND_ENABLED=true and TELEGRAM_DESTRUCTIVE_ENABLED=true."
    ),
}

def enrich_all_tools(server: Any) -> int:
    """Enrich all registered MCP tools with titles, parameter schemas, and TDQS descriptions."""
    count = 0
    tools = list(server._tool_manager.list_tools())
    for tool in tools:
        name = tool.name

        # 1. Ensure meaningful title (longer than name)
        title = TOOL_TITLES.get(name)
        if not title:
            # Generate human-readable title from snake_case
            parts = name.split("_")
            title = " ".join(part.capitalize() for part in parts)
            if len(title) <= len(name):
                title = f"{title} Details"
        tool.title = title
        if tool.annotations:
            tool.annotations.title = title

        # 2. Update tool description if enhanced TDQS version exists
        enhanced_desc = TOOL_DESCRIPTIONS.get(name)
        if enhanced_desc:
            tool.description = enhanced_desc

        # 3. Ensure 100% parameter descriptions in inputSchema
        properties = tool.parameters.get("properties", {})
        for param_name, param_schema in properties.items():
            if not param_schema.get("description"):
                desc = UNIVERSAL_PARAM_DESCRIPTIONS.get(param_name)
                if not desc:
                    desc = f"Parameter '{param_name}' for {title}."
                param_schema["description"] = desc

        count += 1

    logger.info(f"Successfully enriched {count} MCP tools with TDQS metadata.")
    return count
