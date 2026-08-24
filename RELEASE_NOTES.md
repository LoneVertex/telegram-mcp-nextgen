# Release Notes

## 4.0.1 — CI and publication maintenance

This patch release keeps the Telegram MCP runtime and 128-tool compatibility surface unchanged while correcting public-release automation. GitHub Actions now installs the repository in editable mode before collecting tests, and the typed filesystem helper no longer contains a redundant cast that failed the CI type gate.

The release also carries the public-repository metadata, contribution policy, security policy, sanitized documentation, and the verified adversarial hardening from 4.0.0. The default posture remains local stdio, the `core` tier, disabled writes, disabled destructive operations, and deny-by-default filesystem roots.

The full local regression suite passed with 377 tests. The adversarial suite passed with 14 tests, focused next-generation coverage was 97.34% against a 95% threshold, typed shared-layer checks passed, the package built successfully, and the dependency audit reported no known vulnerabilities. Live Telegram behavior and Docker execution remain outside this release’s offline verification scope.

## 4.0.0 — Initial public release

The initial public release introduced the next-generation tool tiers, fail-closed mutation controls, account-keyed concurrency limits, bounded retries, SQLite WAL/FTS5 caching, resumable cache synchronization, safer media paths, typed settings, package entrypoints, CI, Docker/Compose configuration, and adversarial regression coverage.
