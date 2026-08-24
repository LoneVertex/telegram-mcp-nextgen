"""SQLite storage with WAL mode, schema migration, and FTS5 maintenance."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1


class Database:
    """Own schema initialization and short-lived configured SQLite connections."""

    def __init__(self, path: Path, *, busy_timeout_ms: int = 10_000) -> None:
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms
        self._transaction_lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=self.busy_timeout_ms / 1000, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Serialize local transactions while preserving WAL for external readers."""
        with self._transaction_lock:
            connection = self.connect()
            try:
                connection.execute("BEGIN")
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()

    def initialize(self) -> None:
        connection = self.connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    chat_type TEXT NOT NULL,
                    access_hash INTEGER,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    chat_id INTEGER NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                    message_id INTEGER NOT NULL,
                    sender_id INTEGER,
                    sender_name TEXT,
                    message_date TEXT,
                    edit_date TEXT,
                    text TEXT NOT NULL,
                    topic_id INTEGER,
                    deleted_remotely INTEGER NOT NULL DEFAULT 0,
                    media_type TEXT,
                    PRIMARY KEY(chat_id, message_id)
                );
                CREATE TABLE IF NOT EXISTS sync_checkpoints (
                    chat_id INTEGER PRIMARY KEY REFERENCES chats(chat_id) ON DELETE CASCADE,
                    last_message_id INTEGER NOT NULL DEFAULT 0,
                    last_sync_at TEXT NOT NULL,
                    mode TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_chat_date ON messages(chat_id, message_date DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(chat_id, sender_id, message_date DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_topic ON messages(chat_id, topic_id, message_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    text,
                    sender_name,
                    content='messages',
                    content_rowid='rowid'
                );
                CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(rowid, text, sender_name) VALUES (new.rowid, new.text, new.sender_name);
                END;
                CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, text, sender_name)
                    VALUES ('delete', old.rowid, old.text, old.sender_name);
                END;
                CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE OF text, sender_name ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, text, sender_name)
                    VALUES ('delete', old.rowid, old.text, old.sender_name);
                    INSERT INTO messages_fts(rowid, text, sender_name)
                    VALUES (new.rowid, new.text, new.sender_name);
                END;
                """
            )
            connection.execute(
                "INSERT INTO schema_meta(key, value) VALUES ('version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            connection.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
        finally:
            connection.close()

    def integrity_check(self) -> dict[str, str]:
        connection = self.connect()
        try:
            result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            connection.execute("INSERT INTO messages_fts(messages_fts) VALUES ('integrity-check')")
            return {"sqlite": result, "fts5": "ok"}
        finally:
            connection.close()

    def rebuild_fts(self) -> None:
        with self.connection() as connection:
            connection.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
