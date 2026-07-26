# skills/data_skill.py
# ──────────────────────────────────────────────────────────────────────
# Data Skill — Thin adapter delegating to skills/data_engine/ package.
# ──────────────────────────────────────────────────────────────────────

import logging
from skills.data_engine import run_analysis, run_quick_analysis, recall_recent_data, load_dataset

logger = logging.getLogger('dna.skill.data')


def analyze_data(path: str, question: str) -> str:
    """Analyze a local data file. Delegates to data engine."""
    logger.info('data_skill delegating analyze_data to data_engine')
    return run_analysis(path=path, question=question)


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


TOOLS = {
    'analyze_data': analyze_data,
    'quick_analyze': quick_analyze,
    'recall_data': recall_data,
    'load_dataset': load_dataset_tool,
}
