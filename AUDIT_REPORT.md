# Next-Generation Telegram MCP Audit Report

**Author:** LoneVertex
**Date:** 2026-08-24
**Scope:** `chigwell/telegram-mcp` at commit `52cca204d945e4ec292801a9d972334c0c2a4b63`, compared with the hardened `custom-telegram-mcp` reference and upgraded in an isolated working copy.

## Executive summary

The upstream repository is active, Apache-2.0 licensed, and functionally broad: the audited revision registers 125 MCP tools across accounts, chats, contacts, events, folders, groups, media, messages, and profile modules. Its inherited 335-test suite passed offline with 92.68% configured coverage, but capability breadth was concentrated in a 1,823-line runtime with import-time environment/client discovery, distributed retries, incomplete uniform mutation gating, synchronous media writes in async paths, and CI checks that did not cover the new infrastructure. The upgrade preserves upstream modules and compatibility paths while adding a typed configuration layer, `core`/`standard`/`full` tool tiers, fail-closed write gates, keyed account serialization, token-bucket rate limiting, centralized bounded retry policy, SQLite WAL/FTS5 cache storage, resumable cache synchronization, safer media bounds, package entrypoints, Docker/Compose hardening, and a consolidated least-privilege CI workflow.

The resulting working copy registers 129 tools, passes the inherited suite plus the adversarial chaos suite, and passes the focused 95% coverage gate for the new configuration/core/database/model layers. The adversarial pass confirmed and patched unsafe mutation replay, whole-sync checkpoint loss, FTS5 syntax failure on hostile input, and same-process SQLite lock contention. Package building and the offline CLI help path are verified; live Telegram authentication, live mutation behavior, and Docker image execution remain intentionally unverified in the sandbox.

## Baseline evidence

| Check | Result | Evidence |
|---|---|---|
| Upstream revision | **VERIFIED** | `52cca204d945e4ec292801a9d972334c0c2a4b63` on `main` |
| Upstream tool decorators | **VERIFIED** | 125 upstream registrations; 129 after local cache tools (including check_cache_health) |
| Upstream tests | **VERIFIED** | 335 passed offline before changes |
| Upstream configured coverage | **VERIFIED** | 92.68% for `runtime`, `main`, and `sanitize` |
| Upstream Black / critical Flake8 | **VERIFIED** | Passed in the isolated baseline environment |
| External live Telegram | **NOT RUN** | No account/session was authenticated or mutated |

## Findings and remediation

| ID | Severity | Finding | Remediation status |
|---|---|---|---|
| UP-001 | High | Import-time credential conversion and client discovery made local imports depend on live configuration. | **FIXED** — typed settings validate without authenticating; discovery has a silent import mode and runtime startup still fails clearly when no session exists. |
| UP-002 | High | Runtime concentrated lifecycle, storage, path security, aliases, logging, and MCP setup in one large module with wildcard compatibility imports. | **PARTIAL/FIXED** — new `config`, `core`, `db`, and `models` layers are explicit; legacy runtime remains for upstream tool compatibility. |
| UP-003 | High | No uniform per-account in-process mutex/rate limiter covered every account-scoped tool invocation. | **FIXED** — `KeyedLockManager` and per-account `TokenBucket` are applied by `with_account`. |
| UP-004 | High | FloodWait handling was distributed across tools and connection startup. | **FIXED** — account-scoped calls use centralized bounded retry/backoff with jitter and configured ceilings. |
| UP-005 | High | Error/log handling was broad and could expose technical details. | **FIXED/PARTIAL** — new typed error conversion redacts unknown failures; legacy technical logs remain local for compatibility. |
| UP-006 | Medium | Photo bytes were written synchronously in an async tool and downloaded media lacked a post-write size check. | **FIXED** — photo writes use worker threads and downloads are checked against the configured byte limit. |
| UP-007 | Medium | General upload policy did not have one strongly typed, centralized media limit. | **PARTIAL** — inherited root/size allowlists remain, while new typed media limits and streaming security primitives are available for next-generation paths. |
| UP-008 | High | Broad default exposure and distributed write controls increased accidental mutation risk. | **FIXED** — default tier is `core`; writes require `TELEGRAM_SEND_ENABLED=true`; destructive operations require a second flag. `full` remains an explicit compatibility opt-in. |
| UP-009 | Medium | Writable path creation and media operations lacked one central atomic streaming primitive. | **FIXED/PARTIAL** — new `confined_path`, `atomic_write_bytes`, chunked reads, MIME checks, and symlink-component rejection are tested; legacy path wrappers remain for compatibility. |
| UP-010 | Medium | Some fallback branches returned raw exception text. | **PARTIAL** — new error taxonomy is redacted; inherited adapters still contain compatibility-formatted messages in a few branches. |
| UP-011 | Medium | Entity resolution and alias outcomes were spread through the runtime. | **PARTIAL** — upstream resolver behavior is preserved; future extraction can use the typed core boundaries without breaking aliases. |
| UP-012 | Medium | Dependency declarations had open ranges and two lockfile ecosystems. | **FIXED** — Consolidated to standard `pyproject.toml` and `requirements.txt` using bounded tested ranges; obsolete upstream `poetry.lock` removed to eliminate security advisory debt. |
| UP-013 | Medium | CI had duplicated workflows, weak lint enforcement, and no explicit top-level read permission. | **FIXED** — one `ci.yml` uses `permissions: contents: read`, concurrency cancellation, strict focused quality checks, package build, dependency audit, and Docker validation. |
| UP-014 | Medium | Docker defaults and workflows encouraged dummy runtime environment files. | **FIXED** — runtime-only secrets, non-root UID 10001, read-only filesystem, capability drop, no-new-privileges, localhost binding, and persistent state volume. |
| UP-015 | Medium | Configured coverage excluded most live tool adapters. | **PARTIAL** — inherited mocked suite covers the upstream adapters; focused new-layer coverage is enforced at 95% while live Telegram remains untested by design. |
| UP-016 | Low | Upstream identity and Apache-2.0 provenance needed preservation. | **FIXED** — license, authorship, source history, URLs, and provenance are retained and documented. |

