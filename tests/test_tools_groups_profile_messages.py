"""Unit tests covering high-risk untested tools across groups, profile, chats, and messages."""

from __future__ import annotations

import datetime
import json
from types import SimpleNamespace

import pytest
from telethon.tl import functions, types

from telegram_mcp.tools import chats, groups, messages, profile
from tests.helpers.mock_telethon import (
    MockTelethonClient,
    make_channel,
    make_user,
    patch_tool_module,
)


@pytest.mark.asyncio
async def test_group_admin_and_moderation_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = make_channel()
    event = SimpleNamespace(to_dict=lambda: {"id": 1, "action": "title_changed"})
    client = MockTelethonClient(
        handlers={
            "GetAdminLogRequest": lambda _req: SimpleNamespace(
                events=[event], users=[make_user()], chats=[channel]
            ),
        }
    )
    patch_tool_module(monkeypatch, groups, client, entity=channel)

    assert "An error occurred" not in await groups.create_group(title="Team", user_ids=[111])
    assert "An error occurred" not in await groups.create_channel(title="Updates")
    assert "An error occurred" not in await groups.edit_chat_title(
        chat_id=-1000000000222, title="Renamed"
    )
    assert "An error occurred" not in await groups.promote_admin(
        group_id=-1000000000222, user_id=111
    )
    assert "An error occurred" not in await groups.ban_user(chat_id=-1000000000222, user_id=111)
    assert "An error occurred" not in await groups.toggle_slow_mode(
        chat_id=-1000000000222, seconds=30
    )

    actions = await groups.get_recent_actions(chat_id=-1000000000222)
    assert json.loads(actions)[0]["action"] == "title_changed"
    assert any(isinstance(r, functions.channels.ToggleSlowModeRequest) for r in client.requests)


@pytest.mark.asyncio
async def test_profile_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    bot_user = make_user(user_id=333, username="mybot", bot=True)
    photo = types.Photo(
        id=55,
        access_hash=1,
        file_reference=b"",
        date=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        sizes=[],
        dc_id=1,
    )
    client = MockTelethonClient(
        handlers={
            "GetUserPhotosRequest": lambda _req: SimpleNamespace(photos=[photo]),
            "GetFullUserRequest": lambda _req: SimpleNamespace(
                full_user=SimpleNamespace(
                    about="bio",
                    common_chats_count=1,
                    bot_info=SimpleNamespace(description="helper", commands=[]),
                    pinned_msg_id=None,
                    blocked=False,
                    phone_calls_available=True,
                    video_calls_available=True,
                    can_pin_message=True,
                    has_scheduled=False,
                    voice_messages_forbidden=False,
                ),
                users=[bot_user],
                chats=[],
            ),
        }
    )
    patch_tool_module(monkeypatch, profile, client, entity=bot_user)

    assert "An error occurred" not in await profile.update_profile(first_name="Mina")
    assert "An error occurred" not in await profile.delete_profile_photo()
    assert json.loads(await profile.get_user_photos(user_id=333)) == [55]
    assert "UserStatusOnline" in await profile.get_user_status(user_id=333)
    full_user = json.loads(await profile.get_full_user(username="mybot"))
    assert full_user["username"] == "mybot"
    bot_info = json.loads(await profile.get_bot_info(bot_username="mybot"))
    assert bot_info["bot_info"]["is_bot"] is True


@pytest.mark.asyncio
async def test_chat_and_message_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    read_ts = datetime.datetime(2026, 11, 24, 8, 0, tzinfo=datetime.timezone.utc)
    client = MockTelethonClient(
        handlers={
            "GetMessageReadParticipantsRequest": lambda _req: [
                types.ReadParticipantDate(user_id=111, date=read_ts)
            ],
            "ExportMessageLinkRequest": lambda _req: SimpleNamespace(
                link="https://t.me/testgroup/10"
            ),
        }
    )
    patch_tool_module(monkeypatch, chats, client)
    patch_tool_module(monkeypatch, messages, client)

    read_by = json.loads(await chats.get_message_read_by(chat_id=-1000000000222, message_id=10))
    assert read_by["read_by"][0]["user_id"] == 111
    assert "https://t.me/testgroup/10" in await chats.get_message_link(
        chat_id=-1000000000222, message_id=10
    )
    assert "muted" in (await chats.mute_chat(chat_id=-1000000000222)).lower()
    assert "archived" in (await chats.archive_chat(chat_id=-1000000000222)).lower()

    sched = await messages.send_scheduled_message(
        chat_id=-1000000000222, message="later", schedule_date="2026-12-01T10:00:00Z"
    )
    assert "Scheduled message" in sched
    assert "An error occurred" not in await messages.delete_scheduled_message(
        chat_id=-1000000000222, message_ids=[10]
    )
    assert "An error occurred" not in await messages.create_poll(
        chat_id=-1000000000222, question="Ship it?", options=["Yes", "Now"]
    )
    assert "An error occurred" not in await messages.send_reaction(
        chat_id=-1000000000222, message_id=10, emoji="👍"
    )
    assert "An error occurred" not in await messages.save_draft(
        chat_id=-1000000000222, message="wip"
    )
    assert "An error occurred" not in await messages.clear_draft(chat_id=-1000000000222)
