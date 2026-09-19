"""Unit tests for custom TLRequests and models module coverage."""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telethon.tl.tlobject import TLObject

from telegram_mcp import models
from telegram_mcp.core.tl_custom import CreateForumTopicRequest, GetForumTopicsRequest
from telegram_mcp.models import common
from telegram_mcp.models.messages import _inline_button_texts, _link_urls


class DummyTLObject(TLObject):
    CONSTRUCTOR_ID = 0x12345678
    SUBCLASS_OF_ID = 0x0

    def to_dict(self):
        return {"_": "DummyTLObject"}

    def _bytes(self):
        return b"\x78\x56\x34\x12"


@pytest.mark.asyncio
async def test_get_forum_topics_request_lifecycle():
    dummy_channel = DummyTLObject()
    req = GetForumTopicsRequest(
        channel=dummy_channel,
        offset_date=100,
        offset_id=200,
        offset_topic=300,
        limit=50,
        q="test",
    )

    # to_dict
    d = req.to_dict()
    assert d["_"] == "GetForumTopicsRequest"
    assert d["channel"] == {"_": "DummyTLObject"}
    assert d["q"] == "test"
    assert d["limit"] == 50

    # _bytes with q string
    raw_bytes = req._bytes()
    assert isinstance(raw_bytes, bytes)
    assert len(raw_bytes) > 0

    # _bytes with q=None
    req_no_q = GetForumTopicsRequest(
        channel=dummy_channel,
        offset_date=0,
        offset_id=0,
        offset_topic=0,
        limit=20,
        q=None,
    )
    raw_bytes_no_q = req_no_q._bytes()
    assert isinstance(raw_bytes_no_q, bytes)

    # resolve
    mock_client = MagicMock()
    mock_client.get_input_entity = AsyncMock(return_value="raw_entity")
    mock_utils = MagicMock()
    mock_utils.get_input_channel.return_value = "input_channel"

    await req.resolve(mock_client, mock_utils)
    mock_client.get_input_entity.assert_awaited_once_with(dummy_channel)
    mock_utils.get_input_channel.assert_called_once_with("raw_entity")
    assert req.channel == "input_channel"

    # from_reader with flag & 1
    reader = MagicMock()
    reader.read_int.side_effect = [1, 100, 200, 300, 50]  # flags, date, id, topic, limit
    reader.tgread_object.return_value = "channel_from_reader"
    reader.tgread_string.return_value = "query_str"

    parsed = GetForumTopicsRequest.from_reader(reader)
    assert parsed.channel == "channel_from_reader"
    assert parsed.q == "query_str"
    assert parsed.limit == 50

    # from_reader without flag & 1
    reader2 = MagicMock()
    reader2.read_int.side_effect = [0, 0, 0, 0, 10]
    reader2.tgread_object.return_value = "ch"
    parsed2 = GetForumTopicsRequest.from_reader(reader2)
    assert parsed2.q is None


@pytest.mark.asyncio
async def test_create_forum_topic_request_lifecycle():
    dummy_peer = DummyTLObject()
    dummy_send_as = DummyTLObject()
    req = CreateForumTopicRequest(
        peer=dummy_peer,
        title="General",
        random_id=987654321,
        icon_color=0x112233,
        icon_emoji_id=555444333,
        send_as=dummy_send_as,
    )

    # to_dict
    d = req.to_dict()
    assert d["_"] == "CreateForumTopicRequest"
    assert d["peer"] == {"_": "DummyTLObject"}
    assert d["send_as"] == {"_": "DummyTLObject"}
    assert d["title"] == "General"
    assert d["icon_color"] == 0x112233

    # _bytes with all options
    raw_bytes = req._bytes()
    assert isinstance(raw_bytes, bytes)

    # _bytes with minimal options
    req_minimal = CreateForumTopicRequest(
        peer=dummy_peer,
        title="Minimal",
        random_id=123,
    )
    raw_bytes_min = req_minimal._bytes()
    assert isinstance(raw_bytes_min, bytes)

    # resolve
    mock_client = MagicMock()
    mock_client.get_input_entity = AsyncMock(side_effect=["entity_peer", "entity_send_as"])
    mock_utils = MagicMock()
    mock_utils.get_input_peer.side_effect = ["input_peer", "input_send_as"]

    await req.resolve(mock_client, mock_utils)
    assert req.peer == "input_peer"
    assert req.send_as == "input_send_as"

    # from_reader with all flags (1 | 4 | 8 = 13)
    reader = MagicMock()
    reader.read_int.side_effect = [13, 0x112233]  # flags, icon_color
    reader.tgread_object.side_effect = ["peer_obj", "send_as_obj"]
    reader.tgread_string.return_value = "Topic"
    reader.read_long.side_effect = [555444333, 987654321]  # icon_emoji_id, random_id

    parsed = CreateForumTopicRequest.from_reader(reader)
    assert parsed.peer == "peer_obj"
    assert parsed.title == "Topic"
    assert parsed.icon_color == 0x112233
    assert parsed.icon_emoji_id == 555444333
    assert parsed.random_id == 987654321
    assert parsed.send_as == "send_as_obj"

    # from_reader with no optional flags
    reader2 = MagicMock()
    reader2.read_int.side_effect = [0]
    reader2.tgread_object.return_value = "peer2"
    reader2.tgread_string.return_value = "Simple"
    reader2.read_long.return_value = 101

    parsed2 = CreateForumTopicRequest.from_reader(reader2)
    assert parsed2.icon_color is None
    assert parsed2.icon_emoji_id is None
    assert parsed2.send_as is None


