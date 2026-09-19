"""Typed, side-effect-free configuration for the next-generation Telegram MCP server."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, cast

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

Tier = Literal["essential", "core", "standard", "full"]


class ConfigurationError(ValueError):
    """Raised when runtime configuration is invalid or incomplete."""


class Settings(BaseModel):
    """Validated configuration; constructing this model never authenticates Telegram."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    api_id: int | None = Field(default=None, ge=1)
    api_hash: str | None = None
    session_string: str | None = None
    session_name: str = "telegram"
    data_dir: Path = Path.home() / ".local" / "state" / "telegram-mcp"
    session_dir: Path | None = None
    cache_dir: Path | None = None
    media_dir: Path | None = None
    exports_dir: Path | None = None
    db_path: Path | None = None
    tier: Tier = "essential"
    exposed_tools: str = "all"
    allow_server_roots_fallback: bool = False
    send_enabled: bool = False
    destructive_enabled: bool = False
    max_media_download_bytes: int = Field(default=200 * 1024 * 1024, ge=1)
    max_media_upload_bytes: int = Field(default=200 * 1024 * 1024, ge=1)
    max_search_limit: int = Field(default=100, ge=1, le=10_000)
    max_sync_batch: int = Field(default=100, ge=1, le=10_000)
    flood_max_retries: int = Field(default=4, ge=0, le=20)
    flood_max_seconds: int = Field(default=3600, ge=1, le=86_400)
    backoff_base_seconds: float = Field(default=1.0, gt=0, le=60)
    rate_capacity: int = Field(default=8, ge=1, le=100)
    rate_refill_per_second: float = Field(default=2.0, gt=0, le=100)
    log_level: str = "INFO"

    @field_validator("api_hash", "session_string", mode="before")
    @classmethod
    def blank_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, value: str) -> str:
        if Path(value).name != value or value in {"", ".", ".."}:
            raise ConfigurationError("session_name must be a simple filename")
        return value

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, value: str) -> str:
        if value not in {"essential", "core", "standard", "full"}:
            raise ConfigurationError("tier must be one of: essential, core, standard, full")
        return value

    @model_validator(mode="after")
    def derive_paths(self) -> Settings:
        data_dir = self.data_dir.expanduser().resolve()
        object.__setattr__(self, "data_dir", data_dir)
        defaults = {
            "session_dir": data_dir / "session",
            "cache_dir": data_dir / "cache",
            "media_dir": data_dir / "media",
            "exports_dir": data_dir / "exports",
            "db_path": data_dir / "cache" / "telegram.db",
        }
        for field, default in defaults.items():
            value = getattr(self, field)
            resolved = (default if value is None else Path(value)).expanduser().resolve()
            object.__setattr__(self, field, resolved)
            try:
                resolved.relative_to(data_dir)
            except ValueError as exc:
                raise ConfigurationError(f"{field} must remain under data_dir") from exc
        return self

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Load dotenv values followed by process/mapping overrides without side effects."""
        source: dict[str, Any] = {}
        env = dict(os.environ if environ is None else environ)
        env_file = env.get("TELEGRAM_ENV_FILE")
        if env_file:
            source.update({key: value for key, value in dotenv_values(env_file).items() if value is not None})
        source.update(env)

        def get(name: str, default: Any = None) -> Any:
            return source.get(name, default)

        def integer(name: str, default: int | None = None) -> int | None:
            raw = get(name, default)
            if raw in (None, ""):
                return None
            try:
                return int(raw)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(f"{name} must be an integer") from exc

        def integer_default(name: str, default: int) -> int:
            value = integer(name, default)
            assert value is not None
            return value

        def number(name: str, default: float) -> float:
            raw = get(name, default)
            try:
                return float(raw)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(f"{name} must be a number") from exc

        def boolean(name: str, default: bool) -> bool:
            raw = get(name, default)
            if isinstance(raw, bool):
                return raw
            normalized = str(raw).strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
            raise ConfigurationError(f"{name} must be a boolean")

        payload: dict[str, Any] = {
            "api_id": integer("TELEGRAM_API_ID"),
            "api_hash": get("TELEGRAM_API_HASH"),
            "session_string": get("TELEGRAM_SESSION_STRING"),
            "session_name": get("TELEGRAM_SESSION_NAME", "telegram"),
            "data_dir": get("TELEGRAM_DATA_DIR", str(Path.home() / ".local" / "state" / "telegram-mcp")),
            "tier": get("TELEGRAM_MCP_TIER", "essential"),
            "exposed_tools": get("TELEGRAM_EXPOSED_TOOLS", "all"),
            "allow_server_roots_fallback": boolean("TELEGRAM_ALLOW_SERVER_ROOTS_FALLBACK", False),
            "send_enabled": boolean("TELEGRAM_SEND_ENABLED", False),
            "destructive_enabled": boolean("TELEGRAM_DESTRUCTIVE_ENABLED", False),
            "max_media_download_bytes": integer_default("MAX_MEDIA_DOWNLOAD_SIZE_MB", 200) * 1024 * 1024,
            "max_media_upload_bytes": integer_default("MAX_MEDIA_UPLOAD_SIZE_MB", 200) * 1024 * 1024,
            "max_search_limit": integer_default("TELEGRAM_MAX_SEARCH_LIMIT", 100),
            "max_sync_batch": integer_default("TELEGRAM_SYNC_BATCH_SIZE", 100),
            "flood_max_retries": integer_default("TELEGRAM_FLOOD_MAX_RETRIES", 4),
            "flood_max_seconds": integer_default("TELEGRAM_FLOOD_MAX_SECONDS", 3600),
            "rate_capacity": integer_default("TELEGRAM_RATE_CAPACITY", 8),
            "backoff_base_seconds": number("TELEGRAM_BACKOFF_BASE_SECONDS", 1.0),
            "rate_refill_per_second": number("TELEGRAM_RATE_REFILL_PER_SECOND", 2.0),
            "log_level": str(get("TELEGRAM_LOG_LEVEL", "INFO")).upper(),
        }
        for field, env_name in {
            "session_dir": "TELEGRAM_SESSION_DIR",
            "cache_dir": "TELEGRAM_CACHE_DIR",
            "media_dir": "TELEGRAM_MEDIA_DIR",
            "exports_dir": "TELEGRAM_EXPORTS_DIR",
            "db_path": "TELEGRAM_DB_PATH",
        }.items():
            if get(env_name) not in (None, ""):
                payload[field] = get(env_name)
        try:
            return cast(Settings, cls.model_validate(payload))
        except PydanticValidationError as exc:
            raise ConfigurationError(str(exc)) from exc

    def require_credentials(self) -> tuple[int, str]:
        if self.api_id is None or not self.api_hash:
            raise ConfigurationError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
        return self.api_id, self.api_hash

    def require_session(self) -> str:
        if not self.session_string:
            raise ConfigurationError("TELEGRAM_SESSION_STRING is required for the MCP server")
        return self.session_string

    @property
    def session_path(self) -> Path:
        assert self.session_dir is not None
        return self.session_dir / self.session_name

    def ensure_directories(self) -> None:
        for path in (self.session_dir, self.cache_dir, self.media_dir, self.exports_dir):
            assert path is not None
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o700)
        assert self.db_path is not None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def redact(self) -> dict[str, Any]:
        return {
            "data_dir": str(self.data_dir),
            "session_dir": str(self.session_dir),
            "cache_dir": str(self.cache_dir),
            "media_dir": str(self.media_dir),
            "exports_dir": str(self.exports_dir),
            "tier": self.tier,
            "exposed_tools": self.exposed_tools,
            "send_enabled": self.send_enabled,
            "destructive_enabled": self.destructive_enabled,
            "max_media_download_bytes": self.max_media_download_bytes,
            "max_media_upload_bytes": self.max_media_upload_bytes,
            "flood_max_retries": self.flood_max_retries,
            "rate_capacity": self.rate_capacity,
            "rate_refill_per_second": self.rate_refill_per_second,
        }
