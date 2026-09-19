"""Core lifecycle, reliability, security, and registration primitives."""

from .client import TelegramClientCoordinator
from .errors import (
    AuthorizationError,
    PathError,
    SyncError,
    TelegramMcpError,
    ValidationError,
    error_response,
    safe_tool,
)
from .locks import KeyedLockManager
from .rate_limiter import TokenBucket
from .registry import allowed_tool_names, apply_tool_tier
from .retry import run_with_policy
from .security import (
    PathSecurityError,
    atomic_write_bytes,
    confined_path,
    iter_file_chunks,
    safe_filename,
    validate_mime,
)
from .tl_custom import CreateForumTopicRequest, GetForumTopicsRequest

__all__ = [
    "AuthorizationError",
    "CreateForumTopicRequest",
    "GetForumTopicsRequest",
    "KeyedLockManager",
    "PathError",
    "PathSecurityError",
    "SyncError",
    "TelegramClientCoordinator",
    "TelegramMcpError",
    "TokenBucket",
    "ValidationError",
    "allowed_tool_names",
    "apply_tool_tier",
    "atomic_write_bytes",
    "confined_path",
    "error_response",
    "iter_file_chunks",
    "run_with_policy",
    "safe_filename",
    "safe_tool",
    "validate_mime",
]
