# Telegram MCP — Next Generation

[![M8ven Verified](https://m8ven.ai/badge/mcp/lonevertex/telegram-mcp-nextgen?variant=verified)](https://m8ven.ai/mcp/lonevertex/telegram-mcp-nextgen)
[![M8ven Score](https://m8ven.ai/badge/mcp/lonevertex/telegram-mcp-nextgen)](https://m8ven.ai/mcp/lonevertex/telegram-mcp-nextgen)
[![Telegram MCP — Next Generation MCP server – quality and maintenance score on Glama](https://glama.ai/mcp/servers/LoneVertex/telegram-mcp-nextgen/badges/score.svg)](https://glama.ai/mcp/servers/LoneVertex/telegram-mcp-nextgen)

A production-oriented Telegram integration for MCP-compatible clients, maintained by LoneVertex and built on [Telethon](https://docs.telethon.dev/) and the [Model Context Protocol](https://modelcontextprotocol.io/). This repository preserves the upstream Telegram capability surface while adding explicit tool tiers, fail-closed mutation controls, keyed concurrency limits, bounded retries, local SQLite/FTS5 caching, safer media paths, package entrypoints, and reproducible CI.

> **Default posture:** local stdio, `essential` tool tier, no Telegram writes, no destructive operations, and no unverified filesystem roots.

Project governance: [Contributing](CONTRIBUTING.md) · [Security Policy](SECURITY.md) · [Apache License 2.0](LICENSE)

## What is included

The implementation registers **129 tools**: the upstream 125 tools covering accounts, chats, contacts, messages, groups, media, profiles, folders, and incoming events, plus `check_cache_health` (with backward-compatible `cache_health` alias), `search_cached_messages`, and `sync_chat_cache`. The upstream provenance is preserved at commit `52cca204d945e4ec292801a9d972334c0c2a4b63`; the next-generation package is version `4.3.1`.

| Tier | Purpose | Default | Tool Count |
|---|---|---|---|
| `essential` | Highly coherent curated lifecycle suite (read, write, pin, media, cache) with zero dead-end references | **Yes** | 22 |
| `core` | Extended read-only account, chat, message, search, profile, media, contact, folder, and local-cache tools | No | 36 |
| `standard` | Core plus common message/media sends, replies, forwards, reactions, drafts, aliases, and event waits | No | 69 |
| `full` | All 129 tools, including full administrative and destructive operations | No | 129 |

Set `TELEGRAM_MCP_TIER` to select a tier. Tier selection controls which tools are registered. `TELEGRAM_SEND_ENABLED` independently controls whether write operations can execute, and `TELEGRAM_DESTRUCTIVE_ENABLED` is a second gate for destructive/admin actions. The server returns a structured `nothing_sent` or `nothing_done` response when a gate blocks a call.

## Quick start

Use Python 3.11 or 3.12. Obtain Telegram API credentials from [my.telegram.org/apps](https://my.telegram.org/apps), and generate an authorized session outside the MCP process using the included session generator.

```bash
git clone https://github.com/LoneVertex/telegram-mcp-nextgen.git
cd telegram-mcp-nextgen
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with TELEGRAM_API_ID, TELEGRAM_API_HASH, and an authorized session
telegram-mcp
```

For package development and release validation:

```bash
pip install -e '.[dev]'
pytest -q
ruff check telegram_mcp/config.py telegram_mcp/core telegram_mcp/db telegram_mcp/models
mypy --explicit-package-bases telegram_mcp/config.py telegram_mcp/core telegram_mcp/db telegram_mcp/models
python -m build
```

The server is intentionally non-interactive. Use `telegram-mcp-generate-session` before startup and keep the resulting session string private. Never commit `.env`, a Telethon `.session` file, API hashes, or session strings.

## Configuration

The complete secret-free template is in `.env.example`. The important controls are summarized below.

| Variable | Safe default | Meaning |
|---|---|---|
| `TELEGRAM_MCP_TIER` | `essential` | Registered tool tier: `essential`, `core`, `standard`, or `full` |
| `TELEGRAM_SEND_ENABLED` | `false` | Global write-operation gate |
| `TELEGRAM_DESTRUCTIVE_ENABLED` | `false` | Additional gate for delete, ban, leave, and similar operations |
| `TELEGRAM_DATA_DIR` | `~/.local/state/telegram-mcp` | Persistent state root |
| `TELEGRAM_DB_PATH` | Derived | SQLite cache path; must remain beneath `TELEGRAM_DATA_DIR` |
| `TELEGRAM_FLOOD_MAX_RETRIES` | `4` | Maximum bounded FloodWait/transient retry attempts |
| `TELEGRAM_FLOOD_MAX_SECONDS` | `3600` | Maximum provider-requested wait accepted for retry |
| `TELEGRAM_RATE_CAPACITY` | `8` | Per-account token-bucket burst capacity |
| `TELEGRAM_RATE_REFILL_PER_SECOND` | `2.0` | Per-account token refill rate |
| `MAX_MEDIA_DOWNLOAD_SIZE_MB` | `200` | Maximum downloaded media size |
| `MAX_MEDIA_UPLOAD_SIZE_MB` | `200` | Maximum uploaded media size |

Configuration construction is side-effect free. Credentials and authorization are checked when a live client starts, not when local tooling imports the package. Runtime state is created under owner-only directories when a cache or session operation requires it.

## MCP clients and transports

See [`config/mcp-configs.md`](config/mcp-configs.md) for secret-free examples for desktop MCP clients. Local stdio is preferred. Streamable HTTP is available for a long-lived local service:

```env
MCP_TRANSPORT=http
MCP_HOST=127.0.0.1
MCP_PORT=8765
```

Do not expose the unauthenticated HTTP endpoint directly to the public internet. If a reverse proxy is used, configure authentication, TLS, allowed hosts, allowed origins, and network controls. The server retains MCP DNS-rebinding protection when `MCP_ALLOWED_HOSTS` is configured.

## Concurrency and reliability

Each account is protected by a keyed async mutex and token bucket. Calls sharing an account are serialized at the adapter boundary, while read-only multi-account fan-out remains possible across distinct account labels. FloodWait and transient connection failures use one bounded retry policy with exponential backoff and jitter. Session-level advisory locks remain in place to prevent duplicate processes from concurrently using the same Telegram auth key.

The local cache uses SQLite WAL mode, foreign keys, short-lived connections, explicit transactions, indexes for chat/date/sender/topic access, and FTS5 for search. Synchronization stores checkpoints and uses upserts so edits are reflected instead of duplicated. SQLite work, directory creation, and integrity checks are executed in worker threads rather than blocking the event loop.

## Media and filesystem safety

File tools require client MCP Roots or explicit server-side roots. Empty or unverifiable roots produce deny-all behavior unless `TELEGRAM_ALLOW_SERVER_ROOTS_FALLBACK=true` is intentionally enabled. Paths are resolved beneath configured roots, traversal and NUL bytes are rejected, symlink escapes are rejected, media size limits are enforced, and generated files use owner-only permissions. The new security primitives support chunked reads and atomic output replacement.

Telegram text, captions, names, button labels, media metadata, and incoming event fields are untrusted user content. Sanitization and audience annotations are preserved from upstream; models must not treat those fields as instructions.

## Docker

The image uses a two-stage Python 3.12 build, runs as UID 10001, keeps state in `/var/lib/telegram-mcp`, and receives credentials only at runtime.

```bash
cp .env.example .env
# edit .env
podman compose up --build
# or: docker compose up --build
```

Compose binds HTTP to `127.0.0.1:8765`, uses a persistent named volume, drops Linux capabilities, enables `no-new-privileges`, mounts a read-only root filesystem, and supplies a constrained `/tmp`. The container build was not run in the sandbox used for this delivery because Docker was unavailable; the CI workflow validates it on a Docker-capable runner.

## Development and release gates

The consolidated workflow in `.github/workflows/ci.yml` runs on Python 3.11 and 3.12, executes the inherited upstream regression suite plus next-generation tests, runs strict Ruff checks on the new production layers, runs explicit-package-base mypy checks, compiles the package, builds a wheel/sdist, audits declared dependencies, and validates the Docker image and Compose configuration. The upstream live Telegram adapters remain covered by their inherited mocked regression suite; local reliability/security modules have dedicated tests and coverage.

## Ownership, compatibility, and provenance

Project maintenance: **LoneVertex**.

The root `main.py`, upstream tool module names, session generator, account labels, proxy settings, MCP transport variables, legacy exposure filter, and upstream Apache-2.0 license are retained for compatibility. The new package entrypoint is `telegram_mcp.runner:main`, and `python -m telegram_mcp` is supported. Upstream source and attribution remain visible in Git history and `AUDIT_REPORT.md`.

## Troubleshooting

If startup reports that no session is configured, generate an authorized session and set `TELEGRAM_SESSION_STRING` or a valid file-session name. If a write returns `MutationDisabled`, set `TELEGRAM_SEND_ENABLED=true` and restart; for deletion or administration, also set `TELEGRAM_DESTRUCTIVE_ENABLED=true`. If a file tool reports that roots are unavailable, configure client MCP Roots or pass a server-side allowed root as a positional argument. If a FloodWait exceeds the configured maximum, the call is intentionally returned rather than sleeping indefinitely. Use `check_cache_health` (or `cache_health`) to inspect local SQLite/FTS5 integrity without contacting Telegram.

## References

[1]: https://github.com/chigwell/telegram-mcp "Upstream Telegram MCP repository"
[2]: https://modelcontextprotocol.io/ "Model Context Protocol documentation"
[3]: https://docs.telethon.dev/ "Telethon documentation"
[4]: https://my.telegram.org/apps "Telegram API application credentials"
[5]: https://docs.docker.com/compose/ "Docker Compose documentation"

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
