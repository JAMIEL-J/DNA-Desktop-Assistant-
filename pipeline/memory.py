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
            conn.commit()
    except Exception as e:
        logger.error("Failed to log command: %s", e)
