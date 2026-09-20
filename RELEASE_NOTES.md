# Release Notes

## 4.3.1 — Install Guard Artifact Provenance & Runtime Environment Fix

This patch release fixes local wheel distribution verification and guarantees runtime environment discovery:

- **Local Distribution Artifact Provenance:** Extended `install_guard._direct_url_is_explicit_source_install` to recognize `.whl` and `.tar.gz` packages built and installed from the local `dist/` directory, resolving false-positive `UnsafeInstallationError` during tool installations.
- **Environment Discovery Parity:** Configured `telegram_mcp.runtime` to explicitly load environment variables from `TELEGRAM_ENV_FILE` if present.
- **Continuous Integration Lint Coverage:** Expanded CI quality gate in `.github/workflows/ci.yml` to strictly lint `tests/test_install_guard.py`.
- **Regression Test Suite:** Added `test_install_guard_accepts_file_install_from_dist_artifact` in `tests/test_install_guard.py`, expanding the test suite to 535 unit tests.

## 4.3.0 — Anti-Koshary Codebase Hardening, Architectural Decoupling, and Cross-Platform Reliability

This minor release implements the full Anti-Koshary architectural hardening pass, eliminating security gating mismatches, N+1 RPC queries, and platform-specific concurrency locks while decoupling wire-format TLRequests and message presentation layers:

- **Destructive Security Parity:** Synchronized `_DESTRUCTIVE_TOOL_NAMES` with all 18 tools declaring `destructiveHint=True`. Removed non-destructive `unban_user` and added bidirectional parity test in `tests/test_server_coherence.py`.
- **N+1 RPC Elimination:** Batched reply message retrieval in `get_message_context` into a single MTProto vector query, eliminating latency bottlenecks during threaded inspection.
- **Cross-Platform Synchronization:** Replaced Linux-only `fcntl.flock` with `filelock.FileLock` in alias state mutation (`telegram_mcp/runtime.py`), closing concurrency bypasses on Windows. Declared `filelock` as an explicit production dependency.
- **Bounded Dialog Resolution:** Bound `get_contact_chats` dialog searches to 100 entries and resolved direct chats via immutable `contact.id` rather than fragile string username matching.
- **Execution Mode Ordering:** Ensured `_apply_exposed_tools_mode` runs prior to `apply_tool_tier` in `runner.py`, preventing unexpected `SystemExit` on tier-pruned tools.
- **Traversal Validation Hardening:** Hardened path boundary checks against NUL-byte injection attacks.
- **Custom TLRequest Modularization:** Decoupled binary wire structures (`GetForumTopicsRequest`, `CreateForumTopicRequest`) from `chats.py` into dedicated `telegram_mcp.core.tl_custom` with 100% test coverage.
- **Message Presentation Decoupling:** Promoted serialization and presentation helpers (`message_to_dict`, `format_message_line`, `get_reply_quote`, `get_media_label`) into `telegram_mcp.models.messages` with backward-compatible re-exports.
- **Expanded Test Suite:** Increased test suite to 534 unit tests with 96.63% test coverage across core modules.

## 4.2.0 — Server Coherence, Essential Tier, and Complete TDQS Optimization

This minor release elevates the Glama Server Coherence grade to Tier A, achieves complete TDQS compliance, eliminates all dangling cross-references, and introduces the `essential` tool tier:

- **Curated `essential` Tier (22 tools):** Introduced a balanced default tier with exactly 22 tools (<=25 penalty threshold), providing full conversational and media lifecycle (read, send, reply, edit, delete, pin, unpin, mark-as-read, file transfer, contact discovery, and offline cache) while preserving fail-closed safety (`TELEGRAM_SEND_ENABLED=false`).
- **100% Naming Consistency (`verb_noun`):** Renamed `cache_health` to `check_cache_health` to ensure 100% imperative verb adherence across tools, while preserving `cache_health` as a backward-compatible alias.
- **Eliminated Dead-End Tool References:** Cleaned up dangling cross-references in `TOOL_DESCRIPTIONS` pointing to non-existent tools (`set_privacy_settings`, `set_bot_commands`, `unpin_all_messages`, `get_gif_search`) and cross-tier unexposed tools, achieving zero broken references in every tier.
- **Automated Coherence Test Suite:** Added `tests/test_server_coherence.py` enforcing tool count limits, verb-noun naming uniformity, tier lifecycle completeness, and zero dangling tool references across all tiers.
- **Comprehensive Tool Parity:** Increased registered tool count to 129 tools with 100% parameter annotations and 525 passing unit tests.

