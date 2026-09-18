"""Shared pytest setup for import-time Telegram configuration."""

import os

import dotenv

# Disable loading local .env during test execution to guarantee clean, isolated, reproducible test runs
dotenv.load_dotenv = lambda *args, **kwargs: False

# Clean any suffixed account session keys that may have been passed via shell environment
for k in list(os.environ.keys()):
    if k.startswith("TELEGRAM_SESSION_STRING_") or k.startswith("TELEGRAM_SESSION_NAME_"):
        del os.environ[k]

os.environ["TELEGRAM_ACCOUNTS"] = ""
os.environ["TELEGRAM_ACCOUNTS_JSON"] = ""
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "dummy_hash")
os.environ.setdefault("TELEGRAM_SESSION_NAME", "test_session")
os.environ.setdefault("TELEGRAM_SEND_ENABLED", "true")
os.environ.setdefault("TELEGRAM_DESTRUCTIVE_ENABLED", "true")
