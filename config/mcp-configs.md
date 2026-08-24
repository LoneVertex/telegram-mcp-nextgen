# MCP Client Configuration

The safest default is local stdio with `TELEGRAM_MCP_TIER=core` and write operations disabled. Store credentials in a process environment or a secret manager; do not put API hashes or session strings in client configuration files.

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
        "TELEGRAM_MCP_TIER": "core",
        "TELEGRAM_SEND_ENABLED": "false",
        "TELEGRAM_DESTRUCTIVE_ENABLED": "false"
      }
    }
  }
}
```

The positional path is an optional server-side allowed root for file tools. Client MCP Roots are preferred and an empty or unverifiable Roots response remains deny-all unless `TELEGRAM_ALLOW_SERVER_ROOTS_FALLBACK=true` is explicitly set.

## Standard tier

Set `TELEGRAM_MCP_TIER=standard` only when common message and media sends are needed. Set `TELEGRAM_SEND_ENABLED=true` separately; the tier controls visibility, while the mutation flag controls execution.

## Full compatibility tier

Set `TELEGRAM_MCP_TIER=full` to expose all upstream tools, including administrative and destructive operations. For those operations, also set `TELEGRAM_DESTRUCTIVE_ENABLED=true` and use a dedicated Telegram account where practical.

## Streamable HTTP

Run a long-lived local process with `MCP_TRANSPORT=http`, `MCP_HOST=127.0.0.1`, and `MCP_PORT=8765`. Keep the port bound to localhost unless a reverse proxy supplies authentication, TLS, allowed hosts, and allowed origins. Never expose the unauthenticated endpoint directly to the public internet.
