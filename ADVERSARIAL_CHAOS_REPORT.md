# Adversarial Chaos Audit and Hardening Report

**Author:** LoneVertex
**Date:** 2026-08-24
**Target:** `chigwell/telegram-mcp` compatibility checkout, hardened next-generation tree at version 4.0.0
**Audit mode:** Offline, hostile-runtime testing with mocked Telethon clients and local SQLite/filesystem fixtures. No Telegram account was authenticated and no external mutation was performed.

## Scope and disposition

This pass treated the MCP boundary, MTProto adapter behavior, asynchronous iteration, SQLite persistence, media paths, and error surfaces as hostile. The audit executed 14 dedicated adversarial pytest cases covering FloodWait ceilings, uncertain network failures, mutation replay, FTS5 syntax fuzzing, malformed limits and IDs, MCP error redaction, path traversal, atomic media bounds, concurrent SQLite reads/writes, cancellation/resume behavior, and retained-photo persistence. The full repository suite then passed with **377 tests**.

Five production weaknesses were confirmed. All five received shared-layer or inherited-adapter patches and reproducible regression tests. The residual symlink TOCTOU risk in legacy path operations remains **NOT VERIFIED as race-free** because static path validation cannot make a later independent open operation descriptor-atomic. Live MTProto authentication, live RPC behavior, Docker execution, and cross-process filesystem races were not attempted.

## Verification matrix

| Area | Result | Evidence |
|---|---|---|
| Dedicated chaos tests | **VERIFIED** | 14 passed in `tests/test_adversarial_chaos.py` |
| Complete repository regression | **VERIFIED** | 377 passed, 2 known third-party warnings |
| Focused coverage | **VERIFIED** | 97.34% total for `telegram_mcp.config`, `telegram_mcp.core`, and `telegram_mcp.db`; threshold 95% |
| Typed shared layers | **VERIFIED** | mypy passed for `telegram_mcp/core` and `telegram_mcp/db` |
| Syntax gate | **VERIFIED** | Ruff E9 passed on all changed production/test files |
| Full Ruff policy | **PARTIAL** | Existing inherited repository lint debt remains; no broad formatter rewrite was applied to compatibility runtime code |
| Python compilation | **VERIFIED** | `compileall -q telegram_mcp tests` passed |
| Packaging | **VERIFIED** | Wheel and sdist rebuilt successfully; SHA-256 recorded below |
| Dependency vulnerabilities | **VERIFIED** | `pip-audit` reported no known vulnerabilities; local project skipped because it is not on PyPI |
| Offline CLI help | **VERIFIED** | `python -m telegram_mcp --help` exited without network/client startup when no invalid session string was supplied |
| Docker build/runtime | **BLOCKED** | Docker executable unavailable in the sandbox |
| Live Telegram authentication/RPC | **NOT VERIFIED** | Deliberately not attempted |
| Live sends/deletes/admin actions | **NOT VERIFIED** | Deliberately not attempted |

Final package hashes:

| Artifact | SHA-256 |
|---|---|
| `telegram_mcp-4.0.0-py3-none-any.whl` | `5644cc1fe68ec58859314e1250362acee6a2ee84e6e363e0e928ab1b353e6bf4` |
| `telegram_mcp-4.0.0.tar.gz` | `7b222e568875d89666e7b62bbac93b9c10ccdd0b3f0c951064775c8077e883f0` |

## Confirmed weaknesses and patches

### [SEVERITY: HIGH] — Whole-operation retries could replay mutations after uncertain delivery

**Target Location:** `telegram_mcp/core/retry.py` -> `run_with_policy()`, lines 19–53; `telegram_mcp/runtime.py` -> `with_account()`, lines 567–594.

**Attack / Chaos Scenario:** A mutation tool invokes an MTProto write, Telegram applies the write, and the client receives a timeout or connection reset before receiving a response. The wrapper sees a retryable network exception and invokes the complete tool function again. A send operation can therefore broadcast duplicates, while an administrative or destructive operation can repeat an irreversible side effect.

**Failure Mechanism:** The original retry primitive had no idempotence distinction. It retried both FloodWait and transient network exceptions around the entire decorated coroutine. The wrapper applied that policy to writes and reads alike, so it could not distinguish a safe re-fetch from an uncertain side effect.

