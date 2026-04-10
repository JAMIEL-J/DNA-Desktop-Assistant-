# 1. stdlib
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 2. internal
from config import DB_PATH

logger = logging.getLogger('dna.memory')

def init_db():
    """Initializes the SQLite database with the required tables."""
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Conversation table for LLM context
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT
                )
            ''')
            
            # Command log table for auditing and tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS command_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    command TEXT,
                    result TEXT,
                    status TEXT
                )
            ''')
            
            # Preferences table for learning system
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')
            
            # Aliases table for learning system
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aliases (
                    alias TEXT PRIMARY KEY,
                    target TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.commit()
            logger.info("SQLite memory initialized at %s", DB_PATH)
    except Exception as e:
        logger.error("Failed to initialize SQLite memory: %s", e)

def log_command(command: str, result: str, status: str = 'success'):
    """Log a voice command and its outcome."""
    try:
        if not command:
            return
            
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute(
                'INSERT INTO command_log (timestamp, command, result, status) VALUES (?, ?, ?, ?)',
                (timestamp, command, result, status)
            )
    except Exception as e:
        logger.error("Failed to log command: %s", e)

def save_preference(key: str, value: str):
    """Save a user preference key-value pair into SQLite."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            timestamp = datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)',
                (key.lower().strip(), str(value).strip(), timestamp)
            )
            conn.commit()
    except Exception as e:
        logger.error("Failed to save preference: %s", e)

def get_preference(key: str) -> str | None:
    """Retrieve a single preference from SQLite, or None if not found."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM preferences WHERE key = ?', (key.lower().strip(),))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error("Failed to get preference: %s", e)
        return None

def get_preferences() -> dict:
    """Retrieve all mapped preferences from SQLite."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM preferences')
            return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        logger.error("Failed to get preferences: %s", e)
        return {}

def save_alias(alias: str, target: str):
    """Save an application or folder alias mapping into SQLite."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            timestamp = datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO aliases (alias, target, updated_at) VALUES (?, ?, ?)',
                (alias.lower().strip(), str(target).strip(), timestamp)
            )
            conn.commit()
    except Exception as e:
        logger.error("Failed to save alias: %s", e)

def get_aliases() -> dict:
    """Retrieve all learned aliases mapped to their target paths."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT alias, target FROM aliases')
            return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        logger.error("Failed to get aliases: %s", e)
        return {}

