# core/projects.py
# ──────────────────────────────────────────────────────────────────────
# Projects — Cowork-style persistent workspaces.
# Each project namespaces context that is currently global: instructions,
# memory notes, and run ledgers. Global no-project mode is untouched.
# Layout: data/projects/<name>/{AGENTS.md,context/,memory/,runs/}
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('dna.projects')

_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9\-_]{0,39}$')


def _base_dir() -> Path:
    override = os.getenv('DNA_PROJECTS_DIR', '').strip()
    if override:
        return Path(override)
    from config import BASE_DIR
    return Path(BASE_DIR) / 'data' / 'projects'


def sanitize_name(raw: str) -> str | None:
    """Normalize a spoken project name. None when invalid (traversal etc)."""
    if not raw:
        return None
    name = raw.strip().lower().replace(' ', '-')
    name = re.sub(r'[^a-z0-9\-_]', '', name).strip('-_')
    if not name or not _NAME_RE.match(name):
        return None
    return name


def project_root(name: str) -> Path:
    return _base_dir() / name


def ensure_project(name: str) -> Path:
    """Create project dirs + default AGENTS.md. Raises ValueError on bad name."""
    clean = sanitize_name(name)
    if not clean:
        raise ValueError(f"Invalid project name: {name!r}")
    root = project_root(clean)
    (root / 'context').mkdir(parents=True, exist_ok=True)
    (root / 'memory').mkdir(parents=True, exist_ok=True)
    (root / 'runs').mkdir(parents=True, exist_ok=True)
    agents = root / 'AGENTS.md'
    if not agents.exists():
        agents.write_text(
            f"# {clean}\n\nProject workspace for DNA. "
            f"Instructions, memory notes, and run ledgers live here.\n",
            encoding='utf-8',
        )
    return root


def list_projects() -> list[str]:
    """Return sorted project names (dirs only)."""
    base = _base_dir()
    if not base.exists():
        return []
    try:
        return sorted(p.name for p in base.iterdir() if p.is_dir())
    except OSError:
        return []


def get_active_project() -> str | None:
    """Active project name from session (None = global mode)."""
    from core.session import get as session_get
    return session_get('active_project')


def set_active_project(name: str | None) -> str | None:
    """Set (or clear with None) the active project. Returns sanitized name."""
    from core.session import update as session_update
    if name is None:
        session_update('active_project', None)
        return None
    clean = sanitize_name(name)
    if not clean:
        raise ValueError(f"Invalid project name: {name!r}")
    ensure_project(clean)
    session_update('active_project', clean)
    return clean


def append_memory(name: str, text: str) -> Path:
    """Append a timestamped memory note to the project."""
    clean = sanitize_name(name)
    if not clean:
        raise ValueError(f"Invalid project name: {name!r}")
    root = ensure_project(clean)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = root / 'memory' / f'{stamp}.md'
    path.write_text(text.strip() + '\n', encoding='utf-8')
    return path


def append_run(name: str, title: str, body: str, max_chars: int = 4000) -> Path:
    """Append a run-ledger entry (plan + results) to the project."""
    clean = sanitize_name(name)
    if not clean:
        raise ValueError(f"Invalid project name: {name!r}")
    root = ensure_project(clean)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    trimmed = (body or '').strip()[:max_chars]
    path = root / 'runs' / f'{stamp}.md'
    path.write_text(f"# {title.strip()}\n\n{trimmed}\n", encoding='utf-8')
    return path


def read_context_section(name: str | None, max_chars: int = 2200) -> str:
    """Build the LLM prompt section for a project (instructions + recent notes).

    Returns '' when no project is active or the project has no content.
    """
    clean = sanitize_name(name or '')
    if not clean:
        return ''
    root = project_root(clean)
    if not root.exists():
        return ''
    parts = []
    agents = root / 'AGENTS.md'
    try:
        if agents.exists():
            instructions = agents.read_text(encoding='utf-8').strip()[:800]
            if instructions:
                parts.append(f'PROJECT {clean} INSTRUCTIONS:\n{instructions}')
    except OSError:
        pass
    try:
        mem_dir = root / 'memory'
        if mem_dir.exists():
            notes = sorted(mem_dir.glob('*.md'))[-3:]
            chunks = []
            for n in notes:
                try:
                    chunks.append(n.read_text(encoding='utf-8').strip()[:600])
                except OSError:
                    continue
            if chunks:
                parts.append('PROJECT MEMORY NOTES:\n' + '\n---\n'.join(chunks))
    except OSError:
        pass
    section = '\n\n'.join(parts).strip()
    return section[:max_chars]