**Reproducible Chaos Test Case:** The complete regression is in `tests/test_adversarial_chaos.py::test_mutation_is_not_retried_after_uncertain_network_failure`. Its essential runnable command is:

```bash
cd /home/ubuntu/work/telegram-mcp-nextgen/nextgen
PYTHONPATH=. TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=dummy_hash \
TELEGRAM_SESSION_NAME=test_session TELEGRAM_SEND_ENABLED=true \
/home/ubuntu/work/telegram-mcp-nextgen/.venv-upstream/bin/python -m pytest -q \
tests/test_adversarial_chaos.py::test_mutation_is_not_retried_after_uncertain_network_failure
```

The test decorates a coroutine with `with_account(readonly=False)`, raises `ConnectionError("connection dropped after RPC write")`, and asserts that the invocation count is exactly one. Before the patch, the configured retry budget caused repeated invocations.

**Production Hardening Patch:** `run_with_policy()` now accepts explicit `retry_flood` and `retry_network` controls. The single-account mutation path passes both as `False`; the read-only path and read-only multi-account fan-out retain bounded retries. Mutation gates remain fail-closed before the operation is invoked.

**Verification Result:** **VERIFIED.** The regression passes, the complete suite passes with 377 tests, and existing read retry tests continue to pass. No live mutation was attempted.

### [SEVERITY: HIGH] — Interrupted cache synchronization lost all durable progress

**Target Location:** `telegram_mcp/tools/cache.py` -> `sync_chat_cache()`, lines 103–135; related persistence uses `telegram_mcp/db/repository.py` -> `checkpoint()`, lines 63–72.

**Attack / Chaos Scenario:** A remote async message iterator yields 55 messages and is then cancelled or fails with FloodWait/network loss. The caller expects the next incremental run to resume near the last durable message, not start over. The original implementation accumulated every row in a Python list and wrote the chat, messages, and checkpoint only after the async iterator completed successfully.

**Failure Mechanism:** Cancellation or any exception before the end of iteration discarded the entire in-memory list. Because the checkpoint was written last, the database retained neither message rows nor progress. A retry restarted from the old checkpoint, increasing network load and memory pressure and repeatedly exposing the same failure window.

**Reproducible Chaos Test Case:** The complete regression is in `tests/test_adversarial_chaos.py::test_sync_checkpoint_survives_cancellation_and_resumes_from_last_batch`. Run it with:

```bash
cd /home/ubuntu/work/telegram-mcp-nextgen/nextgen
PYTHONPATH=. TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=dummy_hash \
TELEGRAM_SESSION_NAME=test_session TELEGRAM_SEND_ENABLED=true \
/home/ubuntu/work/telegram-mcp-nextgen/.venv-upstream/bin/python -m pytest -q \
tests/test_adversarial_chaos.py::test_sync_checkpoint_survives_cancellation_and_resumes_from_last_batch
```

The test interrupts at message 56 and asserts that 50 rows and checkpoint 50 survive. It then runs an incremental resume and asserts that the client receives `min_id=50`, the final checkpoint is 60, and the archive contains 60 rows.

**Production Hardening Patch:** `sync_chat_cache()` now upserts the chat before iteration, commits bounded batches of at most 50 rows, and advances the monotonic checkpoint after each committed batch. The in-memory working set is limited to the current batch. Cancellation between batches leaves the last committed batch and checkpoint intact; a later incremental sync resumes from that checkpoint.

**Verification Result:** **VERIFIED.** The cancellation/resume regression passes, and the full 377-test suite passes. The design is bounded for the configured sync window; live 5,000-message Telegram behavior remains not verified.

### [SEVERITY: HIGH] — Same-process concurrent SQLite operations could fail with `database is locked`

**Target Location:** `telegram_mcp/db/database.py` -> `Database.connection()`, lines 17–46; exercised by `telegram_mcp/db/repository.py` -> `upsert_messages()`, lines 40–61.

**Attack / Chaos Scenario:** Schedule several `asyncio.to_thread()` message writers against one cache database while readers query the latest messages. WAL mode permits concurrent readers but SQLite still has one writer at a time. Hostile scheduling can overlap transaction start and writer acquisition.

