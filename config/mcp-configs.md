# MCP Client Configuration

The safest default is local stdio with `TELEGRAM_MCP_TIER=essential` and write operations disabled. Store credentials in a process environment or a secret manager; do not put API hashes or session strings in client configuration files.

## Desktop MCP clients

```json
{
  "mcpServers": {
    "telegram": {
      "command": "telegram-mcp",
      "args": ["/home/user/telegram-files"],
      "env": {
        "TELEGRAM_API_ID": "${TELEGRAM_API_ID}",
        "TELEGRAM_API_HASH": "${TELEGRAM_API_HASH}",
        "TELEGRAM_SESSION_STRING": "${TELEGRAM_SESSION_STRING}",
        "TELEGRAM_MCP_TIER": "essential",
        "TELEGRAM_SEND_ENABLED": "false",
        "TELEGRAM_DESTRUCTIVE_ENABLED": "false"
      }
    }
  }
}
```

The positional path is an optional server-side allowed root for file tools. Client MCP Roots are preferred and an empty or unverifiable Roots response remains deny-all unless `TELEGRAM_ALLOW_SERVER_ROOTS_FALLBACK=true` is explicitly set.

## Essential tier (Default)

The `essential` tier is the recommended, highly coherent default containing exactly 22 tools (strictly within Glama's ≤25 tool penalty threshold). It provides a full, self-contained conversational and media lifecycle:
- **Read & Search:** `get_me`, `list_chats`, `get_chat`, `search_public_chats`, `resolve_username`, `get_messages`, `search_messages`.
- **Write & Mutation:** `send_message`, `reply_to_message`, `edit_message`, `delete_message`, `pin_message`, `unpin_message`, `mark_as_read`.
- **Media & Files:** `send_file`, `download_media`, `get_media_info`.
- **Contacts:** `list_contacts`, `search_contacts`.
- **Offline Cache:** `check_cache_health`, `search_cached_messages`, `sync_chat_cache`.

All mutations remain gated behind fail-closed security (`TELEGRAM_SEND_ENABLED=false` by default).

## Core tier

Set `TELEGRAM_MCP_TIER=core` for an extended read-only surface (36 tools) covering deeper account diagnostics, folders, member lists, and administrative inspection without mutation tools.

## Standard tier

Set `TELEGRAM_MCP_TIER=standard` only when common message and media sends are needed. Set `TELEGRAM_SEND_ENABLED=true` separately; the tier controls visibility, while the mutation flag controls execution.

## Full compatibility tier

Set `TELEGRAM_MCP_TIER=full` to expose all upstream tools (129 tools), including administrative and destructive operations. For those operations, also set `TELEGRAM_DESTRUCTIVE_ENABLED=true` and use a dedicated Telegram account where practical.

## Streamable HTTP

Run a long-lived local process with `MCP_TRANSPORT=http`, `MCP_HOST=127.0.0.1`, and `MCP_PORT=8765`. Keep the port bound to localhost unless a reverse proxy supplies authentication, TLS, allowed hosts, and allowed origins. Never expose the unauthenticated endpoint directly to the public internet.
