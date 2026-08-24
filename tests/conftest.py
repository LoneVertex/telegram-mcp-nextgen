"""Shared pytest setup for import-time Telegram configuration."""

import os

os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "dummy_hash")
os.environ.setdefault("TELEGRAM_SESSION_NAME", "test_session")
os.environ.setdefault("TELEGRAM_SEND_ENABLED", "true")
os.environ.setdefault("TELEGRAM_DESTRUCTIVE_ENABLED", "true")
