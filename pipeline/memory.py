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


class MemoryVault:
    """Unified L1/L2 Memory Vault for facts, preferences, aliases, and semantic context."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def init_db(self):
        """Initializes the SQLite database with the required tables."""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
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

                # Facts table for L1 unified facts key-value storage
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS facts (
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
                logger.info("SQLite memory initialized at %s", self.db_path)

            # Backfill usage patterns from historical command logs so suggestions
            # can become useful immediately when old logs already exist.
            self.backfill_usage_patterns_incremental()
        except Exception as e:
            logger.error("Failed to initialize SQLite memory: %s", e)

    def set_fact(self, key: str, value: str) -> None:
        """Save a key-value fact into the facts table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                timestamp = datetime.now().isoformat()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO facts (key, value, updated_at) VALUES (?, ?, ?)',
                    (key.lower().strip(), str(value).strip(), timestamp)
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to set fact: %s", e)

    def get_fact(self, key: str) -> str | None:
        """Retrieve a fact from the database, searching facts, preferences, and aliases in order."""
        try:
            key_cleaned = key.lower().strip()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. Search in facts table
                cursor.execute('SELECT value FROM facts WHERE key = ?', (key_cleaned,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # 2. Search in preferences table
                cursor.execute('SELECT value FROM preferences WHERE key = ?', (key_cleaned,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # 3. Search in aliases table
                cursor.execute('SELECT target FROM aliases WHERE alias = ?', (key_cleaned,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                return None
        except Exception as e:
            logger.error("Failed to get fact: %s", e)
            return None

    def log_command(self, command: str, result: str, status: str = 'success'):
        """Log a voice command and its outcome."""
        try:
            if not command:
                return
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()
                cursor.execute(
                    'INSERT INTO command_log (timestamp, command, result, status) VALUES (?, ?, ?, ?)',
                    (timestamp, command, result, status)
                )
                self._log_usage_pattern(cursor, command, timestamp)
                conn.commit()
        except Exception as e:
            logger.error("Failed to log command: %s", e)

    def _infer_tool_and_app(self, command: str) -> tuple[str | None, str | None]:
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

    def _log_usage_pattern(self, cursor: sqlite3.Cursor, command: str, timestamp: str) -> None:
        """Upsert a usage pattern row for time-based behavior analysis."""
        tool_used, app_name = self._infer_tool_and_app(command)
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

    def save_preference(self, key: str, value: str):
        """Save a user preference key-value pair into SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                timestamp = datetime.now().isoformat()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)',
                    (key.lower().strip(), str(value).strip(), timestamp)
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to save preference: %s", e)

    def get_preference(self, key: str) -> str | None:
        """Retrieve a single preference from SQLite, or None if not found."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM preferences WHERE key = ?', (key.lower().strip(),))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error("Failed to get preference: %s", e)
            return None

    def get_preferences(self) -> dict:
        """Retrieve all mapped preferences from SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT key, value FROM preferences')
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error("Failed to get preferences: %s", e)
            return {}

    def save_alias(self, alias: str, target: str):
        """Save an application or folder alias mapping into SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                timestamp = datetime.now().isoformat()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO aliases (alias, target, updated_at) VALUES (?, ?, ?)',
                    (alias.lower().strip(), str(target).strip(), timestamp)
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to save alias: %s", e)

    def get_aliases(self) -> dict:
        """Retrieve all learned aliases mapped to their target paths."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT alias, target FROM aliases')
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error("Failed to get aliases: %s", e)
            return {}

    def save_session_state(self, state: dict, keys: list[str] | None = None) -> None:
        """Persist selected session keys to SQLite for cross-session continuity."""
        try:
            key_list = keys or PERSISTED_SESSION_KEYS
            timestamp = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
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

    def load_session_state(self, keys: list[str] | None = None) -> dict:
        """Load persisted session keys from SQLite."""
        loaded: dict = {}
        try:
            key_list = keys or PERSISTED_SESSION_KEYS
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for key in key_list:
                    cursor.execute('SELECT value FROM session_state WHERE key = ?', (key,))
                    row = cursor.fetchone()
                    if row and row[0] is not None:
                        loaded[key] = json.loads(row[0])
        except Exception as e:
            logger.error('Failed to load session state: %s', e)
        return loaded

    def get_hourly_open_app_suggestions(self, limit: int = 3) -> list[str]:
        """Return frequent app names for the current hour/day to drive suggestions."""
        try:
            now = datetime.now()
            with sqlite3.connect(self.db_path) as conn:
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
        self,
        min_count: int = 3,
        min_confidence: float = 0.55,
        cooldown_minutes: int = 180,
    ) -> str | None:
        """Return one startup suggestion when confidence and cooldown thresholds are met."""
        try:
            rows: list[tuple[str, int]] = []
            now = datetime.now()
            cooldown_key = 'suggestion.startup.last_offered_at'
            last_offered_raw = self.get_preference(cooldown_key)
            if last_offered_raw:
                try:
                    last_offered_at = datetime.fromisoformat(last_offered_raw)
                    if now - last_offered_at < timedelta(minutes=max(1, cooldown_minutes)):
                        return None
                except ValueError:
                    # Ignore malformed timestamps and continue.
                    pass

            with sqlite3.connect(self.db_path) as conn:
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

            self.save_preference(cooldown_key, now.isoformat())
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

    def backfill_usage_patterns_incremental(self) -> None:
        """Incrementally project command_log history into usage_patterns."""
        try:
            last_key = 'usage_patterns.last_backfill_command_id'
            last_raw = self.get_preference(last_key)
            last_id = int(last_raw) if last_raw and str(last_raw).isdigit() else 0

            with sqlite3.connect(self.db_path) as conn:
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
                    self._log_usage_pattern(cursor, command, timestamp)
                    if cmd_id > max_id:
                        max_id = cmd_id

                conn.commit()

            self.save_preference(last_key, str(max_id))
            logger.info('Usage pattern backfill applied: %d new command(s)', len(rows))
        except Exception as e:
            logger.error('Failed usage pattern backfill: %s', e)

    def get_work_context(self) -> tuple[str | None, str | None]:
        """Retrieve stored work context from current session."""
        try:
            from core.session import get as session_get
            context = session_get('work_context')
            timestamp = session_get('work_context_timestamp')
            return (context, timestamp) if context else (None, None)
        except Exception as e:
            logger.error('Failed to retrieve work context: %s', e)
            return (None, None)

    def clear_work_context(self) -> None:
        """Clear stored work context from session (e.g., at end of work mode)."""
        try:
            from core.session import update as session_update
            session_update('work_context', None)
            session_update('work_context_timestamp', None)
            logger.info('Work context cleared')
        except Exception as e:
            logger.error('Failed to clear work context: %s', e)

    def mirror_conversation(self, history: list[dict], session_timestamp: str = None) -> str | None:
        """Saves conversation history to a text file in data/memory/corpus/conversations/."""
        if not history:
            return None
        try:
            corpus_dir = Path("data/memory/corpus/conversations")
            corpus_dir.mkdir(parents=True, exist_ok=True)
            
            ts = session_timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{ts}.txt"
            filepath = corpus_dir / filename
            
            lines = []
            for msg in history:
                role = "User" if msg.get("role") == "user" else "DNA"
                content = msg.get("content", "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            
            if lines:
                filepath.write_text("\n".join(lines), encoding="utf-8")
                logger.info("Mirrored conversation history to %s", filepath)
                return str(filepath)
        except Exception as e:
            logger.error("Failed to mirror conversation: %s", e)
        return None

    def get_semantic_context(self, entity: str) -> list[dict]:
        """Retrieve semantic context triplets matching the entity from the graph."""
        try:
            from pipeline.graph_processor import GraphProcessor
            # Use default corpus/output paths or allow custom ones in the future.
            processor = GraphProcessor()
            return processor.get_subgraph(entity)
        except Exception as e:
            logger.error("Failed to retrieve semantic context for '%s': %s", entity, e)
            return []



# Module-level instance helper
_global_vault = None

def get_vault() -> MemoryVault:
    """Retrieve or initialize the global MemoryVault instance."""
    global _global_vault
    if _global_vault is None:
        _global_vault = MemoryVault()
    return _global_vault


# Module-level compatibility functions
def init_db():
    get_vault().init_db()

def log_command(command: str, result: str, status: str = 'success'):
    get_vault().log_command(command, result, status)

def save_preference(key: str, value: str):
    get_vault().save_preference(key, value)

def get_preference(key: str) -> str | None:
    return get_vault().get_preference(key)

def get_preferences() -> dict:
    return get_vault().get_preferences()

def save_alias(alias: str, target: str):
    get_vault().save_alias(alias, target)

def get_aliases() -> dict:
    return get_vault().get_aliases()

def save_session_state(state: dict, keys: list[str] | None = None) -> None:
    get_vault().save_session_state(state, keys)

def load_session_state(keys: list[str] | None = None) -> dict:
    return get_vault().load_session_state(keys)

def get_hourly_open_app_suggestions(limit: int = 3) -> list[str]:
    return get_vault().get_hourly_open_app_suggestions(limit)

def get_scored_startup_suggestion(
    min_count: int = 3,
    min_confidence: float = 0.55,
    cooldown_minutes: int = 180,
) -> str | None:
    return get_vault().get_scored_startup_suggestion(min_count, min_confidence, cooldown_minutes)

def backfill_usage_patterns_incremental() -> None:
    get_vault().backfill_usage_patterns_incremental()

def get_work_context() -> tuple[str | None, str | None]:
    return get_vault().get_work_context()

def clear_work_context() -> None:
    get_vault().clear_work_context()

def mirror_conversation(history: list[dict], session_timestamp: str = None) -> str | None:
    return get_vault().mirror_conversation(history, session_timestamp)

def get_semantic_context(entity: str) -> list[dict]:
    return get_vault().get_semantic_context(entity)


