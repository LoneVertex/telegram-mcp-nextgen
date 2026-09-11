"""Import tool modules so their MCP decorators register with the shared server."""

from telegram_mcp.tools.accounts import *
from telegram_mcp.tools.contacts import *
from telegram_mcp.tools.chats import *
from telegram_mcp.tools.messages import *
from telegram_mcp.tools.groups import *
from telegram_mcp.tools.media import *
from telegram_mcp.tools.profile import *
from telegram_mcp.tools.folders import *
from telegram_mcp.tools.events import *
from telegram_mcp.tools.cache import *

from telegram_mcp.core.schema_enricher import enrich_all_tools
from telegram_mcp.runtime import mcp

enrich_all_tools(mcp)

__all__ = [name for name in globals() if not name.startswith("_")]
