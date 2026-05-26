# skills/data_engine/catalog.py
from contextlib import contextmanager
import datetime
import hashlib
import json
import logging
import os
import string
from pathlib import Path
import sqlite3

from config import DB_PATH, FOLDER_ALIASES

logger = logging.getLogger('dna.data_engine.catalog')


def _compute_md5(path: str) -> str:
    """Compute MD5 checksum of a file in chunks."""
    try:
        if not Path(path).is_file():
            return ""
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.warning('Failed to compute MD5 for %s: %s', path, e)
        return ""


class DataCatalog:
    """Dataset registry + analysis history. Extends dna_memory.db."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_tables()

    @contextmanager
    def _get_conn(self):
        """Get connection to SQLite, yield it, and ensure it's closed."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self):
        """Create catalog tables if they do not exist."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with self._get_conn() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS dataset_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    file_hash TEXT,
                    row_count INTEGER,
                    column_count INTEGER,
                    column_schema TEXT,
                    data_quality_score REAL,
                    first_analyzed TEXT,
                    last_analyzed TEXT,
                    analysis_count INTEGER DEFAULT 1
                )
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER REFERENCES dataset_catalog(id),
                    timestamp TEXT,
                    question TEXT,
                    query_type TEXT,
                    generated_sql TEXT,
                    result_summary TEXT,
                    report_path TEXT,
                    findings_json TEXT,
                    charts_json TEXT
                )
                """)
                conn.commit()
            logger.info('Database catalog tables initialized successfully.')
        except Exception as e:
            logger.error('Failed to initialize catalog database: %s', e, exc_info=True)

    def find_dataset(self, keyword: str) -> dict | None:
        """Search catalog by keyword first, then filesystem fallback."""
        try:
            with self._get_conn() as conn:
                # Try exact/substring match on file_name in database first
                row = conn.execute(
                    "SELECT * FROM dataset_catalog WHERE file_name LIKE ?",
                    (f"%{keyword}%",)
                ).fetchone()
                if row:
                    logger.info('Dataset found in database catalog for keyword "%s": %s', keyword, row['file_path'])
                    return dict(row)

            # Fallback to filesystem search
            logger.info('Dataset not found in database catalog. Searching filesystem for "%s".', keyword)
            matches = self._search_data_files(keyword)
            if matches:
                chosen = matches[0]
                chosen_path = str(chosen.resolve())

                # Double check if this path is already registered under a different name/keyword
                with self._get_conn() as conn:
                    row = conn.execute("SELECT * FROM dataset_catalog WHERE file_path = ?", (chosen_path,)).fetchone()
                    if row:
                        return dict(row)

                # Register new file after profiling
                from .profiler import DataProfiler
                profiler = DataProfiler()
                profile = profiler.profile(chosen_path)

                db_id = self.register_dataset(chosen_path, profile)
                with self._get_conn() as conn:
                    row = conn.execute("SELECT * FROM dataset_catalog WHERE id = ?", (db_id,)).fetchone()
                    if row:
                        return dict(row)

        except Exception as e:
            logger.error('find_dataset failed: %s', e, exc_info=True)
        return None

    def register_dataset(self, path: str, profile: dict) -> int:
        """Register or update a dataset in the catalog."""
        try:
            file_hash = _compute_md5(path)
            file_name = Path(path).name
            now = datetime.datetime.now().isoformat()

            row_count = profile.get('row_count', 0)
            column_count = profile.get('column_count', 0)
            schema_json = json.dumps(profile.get('schema', []))
            quality_score = profile.get('quality_score', 100.0)

            with self._get_conn() as conn:
                row = conn.execute("SELECT id, analysis_count FROM dataset_catalog WHERE file_path = ?", (path,)).fetchone()
                if row:
                    db_id = row['id']
                    count = row['analysis_count'] + 1
                    conn.execute("""
                        UPDATE dataset_catalog 
                        SET file_hash = ?, row_count = ?, column_count = ?, column_schema = ?, 
                            data_quality_score = ?, last_analyzed = ?, analysis_count = ?
                        WHERE id = ?
                    """, (file_hash, row_count, column_count, schema_json, quality_score, now, count, db_id))
                    logger.info('Updated existing dataset %s in catalog (ID: %d).', file_name, db_id)
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO dataset_catalog 
                        (file_path, file_name, file_hash, row_count, column_count, column_schema, data_quality_score, first_analyzed, last_analyzed, analysis_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (path, file_name, file_hash, row_count, column_count, schema_json, quality_score, now, now))
                    db_id = cursor.lastrowid
                    logger.info('Registered new dataset %s in catalog (ID: %d).', file_name, db_id)
                conn.commit()
                return db_id
        except Exception as e:
            logger.error('register_dataset failed: %s', e, exc_info=True)
            return -1

    def log_analysis(self, dataset_id: int, question: str, 
                     query_type: str, result_summary: str, **kwargs):
        """Log a query and its results to analysis_history."""
        try:
            now = datetime.datetime.now().isoformat()
            generated_sql = kwargs.get('generated_sql', '')
            report_path = kwargs.get('report_path', '')
            findings_json = json.dumps(kwargs.get('findings_json', []))
            charts_json = json.dumps(kwargs.get('charts_json', []))

            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO analysis_history 
                    (dataset_id, timestamp, question, query_type, generated_sql, result_summary, report_path, findings_json, charts_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (dataset_id, now, question, query_type, generated_sql, result_summary, report_path, findings_json, charts_json))
                conn.commit()
            logger.info('Logged analysis for dataset ID %d to history.', dataset_id)
        except Exception as e:
            logger.error('log_analysis failed: %s', e, exc_info=True)

    def get_history(self, keyword: str) -> list[dict]:
        """Recall past analyses by keyword search."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT h.*, c.file_name, c.file_path 
                    FROM analysis_history h
                    JOIN dataset_catalog c ON h.dataset_id = c.id
                    WHERE h.question LIKE ? OR c.file_name LIKE ?
                    ORDER BY h.timestamp DESC
                """, (f"%{keyword}%", f"%{keyword}%")).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error('get_history failed: %s', e, exc_info=True)
            return []

    def needs_reprofile(self, path: str) -> bool:
        """Check if file hash changed since last profile."""
        try:
            if not Path(path).is_file():
                return False
            current_hash = _compute_md5(path)
            with self._get_conn() as conn:
                row = conn.execute("SELECT file_hash FROM dataset_catalog WHERE file_path = ?", (path,)).fetchone()
                if row:
                    return row['file_hash'] != current_hash
            return True
        except Exception as e:
            logger.error('needs_reprofile failed: %s', e, exc_info=True)
            return True

    def _search_data_files(self, keyword: str = "") -> list[Path]:
        """Search common folders AND all drive roots for CSV/Excel files matching a keyword."""
        valid_exts = {'.csv', '.xlsx', '.xls'}
        candidates = []
        seen = set()

        # Build scan list: configured folders + all drive roots
        scan_dirs = []

        # 1. Configured folder aliases
        for key in ['downloads', 'desktop', 'documents']:
            p = FOLDER_ALIASES.get(key)
            if p and Path(p).exists():
                scan_dirs.append((Path(p), 1))  # depth 1 = scan direct children only

        # 2. Project data folder
        project_data = Path(__file__).parent.parent.parent / 'data'
        if project_data.exists():
            scan_dirs.append((project_data, 1))

        # 3. All available drive roots (C:\, D:\, E:\, etc.) — scan 2 levels deep
        for letter in string.ascii_uppercase:
            drive = Path(f'{letter}:\\')
            if drive.exists():
                scan_dirs.append((drive, 2))

        def _scan(folder: Path, max_depth: int, current_depth: int = 0):
            if current_depth > max_depth:
                return
            try:
                for f in folder.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_exts:
                        resolved = str(f.resolve())
                        if resolved not in seen:
                            seen.add(resolved)
                            candidates.append(f)
                    elif f.is_dir() and current_depth < max_depth:
                        # Skip system/hidden folders
                        skip = {'$recycle.bin', 'windows', 'program files', 'program files (x86)', 
                                'programdata', 'appdata', '.git', '__pycache__', 'node_modules', '.venv'}
                        if f.name.lower() not in skip and not f.name.startswith('.'):
                            _scan(f, max_depth, current_depth + 1)
            except (PermissionError, OSError):
                pass

        for folder, depth in scan_dirs:
            _scan(folder, depth)

        # Filter by keyword if provided
        if keyword:
            kw = keyword.lower().strip()
            scored = []
            for f in candidates:
                stem = f.stem.lower()
                stem_clean = stem.replace('_', ' ').replace('-', ' ').replace('.', ' ')
                stem_flat = stem_clean.replace(' ', '')
                kw_flat = kw.replace(' ', '')

                words = stem_clean.split()

                if stem_flat == kw_flat:
                    scored.append((0, f))  # Best: exact match
                elif kw in words:
                    scored.append((1, f))  # Great: word match
                elif stem_flat.startswith(kw_flat):
                    scored.append((2, f))  # Good: starts with
                elif kw_flat in stem_flat:
                    scored.append((3, f))  # OK: contains
            scored.sort(key=lambda x: x[0])
            return [f for _, f in scored]
        else:
            # No keyword — return most recent files
            candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return candidates[:5]