def test_models_reexports_and_coverage():
    assert hasattr(models, "ChatRecord")
    assert hasattr(models, "MediaRecord")
    assert hasattr(models, "MessageRecord")
    assert hasattr(models, "get_media_label")
    assert hasattr(models, "format_message_line")
    assert hasattr(models, "message_to_dict")

    # test isoformat in common
    now = datetime.datetime.now(datetime.UTC)
    assert common.isoformat(now) == now.isoformat()
    assert common.isoformat(None) is None


def test_models_media_labels():
    class DummyMsg:
        pass

    msg = DummyMsg()
    assert models.get_media_label(msg) == ""

    # web_preview takes precedence
    msg.web_preview = True
    assert models.get_media_label(msg) == ""
    msg.web_preview = None

    # sticker
    msg.sticker = SimpleNamespace(attributes=[SimpleNamespace(alt="🔥")])
    assert models.get_media_label(msg) == "sticker 🔥"
    msg.sticker = SimpleNamespace(attributes=[])
    assert models.get_media_label(msg) == "sticker"
    msg.sticker = None

    # photo, voice, video_note, video, audio, gif
    for attr, label in [
        ("photo", "photo"),
        ("voice", "voice"),
        ("video_note", "video_note"),
        ("video", "video"),
        ("audio", "audio"),
        ("gif", "gif"),
        ("contact", "contact"),
        ("geo", "geo"),
        ("poll", "poll"),
        ("media", "media"),
    ]:
        setattr(msg, attr, True)
        assert models.get_media_label(msg) == label
        setattr(msg, attr, None)

    # document
    msg.document = True
    msg.file = SimpleNamespace(name="archive.tar.gz")
    assert models.get_media_label(msg) == "document: archive.tar.gz"
    msg.file = None
    assert models.get_media_label(msg) == "document"
    msg.document = None

    # exception handling
    class BrokenMsg:
        @property
        def web_preview(self):
            raise RuntimeError("broken")

    assert models.get_media_label(BrokenMsg()) == ""


def test_inline_buttons_and_links():
    msg = SimpleNamespace(
        buttons=[
            [SimpleNamespace(text="Btn 1"), SimpleNamespace(text="Btn 2")],
            [SimpleNamespace(text="")],
        ],
        entities=[SimpleNamespace(url="https://example.com"), SimpleNamespace(url="")],
    )
    assert _inline_button_texts(msg) == ["Btn 1", "Btn 2"]
    assert _link_urls(msg) == ["https://example.com"]


def test_message_to_dict_and_format_all_branches():
    class DummyAction:
        pass

    msg = SimpleNamespace(
        id=555,
        sender=SimpleNamespace(title="Channel A"),
        date=datetime.datetime.now(datetime.UTC),
        sender_id=123,
        out=True,
        message="Hello\nWorld",
        media=None,
        grouped_id=999,
        reply_to=SimpleNamespace(reply_to_msg_id=444, quote_text="fragment", quote_offset=5),
        fwd_from=SimpleNamespace(date="2026-01-01", from_name="Ghost", channel_post=88),
        forward=SimpleNamespace(
            chat=SimpleNamespace(title="Fwd Chat", username="fwd_chat"),
            chat_id=-100123456789,
            sender=SimpleNamespace(first_name="Alice", last_name="Smith"),
        ),
        via_bot_id=777,
        edit_date="2026-01-02",
        pinned=True,
        views=150,
        forwards=10,
        reactions=SimpleNamespace(results=[SimpleNamespace(count=3)]),
        replies=SimpleNamespace(replies=5),
        buttons=[[SimpleNamespace(text="Click")]],
        entities=[SimpleNamespace(url="https://example.com/link")],
        action=DummyAction(),
        ttl_period=60,
    )

    d = models.message_to_dict(msg)
    assert d["id"] == 555
    assert d["sender_id"] == 123
    assert d["out"] is True
    assert d["grouped_id"] == 999
    assert d["via_bot_id"] == 777
    assert d["edited"] == "2026-01-02"
    assert d["pinned"] is True
    assert d["comments"] == 5
    assert d["action"] == "DummyAction"
    assert d["ttl_period"] == 60
    assert d["buttons"] == ["Click"]
    assert d["link_urls"] == ["https://example.com/link"]
    assert d["reply_quote"]["offset"] == 5

    line = models.format_message_line(msg)
    assert "reply to 444" in line
    assert "quoting" in line
    assert "album:999" in line
    assert "forwarded" in line
    assert "edited" in line
    assert "via_bot" in line
    assert "pinned" in line
    assert "buttons:1" in line
    assert "service:DummyAction" in line
    assert "Hello\\nWorld" in line

    # private link branch without username
    msg_private = SimpleNamespace(
        id=556,
        sender=None,
        date=datetime.datetime.now(datetime.UTC),
        fwd_from=SimpleNamespace(channel_post=99, post_author="Editor"),
        forward=SimpleNamespace(chat_id=-100123456789, chat=None, sender=None),
        reply_to=None,
    )
    d_priv = models.message_to_dict(msg_private)
    assert "post_link" in d_priv["forwarded"]
    assert d_priv["forwarded"]["post_author"] == "Editor"
