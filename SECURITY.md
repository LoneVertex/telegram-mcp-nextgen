# Security Policy

## Supported versions

Security fixes are applied to the latest published version of Telegram MCP Next Generation. Users should keep the package and its dependencies current within the supported Python 3.11 and 3.12 environments.

## Reporting a vulnerability

Please do not disclose exploitable details in a public issue. Use the repository’s private security reporting channel on GitHub when available. If private reporting is not available, open a minimal issue requesting a private contact method without including credentials, session data, personal identifiers, or a complete exploit.

Include the affected version or commit, a concise impact description, reproduction steps that use only synthetic local fixtures, and any proposed mitigation. Do not authenticate a Telegram account or perform sends, deletes, bans, administrative actions, or other external mutations while reproducing a report.

## Credential and session safety

Never commit `.env`, API hashes, session strings, Telethon session files, runtime databases, message exports, media containing personal data, or logs. Use the blank `.env.example` template and keep runtime state under owner-only directories. Rotate any credential that may have been exposed and report the exposure privately.

The default configuration is read-only and deny-by-default for mutation and filesystem-root operations. Do not enable write or destructive gates in shared environments without an explicit operational review.

## Disclosure process

Maintainers will acknowledge valid reports, assess impact, develop a fix with regression coverage, and coordinate release communication when disclosure is appropriate. The project will preserve reporter confidentiality unless disclosure is authorized or required by law.
