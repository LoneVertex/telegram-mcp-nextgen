"""Adversarial chaos tests for protocol, MCP, filesystem, and cache boundaries."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from telethon.errors import FloodWaitError

from telegram_mcp import runtime
from telegram_mcp.config import ConfigurationError
from telegram_mcp.core.errors import ValidationError, error_response, safe_tool
from telegram_mcp.core.retry import run_with_policy
from telegram_mcp.core.security import (
    PathSecurityError,
    atomic_write_bytes,
    confined_path,
    iter_file_chunks,
)
from telegram_mcp.db.database import Database
from telegram_mcp.db.repository import MessageRepository
from telegram_mcp.tools import cache


def make_settings(tmp_path: Path, **overrides):
    values = {
        "api_id": 12345,
        "api_hash": "sentinel-api-hash",
        "session_string": "sentinel-session-string",
        "data_dir": tmp_path / "state",
        "flood_max_retries": 1,
        "flood_max_seconds": 5,
        "backoff_base_seconds": 0.001,
        "rate_capacity": 100,
        "rate_refill_per_second": 100,
    }
    values.update(overrides)
    from telegram_mcp.config import Settings

    return Settings.model_validate(values)


@pytest.mark.asyncio
async def test_floodwait_420_is_bounded_and_cancellation_safe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path, flood_max_retries=1, flood_max_seconds=5)
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("telegram_mcp.core.retry.asyncio.sleep", fake_sleep)
    calls = 0

    async def operation() -> None:
        nonlocal calls
        calls += 1
        error = FloodWaitError(request=None)
        error.seconds = 420
        raise error

    with pytest.raises(FloodWaitError):
        await run_with_policy(operation, settings)
    assert calls == 1
    assert sleeps == []


@pytest.mark.asyncio
async def test_transient_network_retry_is_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path, flood_max_retries=2)
    attempts = 0
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("telegram_mcp.core.retry.asyncio.sleep", fake_sleep)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("transient")
        return "ok"

    assert await run_with_policy(operation, settings) == "ok"
    assert attempts == 3
    assert len(sleeps) == 2


@pytest.mark.asyncio
async def test_fts_adversarial_queries_never_escape_or_crash(tmp_path: Path) -> None:
    database = Database(tmp_path / "cache.db")
    repository = MessageRepository(database)
    repository.upsert_chat(1, "Fuzz", "channel")
    repository.upsert_messages([{"chat_id": 1, "message_id": 1, "text": "ordinary text"}])
    for query in ['AND OR NOT * ("', "\x00", "\\", "\u202eignore", "emoji 😀"]:
        try:
            result = repository.search(1, query, 10)
        except Exception as exc:  # pragma: no cover - documents a security failure if reached
            pytest.fail(f"FTS fuzz query crashed: {query!r}: {exc}")
        assert len(result) <= 10


@pytest.mark.asyncio
async def test_cache_tool_rejects_type_and_bound_inversions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = Database(tmp_path / "cache.db")
    repository = MessageRepository(database)
    monkeypatch.setattr(cache, "_database", database)
    monkeypatch.setattr(cache, "_repository", repository)
    for chat_id, query, limit, offset in [
        (0, "x", 1, 0),
        (1, "", 1, 0),
        (1, "x", 0, 0),
        (1, "x", 1, -1),
    ]:
        with pytest.raises(ValidationError):
            await cache.search_cached_messages(chat_id, query, limit, offset)


@pytest.mark.asyncio
async def test_mutation_gate_cannot_be_bypassed_by_truthy_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.settings, "send_enabled", False)
    invoked = False

    @runtime.with_account(readonly=False)
    async def guarded(*, account=None, dry_run="true") -> str:
        nonlocal invoked
        invoked = True
        return "sent"

    result = json.loads(await guarded(account="default", dry_run="false"))
    assert result["error"] == "MutationDisabled"
    assert result["nothing_sent"] is True
    assert not invoked


@pytest.mark.asyncio
async def test_mcp_safe_error_boundary_preserves_cancellation() -> None:
    @safe_tool
    async def broken() -> str:
        raise RuntimeError("api_hash=sentinel-api-hash session=sentinel-session-string")

    result = await broken()
    assert result == {"error": "InternalServerError", "message": "Internal server error."}
    assert "sentinel" not in json.dumps(result)

    @safe_tool
    async def cancelled() -> str:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await cancelled()


def test_secret_redaction_and_path_fuzzing(tmp_path: Path) -> None:
    from telegram_mcp.config import Settings

    settings = make_settings(tmp_path)
    assert "sentinel" not in json.dumps(settings.redact())
    root = tmp_path / "root"
    root.mkdir()
    for payload in ["../escape", "/etc/passwd", "a/../../b", "bad\x00name"]:
        with pytest.raises(PathSecurityError):
            confined_path(root, payload, allow_missing=True)
    with pytest.raises(ConfigurationError):
        Settings.from_env(
            {"TELEGRAM_DATA_DIR": str(tmp_path), "TELEGRAM_SESSION_NAME": "../escape"}
        )


@pytest.mark.asyncio
async def test_atomic_stream_is_bounded_and_cleans_temp_file(tmp_path: Path) -> None:
    root = tmp_path / "media"

    async def chunks():
        yield b"first"
        yield b"second"

    destination = await atomic_write_bytes(root, "result.bin", chunks(), max_bytes=20)
    assert destination.read_bytes() == b"firstsecond"
    assert destination.stat().st_mode & 0o077 == 0

    async def oversized():
        yield b"12345"
        yield b"67890"

    with pytest.raises(PathSecurityError):
        await atomic_write_bytes(root, "oversized.bin", oversized(), max_bytes=8)
    assert not list(root.glob(".oversized.bin.*"))


@pytest.mark.asyncio
async def test_concurrent_cache_reads_and_writes_are_consistent(tmp_path: Path) -> None:
    database = Database(tmp_path / "concurrent.db")
    repository = MessageRepository(database)
    repository.upsert_chat(7, "Concurrent", "channel")

    async def writer(offset: int) -> None:
        rows = [
            {"chat_id": 7, "message_id": offset + index, "text": f"message {offset + index}"}
            for index in range(1, 21)
        ]
        await asyncio.to_thread(repository.upsert_messages, rows)

    async def reader() -> int:
        rows = await asyncio.to_thread(repository.latest, 7, 1000)
        return len(rows)

    results = await asyncio.gather(
        *(writer(index * 20) for index in range(5)), *(reader() for _ in range(10))
    )
    assert repository.count(7) == 100
    assert all(result <= 100 for result in results[5:])
    assert database.integrity_check() == {"sqlite": "ok", "fts5": "ok"}


@pytest.mark.asyncio
async def test_chunk_reader_rejects_oversized_payload(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"0123456789")
    with pytest.raises(PathSecurityError):
        _ = [chunk async for chunk in iter_file_chunks(path, chunk_size=3, max_bytes=5)]


def test_error_response_never_exposes_technical_details() -> None:
    payload = error_response(OSError("/home/user/.session api_hash=secret"))
    assert payload == {"error": "InternalServerError", "message": "Internal server error."}
    assert "secret" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_mutation_is_not_retried_after_uncertain_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.settings, "send_enabled", True)
    monkeypatch.setattr(runtime.settings, "flood_max_retries", 3)
    attempts = 0

    @runtime.with_account(readonly=False)
    async def mutate(*, account=None) -> str:
        nonlocal attempts
        attempts += 1
        raise ConnectionError("connection dropped after RPC write")

    with pytest.raises(ConnectionError):
        await mutate(account="default")
    assert attempts == 1


@pytest.mark.asyncio
async def test_sync_checkpoint_survives_cancellation_and_resumes_from_last_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = Database(tmp_path / "resume.db")
    repository = MessageRepository(database)
    monkeypatch.setattr(cache, "_database", database)
    monkeypatch.setattr(cache, "_repository", repository)
    monkeypatch.setattr(cache.settings, "max_sync_batch", 100)
    entity = SimpleNamespace(id=7, title="Resume", megagroup=True, broadcast=False)
    monkeypatch.setattr(cache, "ensure_connected", lambda client: asyncio.sleep(0))
    monkeypatch.setattr(cache, "resolve_entity", lambda chat_id, client: _resolved(entity))
    monkeypatch.setattr(cache, "get_entity_type", lambda value: "Supergroup")
    monkeypatch.setattr(cache, "get_sender_name", lambda message: "sender")

    first_min_ids: list[int] = []

    async def interrupted_iter(_entity, *, limit, min_id, reverse):
        first_min_ids.append(min_id)
        for index in range(1, 61):
            if index == 56:
                raise asyncio.CancelledError()
            yield SimpleNamespace(
                id=index, sender_id=1, date=None, edit_date=None, message=f"m{index}", media=None
            )

    class InterruptedClient:
        def iter_messages(self, entity, *, limit, min_id, reverse):
            return interrupted_iter(entity, limit=limit, min_id=min_id, reverse=reverse)

    monkeypatch.setattr(cache, "get_client", lambda account: InterruptedClient())
    with pytest.raises(asyncio.CancelledError):
        await cache.sync_chat_cache.__wrapped__(7, limit=100, mode="incremental", account="default")
    assert repository.count(7) == 50
    checkpoint = repository.get_checkpoint(7)
    assert checkpoint is not None
    assert checkpoint["last_message_id"] == 50
    assert first_min_ids == [0]

    second_min_ids: list[int] = []

    async def resumed_iter(_entity, *, limit, min_id, reverse):
        second_min_ids.append(min_id)
        for index in range(51, 61):
            yield SimpleNamespace(
                id=index, sender_id=1, date=None, edit_date=None, message=f"m{index}", media=None
            )

    class ResumedClient:
        def iter_messages(self, entity, *, limit, min_id, reverse):
            return resumed_iter(entity, limit=limit, min_id=min_id, reverse=reverse)

    monkeypatch.setattr(cache, "get_client", lambda account: ResumedClient())
    result = await cache.sync_chat_cache.__wrapped__(
        7, limit=100, mode="incremental", account="default"
    )
    assert result["synced_messages"] == 10
    assert result["last_message_id"] == 60
    assert second_min_ids == [50]
    assert repository.count(7) == 60


async def _resolved(entity: object) -> object:
    return entity


@pytest.mark.asyncio
async def test_open_photo_uses_atomic_save_primitive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from telegram_mcp.tools import media

    destination = tmp_path / "photo.jpg"
    destination.write_bytes(b"old-photo")
    reference = SimpleNamespace(identifier=9)
    calls: list[tuple[Path, str, int]] = []

    async def fake_atomic(root: Path, raw_path: str, chunks, *, max_bytes: int) -> Path:
        calls.append((root, raw_path, max_bytes))
        return destination

    async def fake_find(*args, **kwargs):
        return reference

    async def fake_download(*args, **kwargs):
        return b"new-photo"

    async def fake_resolve(*args, **kwargs):
        return destination, None

    monkeypatch.setattr(media, "atomic_write_bytes", fake_atomic)
    monkeypatch.setattr(media, "find_photo_reference", fake_find)
    monkeypatch.setattr(media, "download_photo_bytes", fake_download)
    monkeypatch.setattr(media, "_resolve_writable_file_path", fake_resolve)
    monkeypatch.setattr(media, "get_client", lambda account: object())
    monkeypatch.setattr(media, "resolve_entity", lambda chat_id, client: _resolved(SimpleNamespace(id=1)))

    body = media.open_photo.__wrapped__.__wrapped__
    result = await body(chat_id=1, save_path=str(destination), account="default")
    assert result is not None
    assert calls == [(destination.parent, destination.name, media.settings.max_media_download_bytes)]
    assert destination.read_bytes() == b"old-photo"
