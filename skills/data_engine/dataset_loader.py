# skills/data_engine/dataset_loader.py
import difflib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.session import update as session_update
from .catalog import DataCatalog
from .profiler import DataProfiler

logger = logging.getLogger('dna.data_engine.dataset_loader')


def _clean_keyword(raw_keyword: str) -> str:
    """Strip common STT prefixes and stop words from spoken load commands."""
    kw = raw_keyword.lower().strip()
    stopwords = [
        'load', 'the', 'my', 'data', 'dataset', 'file', 'csv', 'excel',
        'please', 'hey', 'jarvis', 'open', 'use', 'bring', 'up', 'a'
    ]
    words = kw.split()
    filtered = [w for w in words if w not in stopwords]
    clean = " ".join(filtered).strip()
    return clean if clean else raw_keyword.strip()


def find_best_matching_dataset(keyword: str) -> Optional[Path]:
    """Search for a dataset using exact, substring, and fuzzy matching."""
    catalog = DataCatalog()
    clean_kw = _clean_keyword(keyword)

    # 1. Search catalog & filesystem candidates
    candidates: List[Path] = catalog._search_data_files(clean_kw)
    if candidates:
        return candidates[0]

    # 2. Broader search in project data/ and workspace if no direct match
    project_root = Path(__file__).parent.parent.parent
    search_dirs = [
        project_root / 'data',
        project_root,
        Path.home() / 'Downloads',
        Path.home() / 'Documents',
        Path.home() / 'Desktop'
    ]

    valid_exts = {'.csv', '.xlsx', '.xls'}
    all_files: List[Path] = []
    for s_dir in search_dirs:
        if s_dir.exists():
            try:
                for p in s_dir.rglob('*'):
                    if p.is_file() and p.suffix.lower() in valid_exts:
                        if not any(part.startswith('.') or part in ('node_modules', '.venv', '__pycache__') for part in p.parts):
                            all_files.append(p)
            except Exception:
                pass

    if not all_files:
        return None

    # Map stems for fuzzy comparison
    stem_map = {f.stem.lower(): f for f in all_files}
    stems = list(stem_map.keys())

    # Fuzzy match using difflib
    close_matches = difflib.get_close_matches(clean_kw, stems, n=1, cutoff=0.3)
    if close_matches:
        matched_stem = close_matches[0]
        logger.info('Fuzzy matched keyword "%s" to dataset "%s"', keyword, stem_map[matched_stem])
        return stem_map[matched_stem]

    # Partial token overlap check
    kw_tokens = set(clean_kw.split())
    best_file = None
    best_score = 0
    for f in all_files:
        f_tokens = set(f.stem.lower().replace('-', ' ').replace('_', ' ').split())
        overlap = len(kw_tokens.intersection(f_tokens))
        if overlap > best_score:
            best_score = overlap
            best_file = f

    return best_file


def load_dataset_by_keyword(keyword: str) -> str:
    """Load a dataset by spoken keyword or name and update session state."""
    logger.info('Executing dataset load for keyword: %s', keyword)
    matched_path = find_best_matching_dataset(keyword)

    if not matched_path or not matched_path.exists():
        msg = f"Sorry sir, I couldn't find any dataset matching '{keyword}' in your data directory or workspace."
        logger.warning(msg)
        return msg

    str_path = str(matched_path.resolve())

    # Profile & register dataset
    profiler = DataProfiler()
    profile = profiler.profile(str_path)
    catalog = DataCatalog()
    catalog.register_dataset(str_path, profile)

    # Sync session state
    session_update('active_file', str_path)
    session_update('active_skill', 'data')

    dataset_name = matched_path.stem.replace('_', ' ').replace('-', ' ').title()
    row_count = profile.get('row_count', 0)
    col_count = profile.get('column_count', 0)

    # Speak verbal confirmation
    verbal_msg = (
        f"Yes sir. The {dataset_name} dataset is loaded and ready for analysis with "
        f"{row_count:,} rows and {col_count} columns. What would you like to explore?"
    )
    try:
        from pipeline.tts import speak
        speak(f"Yes sir, {dataset_name} dataset loaded.")
    except Exception as e:
        logger.debug("TTS speak failed: %s", e)

    return verbal_msg
