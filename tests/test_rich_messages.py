"""Tests for rich message sending (Telegram Premium gated)."""

import json
from types import SimpleNamespace

import pytest
import telethon

from telegram_mcp import runtime
from telegram_mcp.tools import messages


class _FakeClient:
    def __init__(self, premium=True, rpc_error=None):
        self._premium = premium
        self._rpc_error = rpc_error
        self.requests = []

    async def get_me(self):
        return SimpleNamespace(premium=self._premium)

    async def __call__(self, request):
        self.requests.append(request)
        if self._rpc_error is not None:
            raise self._rpc_error
        return SimpleNamespace()


def test_make_rich_input_routes_by_mode():
    md = runtime.make_rich_input("rich_markdown", "| a | b |")
    assert isinstance(md, runtime.types.InputRichMessageMarkdown)
    assert md.markdown == "| a | b |"

    html = runtime.make_rich_input("rich_html", "<table></table>")
    assert isinstance(html, runtime.types.InputRichMessageHTML)
    assert html.html == "<table></table>"


@pytest.mark.asyncio
async def test_send_rich_without_premium_sends_nothing():
    cl = _FakeClient(premium=False)
    result = json.loads(await messages._send_rich(cl, "peer", "| a |", "rich"))

    assert result["sent"] is False
    assert result["reason"] == "telegram_premium_required"
    assert cl.requests == []  # nothing hit the network


@pytest.mark.asyncio
async def test_send_rich_with_premium_sends_rich_request():
    cl = _FakeClient(premium=True)
    result = json.loads(await messages._send_rich(cl, "peer", "| a |", "rich", reply_to=5))

    assert result == {"sent": True, "rich": True}
    (req,) = cl.requests
    assert isinstance(req.rich_message, runtime.types.InputRichMessageMarkdown)
    assert req.reply_to.reply_to_msg_id == 5


@pytest.mark.asyncio
async def test_send_rich_premium_lapsed_midflight():
    err = telethon.errors.RPCError(None, "PREMIUM_ACCOUNT_REQUIRED", 403)
    cl = _FakeClient(premium=True, rpc_error=err)
    result = json.loads(await messages._send_rich(cl, "peer", "x", "rich"))

    assert result["sent"] is False
    assert result["reason"] == "telegram_premium_required"


@pytest.mark.asyncio
async def test_send_rich_other_rpc_error_propagates():
    err = telethon.errors.RPCError(None, "FLOOD_WAIT", 420)
    cl = _FakeClient(premium=True, rpc_error=err)
    with pytest.raises(telethon.errors.RPCError):
        await messages._send_rich(cl, "peer", "x", "rich")


class _EditRecorder:
    """Records how edit_message forwards parse_mode to Telethon."""

    def __init__(self):
        self.calls = []

    async def edit_message(self, entity, message_id, text, **kwargs):
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_edit_message_omits_parse_mode_when_not_given(monkeypatch):
    # Telethon treats an explicit None as "disable parsing" while an omitted
    # argument uses its default parser, so callers who never passed parse_mode
    # must keep getting formatted edits.
    cl = _EditRecorder()
    monkeypatch.setattr(messages, "get_client", lambda account=None: cl)

    async def fake_resolve(chat_id, client=None):
        return "entity"

    monkeypatch.setattr(messages, "resolve_entity", fake_resolve)

    await messages.edit_message(chat_id=1, message_id=2, new_text="**bold**")
    assert cl.calls == [{}]

    await messages.edit_message(chat_id=1, message_id=2, new_text="x", parse_mode="html")
    assert cl.calls[-1] == {"parse_mode": "html"}


@pytest.mark.asyncio
async def test_edit_rich_both_premium_cases():
    ok = _FakeClient(premium=True)
    result = json.loads(await messages._edit_rich(ok, "peer", 7, "new", "rich_html"))
    assert result["sent"] is True and result["edited_message_id"] == 7
    (req,) = ok.requests
    assert isinstance(req.rich_message, runtime.types.InputRichMessageHTML)

    no = _FakeClient(premium=False)
    result = json.loads(await messages._edit_rich(no, "peer", 7, "new", "rich"))
    assert result["reason"] == "telegram_premium_required"
    assert no.requests == []


@pytest.mark.asyncio
async def test_get_message_context_batches_replies(monkeypatch):
    """Verify get_message_context batches replied message lookups into a single RPC."""
    class _ContextClient:
        def __init__(self):
            self.id_calls = []

        async def get_messages(self, entity, **kwargs):
            if "ids" in kwargs:
                ids = kwargs["ids"]
                self.id_calls.append(ids)
                if isinstance(ids, list):
                    return [
                        SimpleNamespace(
                            id=i,
                            date="2026-01-01",
                            message=f"reply to {i}",
                            sender=SimpleNamespace(first_name="User", last_name=str(i), title=None, username=None),
                            sender_id=i,
                            reply_to=None,
                        )
                        for i in ids
                    ]
                elif ids == 50:
                    return SimpleNamespace(
                        id=50,
                        date="2026-01-01",
                        message="central",
                        sender=SimpleNamespace(first_name="Target", last_name="", title=None, username=None),
                        sender_id=99,
                        reply_to=None,
                    )
                return None

            if kwargs.get("max_id") == 50:
                return [
                    SimpleNamespace(
                        id=48,
                        date="2026-01-01",
                        message="msg 48",
                        sender=SimpleNamespace(first_name="A", last_name="", title=None, username=None),
                        sender_id=1,
                        reply_to=SimpleNamespace(reply_to_msg_id=101),
                    ),
                    SimpleNamespace(
                        id=49,
                        date="2026-01-01",
                        message="msg 49",
                        sender=SimpleNamespace(first_name="B", last_name="", title=None, username=None),
                        sender_id=2,
                        reply_to=SimpleNamespace(reply_to_msg_id=102),
                    ),
                ]
            return []

    cl = _ContextClient()
    monkeypatch.setattr(messages, "get_client", lambda account=None: cl)

    async def fake_resolve(chat_id, client=None):
        return "entity"

    monkeypatch.setattr(messages, "resolve_entity", fake_resolve)

    result = await messages.get_message_context(chat_id=123, message_id=50, context_size=5)
    parsed = json.loads(result)
    records = parsed["results"]
    assert len(records) == 3
    # Verify IDs was called with batch list [101, 102], not individual scalar calls
    assert [101, 102] in cl.id_calls
    assert 101 not in cl.id_calls
    assert 102 not in cl.id_calls
    # Verify replied messages are mapped correctly
    msg48 = next(m for m in records if m["id"] == 48)
    assert msg48["replied_message"]["text"] == "reply to 101"
    msg49 = next(m for m in records if m["id"] == 49)
    assert msg49["replied_message"]["text"] == "reply to 102"

