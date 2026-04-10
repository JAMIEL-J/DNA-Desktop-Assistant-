# skills/learning_skill.py
# ──────────────────────────────────────────────────────────────────────
# Learning Skill
# Teaches DNA to memorise user preferences and custom aliases into SQLite.
# ──────────────────────────────────────────────────────────────────────

import logging

from pipeline.memory import save_alias, save_preference

logger = logging.getLogger('dna.skill.learning')


def learn_alias(alias_name: str, target_path: str) -> str:
    """Learn a new alias for an application or folder to use in future commands."""
    try:
        alias_cleaned = str(alias_name).lower().strip()
        target_cleaned = str(target_path).strip()
        
        save_alias(alias_cleaned, target_cleaned)
        logger.info('Learned alias: %s -> %s', alias_cleaned, target_cleaned)
        
        return f"Got it, from now on '{alias_name}' points to '{target_path}'."
    except Exception as e:
        logger.error('Failed to learn alias: %s', e, exc_info=True)
        return f"Could not save the alias: {str(e)}"


def learn_preference(key: str, value: str) -> str:
    """Learn a new user preference (e.g. favourite IDE, preferred web browser)."""
    try:
        key_cleaned = str(key).lower().strip()
        val_cleaned = str(value).strip()
        
        save_preference(key_cleaned, val_cleaned)
        logger.info('Learned preference: %s -> %s', key_cleaned, val_cleaned)
        
        return f"Noted. I have set your preference for {key} to {value}."
    except Exception as e:
        logger.error('Failed to learn preference: %s', e, exc_info=True)
        return f"Could not save the preference: {str(e)}"


TOOLS = {
    'learn_alias': learn_alias,
    'learn_preference': learn_preference,
}