**Failure Mechanism:** Each repository call opened a new connection and began a transaction. The finite busy timeout did not guarantee that same-process writers would serialize before a lock error escaped. A single contention failure could abort a cache sync or leave the MCP request in an error state even though the transaction itself was otherwise valid.

**Reproducible Chaos Test Case:** The complete regression is in `tests/test_adversarial_chaos.py::test_concurrent_cache_reads_and_writes_are_consistent`. Run it with:

```bash
cd /home/ubuntu/work/telegram-mcp-nextgen/nextgen
PYTHONPATH=. TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=dummy_hash \
TELEGRAM_SESSION_NAME=test_session \
/home/ubuntu/work/telegram-mcp-nextgen/.venv-upstream/bin/python -m pytest -q \
tests/test_adversarial_chaos.py::test_concurrent_cache_reads_and_writes_are_consistent
```

The pre-fix run failed with `sqlite3.OperationalError: database is locked` during `upsert_messages()` under five concurrent writers and ten concurrent readers.

**Production Hardening Patch:** `Database` now owns a process-local reentrant transaction lock and acquires it around connection creation, `BEGIN`, transaction work, commit/rollback, and close. WAL, foreign keys, synchronous mode, and the configured SQLite busy timeout remain enabled. This serializes transactions originating from the same `Database` instance while retaining the database’s WAL behavior for external readers/processes.

**Verification Result:** **VERIFIED for same-process contention.** The regression passes, SQLite/FTS5 integrity checks pass, and the full suite passes. Cross-process lock behavior and network filesystem semantics are not verified.

### [SEVERITY: HIGH] — Hostile FTS5 search input could escape normalization and crash the repository

**Target Location:** `telegram_mcp/db/repository.py` -> new `_fts_match()`, lines 12–20, and `MessageRepository.search()`, lines 78–89.

**Attack / Chaos Scenario:** Submit cache queries containing NUL bytes, unmatched quotes, FTS operators, backslashes, parentheses, RTL text, or emoji. An LLM-generated argument can contain these values without intentional user input.

**Failure Mechanism:** The original implementation removed double quotes but still embedded arbitrary tokens into a quoted FTS5 `MATCH` expression. A NUL token generated an SQLite FTS5 `unterminated string` error. The error could escape any path that did not use the typed error boundary and exposed a database failure instead of a bounded search result.

**Reproducible Chaos Test Case:** The complete regression is in `tests/test_adversarial_chaos.py::test_fts_adversarial_queries_never_escape_or_crash`. Run it with:

```bash
cd /home/ubuntu/work/telegram-mcp-nextgen/nextgen
PYTHONPATH=. TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=dummy_hash \
TELEGRAM_SESSION_NAME=test_session \
/home/ubuntu/work/telegram-mcp-nextgen/.venv-upstream/bin/python -m pytest -q \
tests/test_adversarial_chaos.py::test_fts_adversarial_queries_never_escape_or_crash
```

The pre-fix case failed for `query="\x00"` with `sqlite3.OperationalError: unterminated string`.

**Production Hardening Patch:** `_fts_match()` now drops non-printable characters, doubles embedded double quotes for FTS5 phrase safety, wraps normalized tokens as quoted terms, joins terms with `AND`, and returns an empty expression for input that normalizes to no tokens. SQL values remain parameterized.

**Verification Result:** **VERIFIED.** The fuzz regression passes for operators, unmatched syntax, NUL/control input, backslashes, RTL text, and emoji. The MCP-level limit/offset boundary cases also pass without raw SQL leakage.

### [SEVERITY: MEDIUM] — Retained photo output used a non-atomic direct write

**Target Location:** `telegram_mcp/tools/media.py` -> `open_photo()`, original direct save at lines 576–586; patched save path at lines 586–594.

**Attack / Chaos Scenario:** Call `open_photo(save_path=...)` while the process is interrupted, the filesystem fills, or a concurrent consumer opens the destination. The original `Path.write_bytes()` truncates the destination before writing the new bytes, so an interruption can leave a corrupt partial file.

