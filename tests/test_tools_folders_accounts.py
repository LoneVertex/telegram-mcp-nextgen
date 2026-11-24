"""Unit tests for untested folder and account MCP tools."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from telethon.tl import functions, types

from telegram_mcp.tools import accounts, folders
from tests.helpers.mock_telethon import MockTelethonClient, patch_tool_module


def _dialog_filter(folder_id: int = 2, title: str = "Work") -> types.DialogFilter:
    return types.DialogFilter(
        id=folder_id,
        title=types.TextWithEntities(text=title, entities=[]),
        pinned_peers=[],
        include_peers=[types.InputPeerChannel(channel_id=222, access_hash=2)],
        exclude_peers=[],
    )


@pytest.mark.asyncio
async def test_list_accounts_returns_account_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        accounts,
        "clients",
        {"default": MockTelethonClient(), "work": MockTelethonClient()},
    )
    result = await accounts.list_accounts()
    assert "default: Alice Smith" in result
    assert "work: Alice Smith" in result


@pytest.mark.asyncio
async def test_folder_crud_and_reorder(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = _dialog_filter(2, "Work")
    client = MockTelethonClient(
        handlers={
            "GetDialogFiltersRequest": lambda _req: SimpleNamespace(filters=[existing]),
        }
    )
    patch_tool_module(monkeypatch, folders, client)

    listed = await folders.list_folders()
    assert "Work" in listed

    detail = await folders.get_folder(folder_id=2)
    assert "Work" in detail

    missing = await folders.get_folder(folder_id=999)
    assert "not found" in missing.lower() or "999" in missing

    created = await folders.create_folder(title="Dev", chat_ids=[-1000000000222])
    assert "Dev" in created or "created" in created.lower()
    assert any(isinstance(r, functions.messages.UpdateDialogFilterRequest) for r in client.requests)

    added = await folders.add_chat_to_folder(folder_id=2, chat_id=-1000000000222)
    assert "folder" in added.lower() or "already" in added.lower()

    removed = await folders.remove_chat_from_folder(folder_id=2, chat_id=-1000000000222)
    assert "removed" in removed.lower() or "folder" in removed.lower()

    reordered = await folders.reorder_folders(folder_ids=[2])
    assert "reorder" in reordered.lower() or "order" in reordered.lower()
    assert any(
        isinstance(r, functions.messages.UpdateDialogFiltersOrderRequest) for r in client.requests
    )

    deleted = await folders.delete_folder(folder_id=2)
    assert "deleted" in deleted.lower() or "2" in deleted
    assert any(isinstance(r, functions.messages.UpdateDialogFilterRequest) for r in client.requests)

    # Confirm valid JSON or non-error output on list_folders
    assert "An error occurred" not in listed
    assert not json.dumps(listed).startswith('"An error occurred')
