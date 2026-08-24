"""Tests for next-generation reliability, security, and storage primitives."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from telethon.errors import FloodWaitError

from telegram_mcp.config import ConfigurationError, Settings
from telegram_mcp.core.locks import KeyedLockManager
from telegram_mcp.core.rate_limiter import TokenBucket
from telegram_mcp.core.retry import run_with_policy
from telegram_mcp.core.security import (
    PathSecurityError,
    atomic_write_bytes,
    confined_path,
    iter_file_chunks,
    safe_filename,
    validate_mime,
)
from telegram_mcp.db.database import Database
from telegram_mcp.db.repository import MessageRepository


def make_settings(tmp_path: Path, **values: str) -> Settings:
    environment = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdef123456",
        "TELEGRAM_SESSION_STRING": "session",
        "TELEGRAM_DATA_DIR": str(tmp_path),
    }
    environment.update(values)
    return Settings.from_env(environment)


def test_settings_are_typed_and_redacted(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, TELEGRAM_MCP_TIER="standard")
    assert settings.tier == "standard"
    assert settings.require_credentials() == (12345, "abcdef123456")
    assert settings.require_session() == "session"
    assert settings.session_path == tmp_path / "session" / "telegram"
    settings.ensure_directories()
    assert settings.media_dir.is_dir()
    assert "api_hash" not in settings.redact()
    assert "session_string" not in settings.redact()


def test_settings_reject_bad_values(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="must be an integer"):
        Settings.from_env({"TELEGRAM_API_ID": "bad", "TELEGRAM_DATA_DIR": str(tmp_path)})
    with pytest.raises(ConfigurationError, match="tier"):
        make_settings(tmp_path, TELEGRAM_MCP_TIER="unsafe")
    with pytest.raises(ConfigurationError, match="session_name"):
        make_settings(tmp_path, TELEGRAM_SESSION_NAME="../bad")
    with pytest.raises(ConfigurationError, match="under data_dir"):
        make_settings(tmp_path, TELEGRAM_MEDIA_DIR="/tmp/outside")
    with pytest.raises(ConfigurationError, match="required"):
        Settings.from_env({"TELEGRAM_DATA_DIR": str(tmp_path)}).require_credentials()
    with pytest.raises(ConfigurationError, match="required"):
        Settings.from_env({"TELEGRAM_DATA_DIR": str(tmp_path)}).require_session()


@pytest.mark.asyncio
async def test_keyed_locks_serialize_same_key_and_release_on_cancel() -> None:
    locks = KeyedLockManager()
    events: list[str] = []

    async def worker(label: str) -> None:
        async with locks.hold("chat"):
            events.append(f"start-{label}")
            await asyncio.sleep(0)
            events.append(f"end-{label}")

    await asyncio.gather(worker("a"), worker("b"))
    assert events in (["start-a", "end-a", "start-b", "end-b"], ["start-b", "end-b", "start-a", "end-a"])
    assert locks.key_count == 0

    blocker = asyncio.Event()

    async def held() -> None:
        async with locks.hold("cancel"):
            await blocker.wait()

    task = asyncio.create_task(held())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert locks.key_count == 0


@pytest.mark.asyncio
async def test_rate_limiter_bounds_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    bucket = TokenBucket(1, 1000)
    await bucket.acquire()
    assert bucket.available < 1.1
    await bucket.acquire()
    assert bucket.available <= 1


@pytest.mark.asyncio
async def test_retry_handles_flood_wait_and_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path, TELEGRAM_FLOOD_MAX_RETRIES="2", TELEGRAM_FLOOD_MAX_SECONDS="10", TELEGRAM_BACKOFF_BASE_SECONDS="0.001")
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            error = FloodWaitError(request=None)
            error.seconds = 0
            raise error
        if attempts == 2:
            raise ConnectionError("offline")
        return "ok"

    assert await run_with_policy(operation, settings) == "ok"
    assert attempts == 3
    assert len(sleeps) == 2


@pytest.mark.asyncio
async def test_security_confinement_and_streaming(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("abcdef", encoding="utf-8")
    assert safe_filename("../a:b.txt") == "a_b.txt"
    assert validate_mime(source) == "text/plain"
    assert confined_path(root, "source.txt") == source
    with pytest.raises(PathSecurityError):
        confined_path(root, "../outside.txt")
    with pytest.raises(PathSecurityError):
        confined_path(root, "/tmp/outside.txt", allow_missing=True)
    chunks = [chunk async for chunk in iter_file_chunks(source, chunk_size=2, max_bytes=10)]
    assert b"".join(chunks) == b"abcdef"

    async def stream():
        yield b"hello"
        yield b" world"

    destination = await atomic_write_bytes(root, "output.bin", stream(), max_bytes=32)
    assert destination.read_bytes() == b"hello world"
    assert destination.stat().st_mode & 0o777 == 0o600

    async def too_large():
        yield b"123456"

    with pytest.raises(PathSecurityError):
        await atomic_write_bytes(root, "too-large.bin", too_large(), max_bytes=5)


def test_repository_fts_and_checkpoint(tmp_path: Path) -> None:
    database = Database(tmp_path / "cache" / "telegram.db")
    repository = MessageRepository(database)
    repository.upsert_chat(1, "Тестовый чат", "supergroup")
    rows = [
        {"chat_id": 1, "message_id": 1, "sender_id": 10, "sender_name": "Алиса", "message_date": "2026-01-01", "text": "hello world"},
        {"chat_id": 1, "message_id": 2, "sender_id": 11, "sender_name": "Боб", "message_date": "2026-01-02", "text": "second message"},
    ]
    assert repository.upsert_messages(rows) == 2
    assert repository.search(1, "hello", 10)[0]["message_id"] == 1
    assert repository.latest(1, 1)[0]["message_id"] == 2
    assert repository.count(1) == 2
    repository.checkpoint(1, 2, "incremental")
    assert repository.get_checkpoint(1)["last_message_id"] == 2
    assert repository.mark_deleted(1, [1]) == 1
    assert repository.search(1, "hello", 10)[0]["deleted_remotely"] == 1
    assert database.integrity_check() == {"sqlite": "ok", "fts5": "ok"}
    database.rebuild_fts()


@pytest.mark.asyncio
async def test_client_coordinator_serializes_calls_and_closes(tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            self.connected = False
            self.disconnected = False

        async def connect(self) -> None:
            self.connected = True

        async def is_user_authorized(self) -> bool:
            return True

        async def disconnect(self) -> None:
            self.disconnected = True

        async def ping(self) -> str:
            return "pong"

    from telegram_mcp.core.client import TelegramClientCoordinator

    settings = make_settings(tmp_path)
    coordinator = TelegramClientCoordinator(settings, factory=FakeClient)
    assert await coordinator.call(lambda client: client.ping()) == "pong"
    assert coordinator.client is not None
    await coordinator.close()
    assert coordinator.client is None
    with pytest.raises(RuntimeError, match="closed"):
        await coordinator.start()


def test_error_taxonomy_and_typed_models() -> None:
    from telegram_mcp.core.errors import (
        AuthorizationError,
        PathError,
        SyncError,
        TelegramMcpError,
        error_response,
    )
    from telegram_mcp.models import ChatRecord, MediaRecord, MessageRecord

    assert error_response(AuthorizationError("no", public_message="denied")) == {"error": "AuthorizationError", "message": "denied"}
    assert error_response(PathError("bad", public_message="invalid path"))["error"] == "PathError"
    assert error_response(SyncError("bad"))["error"] == "SyncError"
    assert error_response(TypeError("bad"))["error"] == "InvalidInput"
    assert issubclass(AuthorizationError, TelegramMcpError)
    assert ChatRecord and MediaRecord and MessageRecord


def test_registry_prunes_unknown_tools() -> None:
    from types import SimpleNamespace

    from telegram_mcp.core.registry import apply_tool_tier

    class Manager:
        def __init__(self) -> None:
            self.tools = [SimpleNamespace(name="list_accounts"), SimpleNamespace(name="delete_message")]

        def list_tools(self):
            return list(self.tools)

        def remove_tool(self, name: str) -> None:
            self.tools = [tool for tool in self.tools if tool.name != name]

    server = SimpleNamespace(_tool_manager=Manager())
    assert apply_tool_tier(server, "core") == ["delete_message"]
    assert [tool.name for tool in server._tool_manager.list_tools()] == ["list_accounts"]


def test_security_rejects_symlinks_and_mime(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "target.txt"
    target.write_text("safe", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to(target)
    with pytest.raises(PathSecurityError):
        confined_path(root, "link.txt")
    unknown = root / "unknown.invalidext"
    unknown.write_bytes(b"data")
    with pytest.raises(PathSecurityError):
        validate_mime(unknown)
    with pytest.raises(PathSecurityError):
        validate_mime(target, {"application/json"})


def test_database_migration_and_fts_facades(tmp_path: Path) -> None:
    from telegram_mcp.db.fts import integrity, rebuild
    from telegram_mcp.db.migrations import SCHEMA_VERSION, migrate

    database = migrate(tmp_path / "migrated.db")
    assert SCHEMA_VERSION == 1
    rebuild(database)
    assert integrity(database) == {"sqlite": "ok", "fts5": "ok"}


@pytest.mark.asyncio
async def test_coordinator_rejects_unauthorized_client(tmp_path: Path) -> None:
    class Unauthorized:
        def __init__(self, *_args, **_kwargs):
            pass

        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return False

    from telegram_mcp.core.client import TelegramClientCoordinator

    with pytest.raises(RuntimeError, match="not authorized"):
        await TelegramClientCoordinator(make_settings(tmp_path), factory=Unauthorized).start()


@pytest.mark.asyncio
async def test_coordinator_operation_exposes_lock_count(tmp_path: Path) -> None:
    class Client:
        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return True

        async def disconnect(self) -> None:
            return None

    from telegram_mcp.core.client import TelegramClientCoordinator

    coordinator = TelegramClientCoordinator(make_settings(tmp_path), factory=lambda *_args: Client())
    async with coordinator.operation("chat:1"):
        assert coordinator.active_lock_keys == 1
    assert coordinator.active_lock_keys == 0
    await coordinator.close()


def test_error_response_maps_telethon_failures() -> None:
    from telethon.errors import (
        ChannelPrivateError,
        ChatAdminRequiredError,
        FloodWaitError,
        UserDeactivatedBanError,
    )

    from telegram_mcp.core.errors import error_response

    flood = FloodWaitError(request=None)
    flood.seconds = 7
    assert error_response(flood)["wait_seconds"] == 7
    assert error_response(ChatAdminRequiredError(request=None))["error"] == "ChatAdminRequiredError"
    assert error_response(ChannelPrivateError(request=None))["error"] == "PeerUnavailable"
    assert error_response(UserDeactivatedBanError(request=None))["error"] == "UserDeactivatedBanError"


@pytest.mark.asyncio
async def test_safe_tool_converts_failures_but_propagates_cancel() -> None:
    from telegram_mcp.core.errors import safe_tool

    @safe_tool
    async def broken() -> str:
        raise RuntimeError("private")

    assert await broken() == {"error": "InternalServerError", "message": "Internal server error."}

    @safe_tool
    async def cancelled() -> str:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await cancelled()


@pytest.mark.asyncio
async def test_rate_limiter_rejects_invalid_requests() -> None:
    with pytest.raises(ValueError):
        TokenBucket(0, 1)
    bucket = TokenBucket(2, 100)
    with pytest.raises(ValueError):
        await bucket.acquire(0)
    with pytest.raises(ValueError):
        await bucket.acquire(3)


@pytest.mark.asyncio
async def test_security_rejects_non_bytes_and_oversized_files(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "source.bin"
    source.write_bytes(b"123456")
    with pytest.raises(PathSecurityError):
        _ = [chunk async for chunk in iter_file_chunks(source, chunk_size=2, max_bytes=5)]

    async def non_bytes():
        yield "not bytes"  # type: ignore[misc]

    with pytest.raises(PathSecurityError):
        await atomic_write_bytes(root, "bad.bin", non_bytes(), max_bytes=20)

    with pytest.raises(PathSecurityError):
        confined_path(root, "")
    with pytest.raises(PathSecurityError):
        confined_path(root, "bad\x00name")


def test_settings_file_and_boolean_parsing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_API_ID=12345\nTELEGRAM_API_HASH=hash_value\nTELEGRAM_SESSION_STRING=session_value\nTELEGRAM_SEND_ENABLED=yes\n", encoding="utf-8")
    settings = Settings.from_env({"TELEGRAM_ENV_FILE": str(env_file), "TELEGRAM_DATA_DIR": str(tmp_path / "state")})
    assert settings.send_enabled is True
    with pytest.raises(ConfigurationError, match="boolean"):
        Settings.from_env({"TELEGRAM_DATA_DIR": str(tmp_path), "TELEGRAM_SEND_ENABLED": "maybe"})
    with pytest.raises(ConfigurationError, match="number"):
        Settings.from_env({"TELEGRAM_DATA_DIR": str(tmp_path), "TELEGRAM_BACKOFF_BASE_SECONDS": "bad"})


@pytest.mark.asyncio
async def test_retry_stops_at_configured_limits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path, TELEGRAM_FLOOD_MAX_RETRIES="0", TELEGRAM_FLOOD_MAX_SECONDS="1")

    async def flood() -> None:
        error = FloodWaitError(request=None)
        error.seconds = 2
        raise error

    with pytest.raises(FloodWaitError):
        await run_with_policy(flood, settings)

    settings = make_settings(tmp_path, TELEGRAM_FLOOD_MAX_RETRIES="0")
    with pytest.raises(ConnectionError):
        await run_with_policy(lambda: _raise_connection(), settings)


async def _raise_connection() -> None:
    raise ConnectionError("offline")


@pytest.mark.asyncio
async def test_client_start_reuses_existing_client_and_empty_close(tmp_path: Path) -> None:
    class Client:
        async def connect(self) -> None:
            return None

        async def is_user_authorized(self) -> bool:
            return True

        async def disconnect(self) -> None:
            return None

    from telegram_mcp.core.client import TelegramClientCoordinator

    first = TelegramClientCoordinator(make_settings(tmp_path), factory=lambda *_args: Client())
    client = await first.start()
    assert await first.start() is client
    await first.close()
    second = TelegramClientCoordinator(make_settings(tmp_path), factory=lambda *_args: Client())
    await second.close()


def test_repository_empty_and_transaction_rollback(tmp_path: Path) -> None:
    database = Database(tmp_path / "rollback.db")
    repository = MessageRepository(database)
    assert repository.upsert_messages([]) == 0
    assert repository.search(99, "", 10) == []
    assert repository.mark_deleted(99, []) == 0
    assert repository.count(99) == 0
    with pytest.raises(sqlite3.IntegrityError), database.connection() as connection:
        connection.execute("INSERT INTO messages(chat_id, message_id, text) VALUES (999, 1, 'x')")
    assert repository.count(999) == 0


def test_security_missing_component_and_root_helper(tmp_path: Path) -> None:
    from telegram_mcp.core.security import settings_media_root

    root = tmp_path / "root"
    root.mkdir()
    nested = root / "nested"
    nested.mkdir()
    link = nested / "link"
    link.symlink_to(root)
    with pytest.raises(PathSecurityError):
        confined_path(root, "nested/link/new.bin", allow_missing=True)
    with pytest.raises(PathSecurityError):
        confined_path(root, "missing.bin")
    settings = make_settings(tmp_path)
    assert settings_media_root(settings) == settings.media_dir
