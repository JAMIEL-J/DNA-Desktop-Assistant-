# skills/data_skill.py
# ──────────────────────────────────────────────────────────────────────
# Data Skill — Thin adapter delegating to skills/data_engine/ package.
# ──────────────────────────────────────────────────────────────────────

import logging
from skills.data_engine import run_analysis, run_quick_analysis, recall_recent_data, load_dataset

logger = logging.getLogger('dna.skill.data')


def analyze_data(path: str, question: str, sheet: str | None = None) -> str:
    """Analyze a local data file. Delegates to data engine."""
    logger.info('data_skill delegating analyze_data to data_engine')
    kwargs = {'path': path, 'question': question}
    if sheet:
        kwargs['sheet'] = sheet
    return run_analysis(**kwargs)


def quick_analyze(question: str = "Give me a summary", keyword: str = "") -> str:
    """Find and analyze a data file by keyword. Delegates to data engine."""
    logger.info('data_skill delegating quick_analyze to data_engine')
    return run_quick_analysis(question=question, keyword=keyword)


def recall_data(question: str = "") -> str:
    """Recall the most recently analyzed dataset from persistent history."""
    logger.info('data_skill delegating recall_data to data_engine')
    return recall_recent_data(question=question)


def load_dataset_tool(keyword: str = "") -> str:
    """Load a dataset by keyword using fuzzy matching and set active session context."""
    logger.info('data_skill delegating load_dataset to data_engine')
    return load_dataset(keyword=keyword)


def open_datasets_tool(refs: str = "") -> str:
    """Open several datasets into one shared session for joins."""
    from skills.data_engine import open_datasets
    return open_datasets(refs=refs)


def suggest_join_keys_tool() -> str:
    """Propose join keys across the open datasets."""
    from skills.data_engine import suggest_join_keys
    return suggest_join_keys()


def join_datasets_tool(fact: str = "", dim: str = "", fact_key: str = "", dim_key: str = "") -> str:
    """LEFT-join fact to dimension on a key, with grain validation."""
    from skills.data_engine import join_datasets
    return join_datasets(fact=fact, dim=dim, fact_key=fact_key, dim_key=dim_key)


TOOLS = {
    'analyze_data': analyze_data,
    'quick_analyze': quick_analyze,
    'recall_data': recall_data,
    'load_dataset': load_dataset_tool,
    'open_datasets': open_datasets_tool,
    'suggest_join_keys': suggest_join_keys_tool,
    'join_datasets': join_datasets_tool,
}
