"""Automated tests for Glama Server Coherence, TDQS, and lifecycle completeness."""

import re

import pytest

from telegram_mcp.config import Settings
from telegram_mcp.core.registry import (
    CORE_TOOL_NAMES,
    ESSENTIAL_TOOL_NAMES,
    STANDARD_ADDITIONS,
    allowed_tool_names,
)
from telegram_mcp.core.schema_enricher import TOOL_DESCRIPTIONS, TOOL_TITLES

VERB_PREFIXES = (
    "get_",
    "list_",
    "search_",
    "resolve_",
    "send_",
    "reply_",
    "edit_",
    "delete_",
    "pin_",
    "unpin_",
    "mark_",
    "download_",
    "check_",
    "sync_",
    "upload_",
    "clear_",
    "save_",
    "forward_",
    "add_",
    "remove_",
    "set_",
    "block_",
    "unblock_",
    "ban_",
    "unban_",
    "leave_",
    "open_",
    "press_",
    "wait_",
    "incoming_",
    "archive_",
    "unarchive_",
    "create_",
    "subscribe_",
    "toggle_",
    "update_",
)

# Non-tool backtick identifiers allowed in docstrings
IGNORED_BACKTICKS = frozenset(
    {
        "TELEGRAM_SEND_ENABLED=true",
        "TELEGRAM_DESTRUCTIVE_ENABLED=true",
        "TELEGRAM_DOWNLOAD_ROOT",
        "TELEGRAM_UPLOAD_ROOT",
        "TELEGRAM_STORAGE_ROOT",
        "TELEGRAM_BASE_DIR",
        "TELEGRAM_SESSION_NAME",
        ".ogg",
        ".opus",
        ".webp",
    }
)


def test_essential_tier_count():
    """Glama imposes a tool count penalty for >25 tools on default tier."""
    assert len(ESSENTIAL_TOOL_NAMES) <= 25
    assert len(ESSENTIAL_TOOL_NAMES) == 22


def test_default_config_tier():
    """Default tier must be essential for optimal context efficiency and Glama score."""
    settings = Settings()
    assert settings.tier == "essential"
    assert settings.send_enabled is False
    assert settings.destructive_enabled is False


def test_essential_naming_consistency_verb_noun():
    """All essential tools must adhere 100% to verb_noun naming convention."""
    for tool_name in ESSENTIAL_TOOL_NAMES:
        assert any(tool_name.startswith(p) for p in VERB_PREFIXES), (
            f"Tool '{tool_name}' in essential tier does not start with a recognized verb prefix."
        )


def test_check_cache_health_verb_noun():
    """check_cache_health must strictly follow verb_noun (check_ prefix)."""
    assert "check_cache_health" in ESSENTIAL_TOOL_NAMES
    assert "check_cache_health" in CORE_TOOL_NAMES
    assert "check_cache_health".startswith("check_")


def test_zero_dead_end_cross_references_essential():
    """All tools in essential tier must have zero dead-end references to tools outside essential."""
    dangling: list[tuple[str, str]] = []
    for tool_name in ESSENTIAL_TOOL_NAMES:
        desc = TOOL_DESCRIPTIONS.get(tool_name, "")
        refs = re.findall(r"`([a-zA-Z0-9_=\.\-]+)`", desc)
        for ref in refs:
            if (
                ref not in ESSENTIAL_TOOL_NAMES
                and ref not in IGNORED_BACKTICKS
                and not ref.startswith("TELEGRAM_")
            ):
                dangling.append((tool_name, ref))
    assert not dangling, f"Essential tier contains dead-end references: {dangling}"


def test_zero_dead_end_cross_references_core():
    """All tools in core tier must have zero dead-end references to tools outside core."""
    dangling: list[tuple[str, str]] = []
    for tool_name in CORE_TOOL_NAMES:
        desc = TOOL_DESCRIPTIONS.get(tool_name, "")
        refs = re.findall(r"`([a-zA-Z0-9_=\.\-]+)`", desc)
        for ref in refs:
            if (
                ref not in CORE_TOOL_NAMES
                and ref not in IGNORED_BACKTICKS
                and not ref.startswith("TELEGRAM_")
            ):
                dangling.append((tool_name, ref))
    assert not dangling, f"Core tier contains dead-end references: {dangling}"


def test_zero_dead_end_cross_references_standard():
    """All tools in standard tier must have zero dead-end references to tools outside standard."""
    standard_tools = CORE_TOOL_NAMES | STANDARD_ADDITIONS
    dangling: list[tuple[str, str]] = []
    for tool_name in standard_tools:
        desc = TOOL_DESCRIPTIONS.get(tool_name, "")
        refs = re.findall(r"`([a-zA-Z0-9_=\.\-]+)`", desc)
        for ref in refs:
            if (
                ref not in standard_tools
                and ref not in IGNORED_BACKTICKS
                and not ref.startswith("TELEGRAM_")
            ):
                dangling.append((tool_name, ref))
    assert not dangling, f"Standard tier contains dead-end references: {dangling}"