**Failure Mechanism:** Direct in-place writing had no temporary-file, fsync, atomic-replace, or cleanup boundary. It also bypassed the centralized streaming primitive’s byte-bound and nested-symlink checks. The issue was isolated to the legacy adapter’s retained-photo path; the newer primitive was already atomic.

**Reproducible Chaos Test Case:** The complete regression is in `tests/test_adversarial_chaos.py::test_open_photo_uses_atomic_save_primitive`, with primitive cleanup and size-failure behavior covered by `test_atomic_stream_is_bounded_and_cleans_temp_file`. Run it with:

```bash
cd /home/ubuntu/work/telegram-mcp-nextgen/nextgen
PYTHONPATH=. TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=dummy_hash \
TELEGRAM_SESSION_NAME=test_session \
/home/ubuntu/work/telegram-mcp-nextgen/.venv-upstream/bin/python -m pytest -q \
tests/test_adversarial_chaos.py::test_open_photo_uses_atomic_save_primitive
```

The regression invokes the real unwrapped `open_photo()` body with offline photo helpers, intercepts the persistence primitive, and asserts that the existing destination is not directly rewritten by `Path.write_bytes()`.

**Production Hardening Patch:** `open_photo()` now supplies a one-chunk async stream to `atomic_write_bytes(kept_path.parent, kept_path.name, ..., max_bytes=settings.max_media_download_bytes)`. The primitive creates a 0600 temporary file, bounds the stream, flushes and fsyncs, atomically replaces the destination, and removes temporary state on any `BaseException`.

**Verification Result:** **VERIFIED.** The atomic-save regression, all media/path tests, and the complete 377-test suite pass. Live Telethon media download behavior was not attempted.

## Verified protections and residual risks

The following hostile cases did not produce confirmed new weaknesses in the current tree: cancellation propagation through `safe_tool`; secret omission from settings diagnostics and unknown-error responses; traversal, absolute-path escape, NUL path, nested symlink, MIME, size, and temporary-file cleanup checks; mutation denial when write settings are disabled; negative or zero cache search limits and offsets; bounded FloodWait handling for a 420-second wait above the configured ceiling; and concurrent same-process lock cleanup as covered by the existing core tests.

A static `resolve()` plus symlink-component check cannot by itself close a TOCTOU race if a legacy adapter validates a path and later asks another library to open it. The new `atomic_write_bytes()` path narrows this risk for new retained-file writes, but inherited Telethon download paths still perform library-managed filesystem operations after validation. A descriptor-relative `openat`/`O_NOFOLLOW` design or equivalent Telethon-supported file descriptor API would be required to claim race-free behavior; that was not introduced without changing compatibility-sensitive adapter semantics.

Import-time client discovery remains compatibility-sensitive. An invalid non-empty Telethon session string can fail during module import before CLI `--help` reaches its early-return branch; the verified help smoke deliberately omitted the invalid session string. This is an operational limitation, not a live credential disclosure, and it should be addressed in a future lazy-import refactor rather than by weakening validation.

The inherited adapter surface still contains broad exception formatting and full-repository Ruff findings. The new typed error boundary and the adversarial tests prevent leakage on the hardened paths, but complete uniform error wrapping of all 125 compatibility tools remains **PARTIAL**. No raw credential was observed in the final tracked-source scan.

## Reproduction and artifact index

The patched source tree contains the complete runnable chaos module at `tests/test_adversarial_chaos.py`. The relevant production files are `telegram_mcp/core/retry.py`, `telegram_mcp/runtime.py`, `telegram_mcp/tools/cache.py`, `telegram_mcp/db/database.py`, `telegram_mcp/db/repository.py`, `telegram_mcp/tools/media.py`, and `telegram_mcp/core/security.py`. The older summary remains in `AUDIT_REPORT.md`; this document is the authoritative adversarial report for this pass.

## References

[1]: https://github.com/chigwell/telegram-mcp "Upstream Telegram MCP repository"
[2]: https://docs.telethon.dev/ "Telethon documentation"
[3]: https://sqlite.org/wal.html "SQLite Write-Ahead Logging documentation"
[4]: https://sqlite.org/fts5.html "SQLite FTS5 documentation"
[5]: https://modelcontextprotocol.io/ "Model Context Protocol documentation"
