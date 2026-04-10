# core/skill_registry.py
# ──────────────────────────────────────────────────────────────────────
# Skill Registry — Dynamically discovers and loads all tools
# ──────────────────────────────────────────────────────────────────────

import importlib
import logging
import os
from pathlib import Path

logger = logging.getLogger('dna.registry')

_TOOL_MAP = {}
_DISCOVERED = False


def discover_skills(skills_dir: str | Path = None) -> None:
    """Dynamically scan and load all *_skill.py modules and merge their TOOLS."""
    global _TOOL_MAP, _DISCOVERED
    _TOOL_MAP.clear()

    if skills_dir is None:
        skills_dir = Path(os.getcwd()) / 'skills'
    else:
        skills_dir = Path(skills_dir).resolve()

    if not skills_dir.exists():
        logger.error('Skills directory not found: %s', skills_dir)
        return

    logger.info('Scanning for skills in %s', skills_dir)

    for file_path in skills_dir.rglob('*_skill.py'):
        # Map file path to module namespace
        # e.g. "skills/system_skill.py" -> "skills.system_skill"
        rel_path = file_path.relative_to(skills_dir.parent)
        module_name = str(rel_path).replace('.py', '').replace(os.sep, '.')

        try:
            mod = importlib.import_module(module_name)
            if hasattr(mod, 'TOOLS') and isinstance(mod.TOOLS, dict):
                loaded_count = len(mod.TOOLS)
                
                # Check for collisions
                overlap = set(_TOOL_MAP.keys()).intersection(mod.TOOLS.keys())
                if overlap:
                    logger.warning('Tool name collision in %s: %s. Overwriting!', module_name, overlap)
                
                _TOOL_MAP.update(mod.TOOLS)
                logger.debug('Loaded %d tools from %s', loaded_count, module_name)
            else:
                logger.debug('Module %s has no valid TOOLS dict. Skipping.', module_name)
        except Exception as e:
            logger.error('Failed to load skill module %s: %s', module_name, str(e), exc_info=True)

    _DISCOVERED = True
    logger.info('Skill discovery complete. Loaded %d tools.', len(_TOOL_MAP))


def get_tool_map() -> dict:
    """Return the combined TOOLS dictionary."""
    if not _DISCOVERED:
        discover_skills()
    return _TOOL_MAP


def get_tool_names() -> list[str]:
    """Return a list of all loaded tool names."""
    if not _DISCOVERED:
        discover_skills()
    return list(_TOOL_MAP.keys())
