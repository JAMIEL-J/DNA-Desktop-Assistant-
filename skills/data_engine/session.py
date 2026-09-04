# skills/data_engine/session.py
# ──────────────────────────────────────────────────────────────────────
# Dataset sessions — Cowork-style live state for CIPHER.
# One shared DuckDB connection per session key (project or 'global'),
# N registered views (single file = 1 view, joins = N views), profiles
# cached by file hash so follow-ups never re-profile. LRU eviction keeps
# i3/8GB safe: bounded samples only, DuckDB spills to disk.
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import logging
import re
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger('dna.data_engine.session')

_MAX_SESSIONS = 2
_SAMPLE_ROWS = 10000


def _file_kind(path: str) -> str:
    lower = path.lower()
    if lower.endswith('.parquet'):
        return 'parquet'
    if lower.endswith(('.xlsx', '.xls')):
        return 'excel'
    return 'csv'


def _safe_view_name(path: str, existing: set) -> str:
    stem = re.sub(r'\W+', '_', Path(path).stem).strip('_').lower() or 'data'
    name, i = stem[:30], 1
    while name in existing:
        i += 1
        name = f"{stem[:26]}_{i}"
    return name


class DataSession:
    """Live per-key workspace: shared DuckDB handle + views + cached profiles."""

    def __init__(self, key: str):
        import duckdb
        self.key = key
        self.con = duckdb.connect()
        self.views: dict[str, str] = {}      # view -> file path
        self.profiles: dict[str, dict] = {}  # path -> profile (hash-checked)
        self.samples: dict[str, object] = {}  # path -> bounded sample df for detectors
        self.hashes: dict[str, str] = {}     # path -> md5 at profile time
        self.history: list[dict] = []        # {question, sql, rows}

    def close(self) -> None:
        try:
            self.con.close()
        except Exception:
            pass
        self.views.clear()
        self.profiles.clear()
        self.samples.clear()

    # ── files ──

    def open_file(self, path: str, view: str | None = None, sheet: str | int | None = None) -> dict:
        """Register a file as a view (idempotent). Returns info dict."""
        import pandas as pd
        existing = set(self.views)
        if path in self.views.values():
            for v, p in self.views.items():
                if p == path:
                    return {'view': v, 'path': path, 'kind': _file_kind(path), 'reused': True}
        view = view or _safe_view_name(path, existing)
        kind = _file_kind(path)
        esc = path.replace("'", "''")
        if kind == 'csv':
            self.con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_csv_auto('{esc}')")
        elif kind == 'parquet':
            self.con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{esc}')")
        else:
            df = pd.read_excel(path, sheet_name=sheet if sheet is not None else 0)
            self.con.register(view, df)
        self.views[view] = path
        logger.info('Session [%s]: opened %s as view %s (%s).', self.key, Path(path).name, view, kind)
        return {'view': view, 'path': path, 'kind': kind, 'reused': False}

    def get_profile(self, path: str, sheet: str | int | None = None) -> tuple[dict, bool]:
        """Cached profile + cache-hit flag. Re-profiles only on hash change."""
        from .catalog import _compute_md5
        from .profiler import DataProfiler
        h = _compute_md5(path)
        if path in self.profiles and self.hashes.get(path) == h and path in self.samples:
            return self.profiles[path], True
        profiler = DataProfiler()
        profile = profiler.profile(path, sheet=sheet)
        self.profiles[path] = profile
        self.samples[path] = profiler.last_sample_df
        self.hashes[path] = h
        return profile, False

    def sample(self, view: str, n: int = _SAMPLE_ROWS):
        return self.con.execute(f"SELECT * FROM {view} USING SAMPLE {min(n, _SAMPLE_ROWS)}").fetchdf()

    def log_turn(self, question: str, sql: str, rows: int) -> None:
        self.history.append({'question': (question or '')[:200], 'sql': (sql or '')[:500], 'rows': rows})
        self.history = self.history[-10:]

    # ── joins (star-schema aware) ──

    def suggest_keys(self) -> list[dict]:
        """Candidate join keys across views: exact names, then fuzzy."""
        import difflib
        cols: dict[str, list[str]] = {}
        for view in self.views:
            try:
                cur = self.con.execute(f"SELECT * FROM {view} LIMIT 0")
                names = [d[0] for d in cur.description]
            except Exception:
                continue
            for c in names:
                cols.setdefault(c.lower(), []).append(f"{view}.{c}")
        out = []
        for key, refs in cols.items():
            views = {r.split('.')[0] for r in refs}
            if len(views) > 1:
                out.append({'key': key, 'refs': refs, 'match': 'exact'})
        if not out:
            keys = list(cols)
            for i, a in enumerate(keys):
                m = difflib.get_close_matches(a, keys[i + 1:], n=1, cutoff=0.8)
                if m:
                    out.append({'key': f"{a} ~ {m[0]}", 'refs': cols[a] + cols[m[0]], 'match': 'fuzzy'})
        return out

    def validate_grain(self, dim_view: str, key: str) -> dict:
        """Check the 'one' side is actually unique. Returns counts + risk flag."""
        total = self.con.execute(f"SELECT COUNT(*) FROM {dim_view}").fetchone()[0]
        distinct = self.con.execute(f'SELECT COUNT(DISTINCT "{key}") FROM {dim_view}').fetchone()[0]
        return {'dim_rows': total, 'dim_distinct_keys': distinct,
                'fanout_risk': distinct < total,
                'fanout_factor': round(total / distinct, 2) if distinct else 0}

    def join(self, fact_view: str, dim_view: str, fact_key: str, dim_key: str | None = None) -> dict:
        """LEFT join fact->dim with grain validation + fanout/unmatched report."""
        dim_key = dim_key or fact_key
        grain = self.validate_grain(dim_view, dim_key)
        fact_rows = self.con.execute(f"SELECT COUNT(*) FROM {fact_view}").fetchone()[0]
        out_view = _safe_view_name(f"{fact_view}_x_{dim_view}", set(self.views))
        self.con.execute(
            f'CREATE OR REPLACE VIEW {out_view} AS '
            f'SELECT f.* FROM {fact_view} f LEFT JOIN (SELECT DISTINCT "{dim_key}" FROM {dim_view}) d '
            f'ON f."{fact_key}" = d."{dim_key}"'
        )
        # NOTE: base join keeps fact grain; full dim columns joined on demand by analysis SQL.
        self.con.execute(
            f'CREATE OR REPLACE VIEW {out_view}_full AS '
            f'SELECT * FROM {fact_view} f LEFT JOIN {dim_view} d ON f."{fact_key}" = d."{dim_key}"'
        )
        self.views[out_view + '_full'] = f"join:{fact_view}+{dim_view}"
        joined_rows = self.con.execute(f"SELECT COUNT(*) FROM {out_view}_full").fetchone()[0]
        unmatched = self.con.execute(
            f'SELECT COUNT(*) FROM {fact_view} f LEFT JOIN {dim_view} d '
            f'ON f."{fact_key}" = d."{dim_key}" WHERE d."{dim_key}" IS NULL'
        ).fetchone()[0]
        return {
            'view': out_view + '_full', 'fact_rows': fact_rows, 'joined_rows': joined_rows,
            'unmatched_fact_rows': unmatched, 'grain': grain,
            'warning': (f"Dimension key '{dim_key}' is not unique "
                        f"({grain['dim_rows']} rows, {grain['dim_distinct_keys']} distinct) — "
                        f"joined rows fan out ~{grain['fanout_factor']}x. Totals may double-count, boss."
                        if grain['fanout_risk'] else ""),
        }


_sessions: OrderedDict[str, DataSession] = OrderedDict()


def get_session(key: str | None = None) -> DataSession:
    """Process-wide LRU sessions (max 2 live DuckDB handles)."""
    key = key or 'global'
    if key in _sessions:
        _sessions.move_to_end(key)
        return _sessions[key]
    sess = DataSession(key)
    _sessions[key] = sess
    while len(_sessions) > _MAX_SESSIONS:
        old_key, old = _sessions.popitem(last=False)
        try:
            old.close()
        except Exception:
            pass
        logger.info('Evicted dataset session [%s] to protect RAM.', old_key)
    return sess


def session_key_for_request() -> str:
    """Scope sessions by active project (falls back to global)."""
    try:
        from core.session import get as session_get
        return session_get('active_project') or 'global'
    except Exception:
        return 'global'


def reset_sessions() -> None:
    """Close all sessions (tests / shutdown)."""
    for s in list(_sessions.values()):
        try:
            s.close()
        except Exception:
            pass
    _sessions.clear()
