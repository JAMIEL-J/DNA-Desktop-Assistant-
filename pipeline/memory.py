# 1. stdlib
import sqlite3
import logging
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# 2. internal
from config import DB_PATH

logger = logging.getLogger('dna.memory')

PERSISTED_SESSION_KEYS = [
    'active_file',
    'active_app',
    'work_context',
    'work_context_timestamp',
    'work_followup_need',
    'work_followup_timestamp',
]

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

            # Session state table for cross-session continuity
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')

            # Usage patterns foundation for future behavioral suggestions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_patterns (
                    hour INTEGER,
                    day_of_week INTEGER,
                    tool_used TEXT,
                    app_name TEXT NOT NULL DEFAULT '',
                    count INTEGER DEFAULT 1,
                    last_seen TEXT,
                    PRIMARY KEY (hour, day_of_week, tool_used, app_name)
                )
            ''')
            
            conn.commit()
            logger.info("SQLite memory initialized at %s", DB_PATH)

        # Backfill usage patterns from historical command logs so suggestions
        # can become useful immediately when old logs already exist.
        backfill_usage_patterns_incremental()
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
            _log_usage_pattern(cursor, command, timestamp)
            conn.commit()
    except Exception as e:
        logger.error("Failed to log command: %s", e)


def _infer_tool_and_app(command: str) -> tuple[str | None, str | None]:
    """Infer coarse tool/app usage from raw command text for behavior analytics."""
    cleaned = (command or '').strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned:
        return None, None

    app_match = re.search(r'\b(?:open|launch|start|run|close|quit|exit|kill)\s+(.+)$', cleaned)
    app_name = app_match.group(1).strip() if app_match else None

    if cleaned.startswith(('open ', 'launch ', 'start ', 'run ')):
        return 'open_app', app_name
    if cleaned.startswith(('close ', 'quit ', 'exit ', 'kill ')):
        return 'close_app', app_name
    if 'system status' in cleaned or 'cpu usage' in cleaned:
        return 'get_system_status', None
    if 'work mode' in cleaned or 'focus mode' in cleaned or 'end work' in cleaned:
        return 'workflow', None
    return 'other', None


def _log_usage_pattern(cursor: sqlite3.Cursor, command: str, timestamp: str) -> None:
    """Upsert a usage pattern row for time-based behavior analysis."""
    tool_used, app_name = _infer_tool_and_app(command)
    if not tool_used:
        return

    dt = datetime.fromisoformat(timestamp)
    hour = dt.hour
    day_of_week = dt.weekday()
    app_key = (app_name or '').strip()

    cursor.execute(
        '''
        INSERT INTO usage_patterns (hour, day_of_week, tool_used, app_name, count, last_seen)
        VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(hour, day_of_week, tool_used, app_name)
        DO UPDATE SET
            count = count + 1,
            last_seen = excluded.last_seen
        ''',
        (hour, day_of_week, tool_used, app_key, timestamp),
    )

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


def save_session_state(state: dict, keys: list[str] | None = None) -> None:
    """Persist selected session keys to SQLite for cross-session continuity."""
    try:
        key_list = keys or PERSISTED_SESSION_KEYS
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for key in key_list:
                if key not in state:
                    continue
                value = state.get(key)
                cursor.execute(
                    'INSERT OR REPLACE INTO session_state (key, value, updated_at) VALUES (?, ?, ?)',
                    (key, json.dumps(value), timestamp),
                )
            conn.commit()
    except Exception as e:
        logger.error('Failed to save session state: %s', e)


def load_session_state(keys: list[str] | None = None) -> dict:
    """Load persisted session keys from SQLite."""
    loaded: dict = {}
    try:
        key_list = keys or PERSISTED_SESSION_KEYS
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for key in key_list:
                cursor.execute('SELECT value FROM session_state WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row and row[0] is not None:
                    loaded[key] = json.loads(row[0])
    except Exception as e:
        logger.error('Failed to load session state: %s', e)
    return loaded


def get_hourly_open_app_suggestions(limit: int = 3) -> list[str]:
    """Return frequent app names for the current hour/day to drive suggestions."""
    try:
        now = datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT app_name
                FROM usage_patterns
                WHERE hour = ?
                  AND day_of_week = ?
                  AND tool_used = 'open_app'
                  AND app_name != ''
                ORDER BY count DESC, last_seen DESC
                LIMIT ?
                ''',
                (now.hour, now.weekday(), limit),
            )
            return [row[0] for row in cursor.fetchall() if row and row[0]]
    except Exception as e:
        logger.error('Failed to read hourly suggestions: %s', e)
        return []


