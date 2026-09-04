# skills/file_skill.py
# ──────────────────────────────────────────────────────────────────────
# File-system tools: list files, open folders
# v2 — Safety-hardened: blocks access to protected OS paths
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import difflib
import os
import re
import string
import sys
import subprocess
import logging
import time
from pathlib import Path

# 2. internal
from config import FOLDER_ALIASES
from core.safety import is_path_protected
from core.session import update as session_update
from pipeline.memory import get_aliases

logger = logging.getLogger('dna.skill.file')

# Add common variants locally
_FOLDER_VARIANTS = {
    'download': 'downloads',
    'document': 'documents',
    'video': 'videos',
    'picture': 'pictures',
    'photo': 'pictures',
    'photos': 'pictures',
}

# ── Folder index: name -> [Paths] across all drives, rebuilt on TTL ──
# Previously only Home/Desktop/Documents were scanned, so folders on E:\
# (or any dev drive) were invisible, and matching was exact-only so any
# STT mangling meant "not found".
_FOLDER_INDEX = {"ts": 0.0, "map": {}}
_FOLDER_INDEX_TTL = 1800.0  # 30 minutes; folders move rarely
_SKIP_DIR_NAMES = {
    '$recycle.bin', 'windows', 'program files', 'program files (x86)',
    'programdata', 'appdata', '.git', '__pycache__', 'node_modules',
    '.venv', 'venv', 'recovery', 'system volume information',
    '$windows.~bt', '$windows.~ws', 'msocache', 'perflogs',
    'documents and settings',
}

# Index build budgets: deep drive walks must never hang the voice loop.
_INDEX_MAX_DIRS = 80000
_INDEX_MAX_SECS = 20.0


def _search_roots() -> list[tuple]:
    """Directories to index as (root, max_depth).

    Override with DNA_FOLDER_ROOTS (os.pathsep-separated, e.g. in .env:
    DNA_FOLDER_ROOTS=E:\\Projects;E:\\ ) plus optional DNA_FOLDER_DEPTH.
    """
    override = os.getenv('DNA_FOLDER_ROOTS', '').strip()
    if override:
        try:
            depth = int(os.getenv('DNA_FOLDER_DEPTH', '2'))
        except ValueError:
            depth = 2
        roots = []
        for part in override.split(os.pathsep):
            p = Path(part.strip())
            if part.strip() and p.exists():
                roots.append((p, depth))
        return roots

    roots = []
    for alias_path in FOLDER_ALIASES.values():
        try:
            if alias_path and Path(alias_path).exists():
                roots.append((Path(alias_path), 1))
        except Exception:
            continue
    home = Path.home()
    for base in [home, home / 'Desktop', home / 'Documents']:
        if base.exists():
            roots.append((base, 2))
    for dev in [home / 'Projects', home / 'source', home / 'code',
                home / 'Documents' / 'Projects']:
        if dev.exists():
            roots.append((dev, 2))
    # Every drive, top level only: E:\\Vizzy analytics is found here.
    # Nested project folders included automatically; the walk is
    # time/count-budgeted and system dirs are skipped, so no manual
    # roots are needed. DNA_FOLDER_ROOTS only adds *extra* custom roots.
    for letter in string.ascii_uppercase:
        drive = Path(f'{letter}:\\')
        if drive.exists():
            roots.append((drive, 3))
    # Dedupe preserving order
    seen, unique = set(), []
    for r, d in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            unique.append((r, d))
    return unique


def _walk_dirs(folder: Path, max_depth: int, depth: int, out: list, budget: dict) -> None:
    if depth > max_depth or budget["dirs"] >= _INDEX_MAX_DIRS or time.time() > budget["deadline"]:
        return
    try:
        entries = list(folder.iterdir())
    except (PermissionError, OSError):
        return
    for entry in entries:
        try:
            if not entry.is_dir() or entry.is_symlink():
                continue
            name = entry.name
            if not name or name.startswith('.') or name.startswith('$') or name.lower() in _SKIP_DIR_NAMES:
                continue
            out.append(entry)
            budget["dirs"] += 1
            if depth < max_depth:
                _walk_dirs(entry, max_depth, depth + 1, out, budget)
        except (PermissionError, OSError):
            continue


