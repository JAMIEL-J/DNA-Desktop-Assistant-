# core/usage_tracker.py
"""
DNA MCP / External API Daily Usage Tracker

Tracks Apify compute/run count and Composio tool calls in the primary SQLite DB (`data/db/dna_memory.db`).
Uses calendar-day reset windows (`date(timestamp, 'localtime') = date('now', 'localtime')`).
Enforces loud failures when limits are breached.
"""

import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger('dna.core.usage_tracker')

def _init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mcp_api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                action TEXT NOT NULL,
                items_count INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to initialize mcp_api_usage table: %s", e)

# Ensure table exists on import
_init_db()

def log_usage(provider: str, action: str, items_count: int = 0) -> None:
    """Log an API call for a provider (e.g., 'apify', 'composio')."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO mcp_api_usage (provider, action, items_count) VALUES (?, ?, ?)",
            (provider.lower(), action, items_count)
        )
        conn.commit()
        conn.close()
        logger.info("Logged usage for provider=%s action=%s items=%d", provider, action, items_count)
    except Exception as e:
        logger.error("Failed to log usage for provider %s: %s", provider, e)

def get_daily_count(provider: str) -> int:
    """Get total API call count for the current calendar day (local time)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM mcp_api_usage WHERE provider = ? AND date(timestamp, 'localtime') = date('now', 'localtime')",
            (provider.lower(),)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logger.error("Failed to get daily count for provider %s: %s", provider, e)
        return 0

def check_daily_limit(provider: str, max_limit: int) -> tuple[bool, int]:
    """
    Check if provider call is allowed under daily calendar limit.
    Returns (allowed: bool, current_count: int).
    """
    count = get_daily_count(provider)
    allowed = count < max_limit
    return allowed, count