def test_zero_fictional_tool_references_overall():
    """Every tool referenced in any TOOL_DESCRIPTIONS must exist in registry or TOOL_TITLES."""
    all_known_tools = set(TOOL_TITLES.keys()) | set(TOOL_DESCRIPTIONS.keys())
    dangling: list[tuple[str, str]] = []
    for tool_name, desc in TOOL_DESCRIPTIONS.items():
        refs = re.findall(r"`([a-zA-Z0-9_=\.\-]+)`", desc)
        for ref in refs:
            if (
                ref not in all_known_tools
                and ref not in IGNORED_BACKTICKS
                and not ref.startswith("TELEGRAM_")
            ):
                dangling.append((tool_name, ref))
    assert not dangling, f"Found fictional tool references in TOOL_DESCRIPTIONS: {dangling}"


def test_lifecycle_completeness():
    """Essential tier must have complete CRUD capabilities for messages and media."""
    # Read & Search
    assert "get_messages" in ESSENTIAL_TOOL_NAMES
    assert "search_messages" in ESSENTIAL_TOOL_NAMES
    assert "list_chats" in ESSENTIAL_TOOL_NAMES
    assert "get_chat" in ESSENTIAL_TOOL_NAMES
    assert "search_public_chats" in ESSENTIAL_TOOL_NAMES
    assert "resolve_username" in ESSENTIAL_TOOL_NAMES
    assert "get_me" in ESSENTIAL_TOOL_NAMES

    # Write / Mutation
    assert "send_message" in ESSENTIAL_TOOL_NAMES
    assert "reply_to_message" in ESSENTIAL_TOOL_NAMES
    assert "edit_message" in ESSENTIAL_TOOL_NAMES
    assert "delete_message" in ESSENTIAL_TOOL_NAMES
    assert "pin_message" in ESSENTIAL_TOOL_NAMES
    assert "unpin_message" in ESSENTIAL_TOOL_NAMES
    assert "mark_as_read" in ESSENTIAL_TOOL_NAMES

    # Media
    assert "send_file" in ESSENTIAL_TOOL_NAMES
    assert "download_media" in ESSENTIAL_TOOL_NAMES
    assert "get_media_info" in ESSENTIAL_TOOL_NAMES

    # Contacts
    assert "list_contacts" in ESSENTIAL_TOOL_NAMES
    assert "search_contacts" in ESSENTIAL_TOOL_NAMES

    # Cache
    assert "check_cache_health" in ESSENTIAL_TOOL_NAMES
    assert "search_cached_messages" in ESSENTIAL_TOOL_NAMES
    assert "sync_chat_cache" in ESSENTIAL_TOOL_NAMES


def test_tier_resolution():
    """Check allowed_tool_names returns correct sets for each tier."""
    assert allowed_tool_names("essential") == ESSENTIAL_TOOL_NAMES
    assert allowed_tool_names("core") == CORE_TOOL_NAMES
    assert allowed_tool_names("standard") == (CORE_TOOL_NAMES | STANDARD_ADDITIONS)
    assert allowed_tool_names("full") is None

    with pytest.raises(ValueError, match="TELEGRAM_MCP_TIER must be one of"):
        allowed_tool_names("invalid_tier")


@pytest.mark.asyncio
async def test_cache_health_alias_compatibility():
    """Both check_cache_health and cache_health must execute and return identical structure."""
    from telegram_mcp.tools.cache import cache_health, check_cache_health

    res1 = await check_cache_health()
    res2 = await cache_health()
    assert isinstance(res1, dict)
    assert isinstance(res2, dict)
    assert "status" in res1
    assert "tier" in res1
    assert "database" in res1
    assert res1.keys() == res2.keys()


def test_destructive_tool_names_matches_annotated_destructive_hints():
    """Security gating in _DESTRUCTIVE_TOOL_NAMES must strictly match tools declaring destructiveHint=True."""
    from telegram_mcp.runtime import _DESTRUCTIVE_TOOL_NAMES, mcp

    annotated_destructive = {
        tool.name
        for tool in mcp._tool_manager.list_tools()
        if getattr(getattr(tool, "annotations", None), "destructiveHint", False)
    }
    assert (
        annotated_destructive == _DESTRUCTIVE_TOOL_NAMES
    ), f"Mismatch between _DESTRUCTIVE_TOOL_NAMES and destructiveHint=True: diff={_DESTRUCTIVE_TOOL_NAMES ^ annotated_destructive}"

