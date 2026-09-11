"""Telegram MCP server package."""

from typing import Any

__version__ = "4.1.1"


def __getattr__(name: str) -> Any:
    if name == "mcp":
        from telegram_mcp.install_guard import assert_safe_distribution

        assert_safe_distribution()
        from telegram_mcp.runtime import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["__version__", "mcp"]