## Implemented architecture

The `telegram_mcp.config` module provides side-effect-free Pydantic settings, secure path derivation, typed tier/mutation controls, bounded limits, and redacted diagnostics. `telegram_mcp.core` contains keyed locks, token-bucket rate limiting, retry/backoff policy, typed error conversion, path confinement, atomic streaming writes, a coordinator abstraction, and tier pruning. `telegram_mcp.db` provides schema initialization, WAL mode, foreign keys, FTS5 triggers, indexes, checkpoints, repository operations, migrations, and maintenance facades. `telegram_mcp.models` gives a typed boundary for normalized chat, message, and media records. The upstream runtime remains the compatibility adapter and now applies the new settings, controls, retries, mutation gates, and tier selection.

The local archive is deliberately bounded. `sync_chat_cache` stores an explicit message window and checkpoint; `search_cached_messages` uses parameterized FTS queries; `cache_health` checks SQLite/FTS5 integrity. All SQLite operations and potentially blocking filesystem writes are moved to worker threads in the new paths.

## Tool surface

| Surface | Count | Exposure |
|---|---:|---|
| Upstream capability tools | 125 | `full` tier; filtered by default |
| Local cache tools | 4 | `essential` / `core` tiers (`check_cache_health`, `cache_health`, `search_cached_messages`, `sync_chat_cache`) |
| Total registered in full mode | **129** | Compatibility surface |
| Essential tier observed | **22** | High-coherence conversational lifecycle subset |
| Core tier observed | **36** | Extended read/search/cache/admin-inspection subset |

## Verification evidence

| Gate | Status | Result |
|---|---|---|
| Full regression suite | **VERIFIED** | 377 passed offline, including 14 adversarial chaos tests |
| New core/storage/tier/adversarial tests | **VERIFIED** | 41 passed under focused coverage gate |
| Focused coverage | **VERIFIED** | 97.34%, threshold 95% |
| Adversarial chaos matrix | **VERIFIED** | FTS fuzzing, mutation replay, cancellation/resume, SQLite contention, path/media bounds, error redaction, and input-boundary cases executed |
| Ruff syntax gate | **VERIFIED** | No E9 syntax diagnostics in changed production/test files; full historical Ruff run still reports inherited debt |
| Focused mypy | **VERIFIED** | No issues in `telegram_mcp/core` and `telegram_mcp/db`; MCP decorator surface remains SDK-untyped |
| Python compilation | **VERIFIED** | `compileall` passed |
| Wheel and sdist build | **VERIFIED** | Valid wheel and sdist built cleanly (version progression from v4.0.0 to v4.2.0) |
| Offline CLI help | **VERIFIED** | Source-tree `python -m telegram_mcp --help` exits without network/client startup |
| Dependency audit | **VERIFIED** | `pip-audit` found no known vulnerabilities; local project is not published on PyPI and was skipped |
| Docker build | **BLOCKED** | Docker is unavailable in the sandbox; CI contains the build gate |
| Live Telegram authentication | **NOT VERIFIED** | Intentionally not attempted |
| Live sending/deletion/admin operations | **NOT VERIFIED** | Intentionally not attempted |

## Known limitations and release notes

The inherited live adapter layer is intentionally not rewritten wholesale because its 125-tool public surface is compatibility-sensitive. It still contains broad exception formatting and runtime helpers that are not under the focused strict-mypy scope, and a full-repository Ruff run reports inherited lint debt; the changed chaos paths have a syntax-only lint gate. The provenance guard remains strict by default; `TELEGRAM_MCP_ALLOW_INSTALLED=true` is an explicit operator override for trusted locally built artifacts and is not required for source checkouts. The new retry policy forbids whole-operation retries for mutations, while read-only operations retain bounded retries. SQLite transactions are serialized per `Database` instance for same-process safety. The Docker build must be exercised on a Docker-capable runner before production deployment. A public release should choose one lockfile ecosystem and add mocked coverage for every side-effectful upstream adapter module before claiming complete whole-repository coverage.

No Telegram account data, messages, contacts, groups, media, or account settings were modified during this audit. All runtime tests used dummy credentials and mocked/offline data.

## References

[1]: https://github.com/chigwell/telegram-mcp "Upstream Telegram MCP repository"
[2]: https://modelcontextprotocol.io/ "Model Context Protocol documentation"
[3]: https://docs.telethon.dev/ "Telethon documentation"
[4]: https://my.telegram.org/apps "Telegram API application credentials"
[5]: https://docs.docker.com/compose/ "Docker Compose documentation"
