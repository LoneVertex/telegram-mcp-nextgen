"""Regression tests for contact MCP tools."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telethon.tl import functions, types

from telegram_mcp.tools import contacts


class _RecordingClient:
    def __init__(self, imported_count: int = 1) -> None:
        self.requests: list[object] = []
        self._imported_count = imported_count

    async def __call__(self, request: object) -> SimpleNamespace:
        self.requests.append(request)
        return SimpleNamespace(imported=[object()] * self._imported_count)


@pytest.mark.asyncio
async def test_import_contacts_constructs_tl_input_phone_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RecordingClient(imported_count=1)
    monkeypatch.setattr(contacts, "get_client", lambda account=None: client)
    monkeypatch.setattr(contacts, "ensure_connected", AsyncMock(return_value=None))

    result = await contacts.import_contacts(
        contacts=[{"phone": "+201001234567", "first_name": "Mina"}]
    )

    assert result == "Imported 1 contacts."
    assert len(client.requests) == 1
    request = client.requests[0]
    assert isinstance(request, functions.contacts.ImportContactsRequest)
    assert len(request.contacts) == 1
    assert isinstance(request.contacts[0], types.InputPhoneContact)
    assert request.contacts[0].phone == "+201001234567"
    assert request.contacts[0].first_name == "Mina"
    assert request.contacts[0].last_name == ""


@pytest.mark.asyncio
async def test_import_contacts_handles_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _RecordingClient(imported_count=0)
    monkeypatch.setattr(contacts, "get_client", lambda account=None: client)
    monkeypatch.setattr(contacts, "ensure_connected", AsyncMock(return_value=None))

    result = await contacts.import_contacts(contacts=[])

    assert result == "Imported 0 contacts."
    assert len(client.requests) == 1
    request = client.requests[0]
    assert isinstance(request, functions.contacts.ImportContactsRequest)
    assert request.contacts == []
