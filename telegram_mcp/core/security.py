"""Security primitives for filesystem and mutation boundaries."""

from __future__ import annotations

import asyncio
import contextlib
import mimetypes
import os
import re
import tempfile
from collections.abc import AsyncIterator, Iterable
from pathlib import Path

from ..config import Settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


class PathSecurityError(ValueError):
    """Raised when a requested path cannot be proven safe."""


def safe_filename(value: str, fallback: str = "telegram-file") -> str:
    name = Path(value).name.strip()
    name = _SAFE_NAME.sub("_", name).replace("..", "_")
    name = name.strip(" .")
    return name[:180] or fallback


def confined_path(root: Path, raw_path: str, *, allow_missing: bool = False) -> Path:
    """Resolve a path under root and reject traversal, symlinks, and escapes."""
    if not raw_path or "\x00" in raw_path:
        raise PathSecurityError("path is empty or contains a NUL byte")
    candidate = Path(raw_path).expanduser()
    if ".." in candidate.parts:
        raise PathSecurityError("path traversal is not allowed")
    if not candidate.is_absolute():
        candidate = root / candidate
    probe = candidate
    while probe != probe.parent:
        if probe.is_symlink():
            raise PathSecurityError("symlink path components are not allowed")
        probe = probe.parent
        if not probe.exists():
            continue
        if probe.is_symlink():
            raise PathSecurityError("symlink path components are not allowed")
    root_real = root.expanduser().resolve(strict=True)
    if allow_missing:
        resolved = candidate.resolve(strict=False)
        existing = resolved
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        if existing.is_symlink():
            raise PathSecurityError("symlinked path components are not allowed")
    else:
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise PathSecurityError("path does not exist") from exc
        if resolved.is_symlink():
            raise PathSecurityError("symlink targets are not allowed")
    try:
        resolved.relative_to(root_real)
    except ValueError as exc:
        raise PathSecurityError("path is outside the configured root") from exc
    return resolved


def validate_mime(path: Path, allowed: Iterable[str] | None = None) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if not mime:
        raise PathSecurityError("could not determine a MIME type")
    if allowed is not None and mime not in set(allowed):
        raise PathSecurityError("MIME type is not allowed")
    return mime


async def iter_file_chunks(path: Path, *, chunk_size: int = 1024 * 1024, max_bytes: int) -> AsyncIterator[bytes]:
    """Read a bounded file incrementally in a worker thread."""
    if path.stat().st_size > max_bytes:
        raise PathSecurityError("file exceeds configured size limit")
    with path.open("rb") as handle:
        total = 0
        while True:
            chunk = await asyncio.to_thread(handle.read, chunk_size)
            if not chunk:
                return
            total += len(chunk)
            if total > max_bytes:
                raise PathSecurityError("file exceeds configured size limit")
            yield chunk


async def atomic_write_bytes(root: Path, raw_path: str, chunks: AsyncIterator[bytes], *, max_bytes: int) -> Path:
    """Write an async byte stream atomically beneath root with bounded size."""
    root.mkdir(parents=True, exist_ok=True)
    destination = confined_path(root, raw_path, allow_missing=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    total = 0
    try:
        with os.fdopen(fd, "wb") as handle:
            async for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise PathSecurityError("media stream yielded a non-byte chunk")
                total += len(chunk)
                if total > max_bytes:
                    raise PathSecurityError("media stream exceeds configured size limit")
                await asyncio.to_thread(handle.write, chunk)
            await asyncio.to_thread(handle.flush)
            await asyncio.to_thread(os.fsync, handle.fileno())
        await asyncio.to_thread(os.replace, temporary, destination)
        await asyncio.to_thread(os.chmod, destination, 0o600)
        return destination
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def settings_media_root(settings: Settings) -> Path:
    assert settings.media_dir is not None
    return settings.media_dir