def get_scored_startup_suggestion(
    min_count: int = 3,
    min_confidence: float = 0.55,
    cooldown_minutes: int = 180,
) -> str | None:
    """Return one startup suggestion when confidence and cooldown thresholds are met."""
    try:
        rows: list[tuple[str, int]] = []
        now = datetime.now()
        cooldown_key = 'suggestion.startup.last_offered_at'
        last_offered_raw = get_preference(cooldown_key)
        if last_offered_raw:
            try:
                last_offered_at = datetime.fromisoformat(last_offered_raw)
                if now - last_offered_at < timedelta(minutes=max(1, cooldown_minutes)):
                    return None
            except ValueError:
                # Ignore malformed timestamps and continue.
                pass

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT app_name, SUM(count) as score
                FROM usage_patterns
                WHERE hour = ?
                  AND day_of_week = ?
                  AND tool_used = 'open_app'
                  AND app_name != ''
                GROUP BY app_name
                ORDER BY score DESC
                LIMIT 5
                ''',
                (now.hour, now.weekday()),
            )
            rows = [(str(row[0]), int(row[1])) for row in cursor.fetchall() if row and row[0]]

            # Sparse-data fallback: use same hour across all weekdays when
            # same-day evidence is not enough yet.
            if not rows:
                cursor.execute(
                    '''
                    SELECT app_name, SUM(count) as score
                    FROM usage_patterns
                    WHERE hour = ?
                      AND tool_used = 'open_app'
                      AND app_name != ''
                    GROUP BY app_name
                    ORDER BY score DESC
                    LIMIT 5
                    ''',
                    (now.hour,),
                )
                rows = [(str(row[0]), int(row[1])) for row in cursor.fetchall() if row and row[0]]

        if not rows:
            return None

        top_app, top_score = rows[0]
        total = sum(score for _, score in rows)
        if total <= 0:
            return None

        confidence = top_score / total
        second_score = rows[1][1] if len(rows) > 1 else 0
        margin = (top_score - second_score) / top_score if top_score > 0 else 0.0

        if top_score < max(1, min_count):
            return None
        if confidence < max(0.0, min(1.0, min_confidence)):
            return None
        if margin < 0.20:
            return None

        save_preference(cooldown_key, now.isoformat())
        logger.info(
            'Startup suggestion selected: app=%s score=%d confidence=%.2f margin=%.2f',
            top_app,
            top_score,
            confidence,
            margin,
        )
        return top_app
    except Exception as e:
        logger.error('Failed to compute scored startup suggestion: %s', e)
        return None


def backfill_usage_patterns_incremental() -> None:
    """Incrementally project command_log history into usage_patterns."""
    try:
        last_key = 'usage_patterns.last_backfill_command_id'
        last_raw = get_preference(last_key)
        last_id = int(last_raw) if last_raw and str(last_raw).isdigit() else 0

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, timestamp, command FROM command_log WHERE id > ? ORDER BY id ASC',
                (last_id,),
            )
            rows = cursor.fetchall()

            if not rows:
                return

            max_id = last_id
            for row in rows:
                cmd_id = int(row[0])
                timestamp = str(row[1])
                command = str(row[2] or '')
                _log_usage_pattern(cursor, command, timestamp)
                if cmd_id > max_id:
                    max_id = cmd_id

            conn.commit()

        save_preference(last_key, str(max_id))
        logger.info('Usage pattern backfill applied: %d new command(s)', len(rows))
    except Exception as e:
        logger.error('Failed usage pattern backfill: %s', e)


def get_work_context() -> tuple[str | None, str | None]:
    """Retrieve stored work context from current session.
    
    Returns a tuple of (work_context, timestamp) if available, else (None, None).
    Context is captured when user enters work mode or focus mode and is used
    for contextual followup suggestions and assistance.
    """
    try:
        from core.session import get as session_get
        context = session_get('work_context')
        timestamp = session_get('work_context_timestamp')
        return (context, timestamp) if context else (None, None)
    except Exception as e:
        logger.error('Failed to retrieve work context: %s', e)
        return (None, None)


def clear_work_context() -> None:
    """Clear stored work context from session (e.g., at end of work mode)."""
    try:
        from core.session import update as session_update
        session_update('work_context', None)
        session_update('work_context_timestamp', None)
        logger.info('Work context cleared')
    except Exception as e:
        logger.error('Failed to clear work context: %s', e)

