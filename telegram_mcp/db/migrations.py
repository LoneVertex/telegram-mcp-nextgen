"""Schema versioning entrypoint for the local archive."""

from __future__ import annotations

from pathlib import Path

from .database import SCHEMA_VERSION, Database


def migrate(path: Path) -> Database:
    """Create or upgrade the archive schema and return an initialized database."""
    database = Database(path)
    return database


__all__ = ["SCHEMA_VERSION", "migrate"]