def _ensure_folder_index() -> dict:
    """Return cached name->paths index, rebuilding after TTL."""
    now = time.time()
    if _FOLDER_INDEX["map"] and (now - _FOLDER_INDEX["ts"]) < _FOLDER_INDEX_TTL:
        return _FOLDER_INDEX["map"]
    index: dict[str, list] = {}
    budget = {"dirs": 0, "deadline": now + _INDEX_MAX_SECS}
    for root, depth in _search_roots():
        found: list = []
        _walk_dirs(root, depth, 0, found, budget)
        for p in found:
            try:
                key = p.name.lower()
                resolved = str(p.resolve())
            except OSError:
                continue
            bucket = index.setdefault(key, [])
            if all(str(q) != resolved for q in bucket):
                bucket.append(p)
    # Prefer shallowest path when several share a name
    for key in index:
        index[key].sort(key=lambda p: len(p.parts))
    _FOLDER_INDEX["map"] = index
    _FOLDER_INDEX["ts"] = now
    logger.info('Folder index rebuilt: %d names.', len(index))
    return index


def _reset_folder_index() -> None:
    """Clear the index (tests / manual refresh)."""
    _FOLDER_INDEX["map"] = {}
    _FOLDER_INDEX["ts"] = 0.0
    _clear_pending_selection()


# ── Disambiguation memory: show similar, remember the pick ──

_pending_selection = {"query": None, "choices": [], "ts": 0.0}
_PENDING_TTL = 300.0
_ORDINAL_WORDS = {
    'first': 0, '1st': 0, 'one': 0,
    'second': 1, '2nd': 1, 'two': 1,
    'third': 2, '3rd': 2, 'three': 2,
    'fourth': 3, '4th': 3, 'four': 3,
    'fifth': 4, '5th': 4, 'five': 4,
}


def _clear_pending_selection() -> None:
    _pending_selection["query"] = None
    _pending_selection["choices"] = []
    _pending_selection["ts"] = 0.0


def _parse_selection(clean: str, choices: list) -> int | None:
    """Map 'second one' / 'number 2' / '2' / path fragment to a choice index."""
    t = (clean or "").strip()
    if re.fullmatch(r'(?:number|option|no\.?|#)?\s*\d+', t):
        n = int(re.search(r'\d+', t).group())  # type: ignore[union-attr]
        return n - 1 if 1 <= n <= len(choices) else None
    for word, idx in _ORDINAL_WORDS.items():
        if re.search(rf'\b{word}\b(?:\s+one)?', t) and idx < len(choices):
            return idx
    if re.search(r'\blast\b(?:\s+one)?', t):
        return len(choices) - 1
    if ':\\' in t or '/' in t:
        frag = t.replace('/', '\\')
        for i, c in enumerate(choices):
            if frag in str(c).lower():
                return i
    return None


def _check_pending_selection(clean: str) -> tuple | None:
    """Resolve a follow-up pick ('second one', '2', fuller path).

    The pick is remembered as an alias, so the same spoken name resolves
    directly next time with no question asked.
    """
    choices = _pending_selection["choices"]
    if not choices:
        return None
    if time.time() - _pending_selection["ts"] > _PENDING_TTL:
        _clear_pending_selection()
        return None
    idx = _parse_selection(clean, choices)
    if idx is None:
        return None
    target = choices[idx]
    query = _pending_selection["query"] or clean
    try:
        from pipeline.memory import save_alias
        save_alias(query, str(target))
    except Exception as e:
        logger.debug("alias learn skipped: %s", e)
    _clear_pending_selection()
    return _validate_target(target, target.name,
                            note=f"Selected '{target.name}', boss — I'll remember it.")


def _validate_target(target: Path, name: str, note: str = "") -> tuple:
    """Safety + existence gate. Returns (Path|None, display|error, note)."""
    if is_path_protected(target):
        logger.warning('BLOCKED: Resolved path is protected: %s', target)
        return None, (
            f"Sorry, I can't access {name} because it's a protected system folder."
        ), ""
    if not target.exists():
        return None, f"Sorry, the {name} folder doesn't seem to exist on your machine.", ""
    _clear_pending_selection()
    return target, target.name, note