## 4.1.2 — Tool Definition Quality Score (TDQS) certification, test isolation, and dependency modernization

This patch release hardens MCP tool schema definitions, completes test suite isolation, and modernizes continuous integration:

- **TDQS Tier A Certification:** Resolved parameter description behavioral transparency smell in `get_contact_chats` and removed redundant read-only echoes across 11 tools, elevating all 35 core tools to Glama TDQS Tier A.
- **Automated TDQS Regression Suite:** Added `tests/test_glama_and_tdqs.py` ensuring zero regressions in parameter schemas, required field clarity, and absence of echo antipatterns.
- **Test Environment Isolation:** Added autouse session fixture in `tests/conftest.py` guaranteeing multi-account `.env` variables cannot leak into unit test discovery.
- **Runtime Deprecation Elimination:** Updated `python-json-logger` imports in `telegram_mcp.runtime` to support modern `pythonjsonlogger.json` namespace without deprecation warnings.
- **CI Modernization:** Upgraded GitHub Actions workflow to Node 24 native action versions (`actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-artifact@v7`).
- **Dependency Refresh:** Updated `uv.lock` with latest compatible upstream releases for Telethon, MCP Python SDK, Pydantic, and Cryptography.

## 4.1.1 — Glama registry manifest, TDQS schema enrichment, and container inspection

This patch release adds full compatibility and quality verification for the Glama MCP registry:

- **Glama Server Manifest:** Added `glama.json` ownership verification manifest conforming to Glama server schema.
- **100% Parameter Schema Coverage (TDQS):** Implemented schema enrichment populating typed parameter descriptions across all 411 parameters and 128 tools, alongside human-readable tool titles satisfying `titleIsMeaningful`.
- **Sibling Tool Disambiguation:** Added explicit cross-tool guidance and boundary constraints across related tool families (`search_messages`, `search_global`, `search_cached_messages`, `sync_chat_history`, `sync_chat_cache`).
- **Headless Container Inspection Support:** Added unauthenticated inspection mode in `telegram_mcp.runner` allowing automated registry VMs to run MCP `initialize` and `tools/list` handshakes cleanly without credentials.
- **Container Path & Log Alignment:** Added unprivileged runtime log fallback to `settings.data_dir` and enabled `TELEGRAM_MCP_ALLOW_INSTALLED=1` in container manifests.

## 4.1.0 — 100% tool coverage and complete hint annotations

This minor release completes MCP tool metadata and unit test coverage across the entire 128-tool Telegram capability surface:

- **Complete MCP Tool Hint Annotations:** Every single tool across all 10 domain modules (`accounts`, `admin`, `cache`, `chats`, `contacts`, `events`, `folders`, `media`, `messages`, `profile`) now declares explicit boolean values for all 4 MCP tool hints: `readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint`.
- **100% Tool Test Coverage:** Added comprehensive coverage testing in `tests/test_all_tools_coverage.py`, asserting registration, schema generation, docstrings, and complete hints across all 128 tools (increasing the test suite to 506 passing tests).
- **Tool Export Parity:** Added `forward_messages` to `telegram_mcp.tools.messages.__all__` export list for full namespace completeness.
- **Test Session Safety:** Added an explicit cleanup fixture in `tests/test_session_pool.py` ensuring process-wide session locks are released during test suite teardown.
- **M8ven Trust Verification:** Integrated M8ven Verified and Trust Score badges in documentation.

## 4.0.1 — CI and publication maintenance

This patch release keeps the Telegram MCP runtime and 128-tool compatibility surface unchanged while correcting public-release automation. GitHub Actions now installs the repository in editable mode before collecting tests, and the typed filesystem helper no longer contains a redundant cast that failed the CI type gate.

The release also carries the public-repository metadata, contribution policy, security policy, sanitized documentation, and the verified adversarial hardening from 4.0.0. The default posture remains local stdio, the `core` tier, disabled writes, disabled destructive operations, and deny-by-default filesystem roots.

The full local regression suite passed with 377 tests. The adversarial suite passed with 14 tests, focused next-generation coverage was 97.34% against a 95% threshold, typed shared-layer checks passed, the package built successfully, and the dependency audit reported no known vulnerabilities. Live Telegram behavior and Docker execution remain outside this release’s offline verification scope.

## 4.0.0 — Initial public release

The initial public release introduced the next-generation tool tiers, fail-closed mutation controls, account-keyed concurrency limits, bounded retries, SQLite WAL/FTS5 caching, resumable cache synchronization, safer media paths, typed settings, package entrypoints, CI, Docker/Compose configuration, and adversarial regression coverage.
