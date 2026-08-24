"""FTS5 maintenance facade."""

from __future__ import annotations

from .database import Database


def rebuild(database: Database) -> None:
    database.rebuild_fts()


def integrity(database: Database) -> dict[str, str]:
    return database.integrity_check()