def _resolve_folder(name: str) -> tuple:
    """Resolve a spoken folder name to an actual Path.

    Searches aliases first, then the all-drive folder index (Home trio,
    dev dirs, every drive top level — so E:\\ projects are found), with
    fuzzy matching so STT mangling ("vizy analitics") still resolves.
    Blocks access to protected system paths.

    Returns (target|None, display|error_message, note). `note` carries an
    "assuming you meant X" flag for ambiguous speech. When several folders
    match, numbered choices are offered and kept pending: a follow-up pick
    ("second one", "2") resolves AND is remembered as an alias, so the
    same spoken name works directly next time.
    """
    original_name = name.strip()
    clean = original_name.lower()

    # ── Safety: block obvious system path attempts ──
    if is_path_protected(original_name):
        logger.warning('BLOCKED: Attempt to access protected path: %s', original_name)
        return None, (
            f'I cannot access "{original_name}" — it is a protected system path. '
            'This restriction keeps your operating system safe.'
        ), ""

    # ── Follow-up pick for a pending disambiguation? ──
    picked = _check_pending_selection(clean)
    if picked is not None:
        return picked

    # Check for direct alias (case-insensitive)
    db_aliases = get_aliases()
    path = db_aliases.get(clean) or FOLDER_ALIASES.get(clean)

    # Try common variants if not found
    if not path and clean in _FOLDER_VARIANTS:
        path = db_aliases.get(_FOLDER_VARIANTS[clean]) or FOLDER_ALIASES.get(_FOLDER_VARIANTS[clean])

    if path:
        return _validate_target(Path(path), original_name)

    # ── Index search: exact, then fuzzy (STT-tolerant) ──
    index = _ensure_folder_index()
    if clean in index:
        return _validate_target(index[clean][0], original_name)

    close = difflib.get_close_matches(clean, list(index.keys()), n=3, cutoff=0.6)
    if not close:
        return None, (
            f"Sorry, I couldn't find a folder called {original_name} on your system. "
            f"Try the fuller name if you know it."
        ), ""

    if len(close) == 1:
        best = close[0]
    else:
        scored = sorted(
            ((difflib.SequenceMatcher(None, clean, c).ratio(), c) for c in close),
            reverse=True,
        )
        if scored[0][0] - scored[1][0] > 0.15:
            best = scored[0][1]
        else:
            _pending_selection["query"] = clean
            _pending_selection["choices"] = [index[c][0] for c in close]
            _pending_selection["ts"] = time.time()
            options = "; ".join(f"{i}. {index[c][0]}" for i, c in enumerate(close, 1))
            return None, (
                f"Boss, I found a few like that: {options}. "
                f"Say the number or the fuller name."
            ), ""
    target = index[best][0]
    return _validate_target(target, original_name,
                            note=f"Assuming you meant '{target.name}', boss.")


def list_files(directory: str) -> str:
    """List files in common Windows directories like Desktop, Downloads, or Documents."""
    try:
        target, display, note = _resolve_folder(directory)
        if target is None:
            return display  # display holds the error message

        # Store full path so downstream data/analysis routing can use it.
        # Previously stored bare folder name which broke run_analysis(active_file).
        session_update('active_file', str(target))
        items = os.listdir(target)
        prefix = (note + " " if note else "")
        if not items:
            return f'{prefix}Your {display} folder is empty.'

        files = [f for f in items if (target / f).is_file()]
        if not files:
            return f'{prefix}Your {display} folder has no files, only subfolders.'

        count = len(files)
        limit = 5
        to_speak = files[:limit]

        result = f'{prefix}Alright, I found {count} files. '
        result += 'The first few are: ' + ', '.join(to_speak)
        if count > limit:
            result += f' and {count - limit} others.'

        return result

    except Exception as e:
        logger.error('list_files failed: %s', e)
        return 'Sorry, I had trouble reading that folder.'


def open_folder(directory: str) -> str:
    """Open a common folder in Explorer."""
    try:
        target, display, note = _resolve_folder(directory)
        if target is None:
            return display

        session_update('active_file', str(target))
        if sys.platform == 'win32':
            os.startfile(target)
        elif sys.platform == 'darwin':
            subprocess.run(['open', target], check=True)
        else:
            subprocess.run(['xdg-open', target], check=True)
        prefix = (note + " " if note else "")
        return f'{prefix}Sure, opening up that folder for you.'
    except Exception as e:
        logger.error('open_folder failed: %s', e)
        return 'Sorry, I had trouble opening that folder.'


def find_folder(name: str) -> str:
    """Locate a folder by spoken name across all drives and return its full path.

    Used when another app needs the path (e.g. typing a project folder into
    an Open dialog) — the caller passes the returned path verbatim and never
    guesses. No session state is touched.
    """
    try:
        if not (name or "").strip():
            return "Boss, tell me the folder name to find."
        target, display, note = _resolve_folder(name.strip())
        if target is None:
            return display
        prefix = (note + " " if note else "")
        return f"{prefix}The folder is at {target}."
    except Exception as e:
        logger.error('find_folder failed: %s', e)
        return 'Sorry, I had trouble searching for that folder.'


# Skill module contract
TOOLS = {
    'list_files': list_files,
    'open_folder': open_folder,
    'find_folder': find_folder,
}
