"""Parameterized repository operations for the local Telegram archive."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any, cast

from .database import Database


def _fts_match(query: str) -> str:
    """Build a syntax-safe FTS5 expression from user-controlled text."""
    tokens: list[str] = []
    for raw_token in query.split():
        token = "".join(character for character in raw_token if character.isprintable())
        token = token.replace('"', '""').strip()
        if token:
            tokens.append(f'"{token}"')
    return " AND ".join(tokens)


class MessageRepository:
    """Small synchronous repository intended to run through ``asyncio.to_thread``."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_chat(self, chat_id: int, title: str, chat_type: str, access_hash: int | None = None) -> None:
        with self.database.connection() as con:
            con.execute(
                """INSERT INTO chats(chat_id, title, chat_type, access_hash, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,
                   chat_type=excluded.chat_type, access_hash=excluded.access_hash,
                   updated_at=excluded.updated_at""",
                (chat_id, title, chat_type, access_hash, datetime.now(UTC).isoformat()),
            )

    def upsert_messages(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.database.connection() as con:
            for row in rows:
                con.execute(
                    """INSERT INTO messages(
                        chat_id, message_id, sender_id, sender_name, message_date,
                        edit_date, text, topic_id, deleted_remotely, media_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id, message_id) DO UPDATE SET
                        sender_id=excluded.sender_id, sender_name=excluded.sender_name,
                        message_date=excluded.message_date, edit_date=excluded.edit_date,
                        text=excluded.text, topic_id=excluded.topic_id,
                        deleted_remotely=excluded.deleted_remotely, media_type=excluded.media_type""",
                    (
                        row["chat_id"], row["message_id"], row.get("sender_id"), row.get("sender_name"),
                        row.get("message_date"), row.get("edit_date"), row.get("text", ""),
                        row.get("topic_id"), int(bool(row.get("deleted_remotely", False))), row.get("media_type"),
                    ),
                )
        return len(rows)

    def checkpoint(self, chat_id: int, last_message_id: int, mode: str) -> None:
        with self.database.connection() as con:
            con.execute(
                """INSERT INTO sync_checkpoints(chat_id, last_message_id, last_sync_at, mode)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET
                   last_message_id=MAX(sync_checkpoints.last_message_id, excluded.last_message_id),
                   last_sync_at=excluded.last_sync_at, mode=excluded.mode""",
                (chat_id, last_message_id, datetime.now(UTC).isoformat(), mode),
            )

    def get_checkpoint(self, chat_id: int) -> sqlite3.Row | None:
        with self.database.connection() as con:
            return cast(sqlite3.Row | None, con.execute("SELECT * FROM sync_checkpoints WHERE chat_id=?", (chat_id,)).fetchone())

    def search(self, chat_id: int, query: str, limit: int, offset: int = 0) -> list[dict[str, Any]]:
        match = _fts_match(query)
        if not match:
            return []
        with self.database.connection() as con:
            rows = con.execute(
                """SELECT m.* FROM messages m JOIN messages_fts f ON f.rowid=m.rowid
                   WHERE m.chat_id=? AND messages_fts MATCH ?
                   ORDER BY m.message_date DESC, m.message_id DESC LIMIT ? OFFSET ?""",
                (chat_id, match, limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest(self, chat_id: int, limit: int) -> list[dict[str, Any]]:
        with self.database.connection() as con:
            rows = con.execute(
                "SELECT * FROM messages WHERE chat_id=? ORDER BY message_id DESC LIMIT ?",
                (chat_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def count(self, chat_id: int) -> int:
        with self.database.connection() as con:
            return int(con.execute("SELECT COUNT(*) FROM messages WHERE chat_id=?", (chat_id,)).fetchone()[0])

    def mark_deleted(self, chat_id: int, message_ids: list[int]) -> int:
        if not message_ids:
            return 0
        placeholders = ",".join("?" for _ in message_ids)
        with self.database.connection() as con:
            result = con.execute(
                f"UPDATE messages SET deleted_remotely=1 WHERE chat_id=? AND message_id IN ({placeholders})",
                [chat_id, *message_ids],
            )
        return result.rowcount

    def export(self, chat_id: int, limit: int) -> list[dict[str, Any]]:
        return self.latest(chat_id, limit)
