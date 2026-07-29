# core/session.py
# 1. stdlib
import logging
import threading

# 2. internal
from core.blackboard import Blackboard, BlackboardMessage

logger = logging.getLogger('dna.session')

# Instantiate the global Blackboard
_bb = Blackboard()

# Seed default states
DEFAULT_STATE = {
    'active_file': None,
    'active_app': None,
    'active_skill': None,
    'last_result': None,
    'last_df': None,
    'last_command': None,
    'is_listening': False,
    'assistant_state': 'sleeping',
    'is_speaking': False,
    'mic_level': 0.0,
    'is_running': True,
    'suppress_next_tts': False,
}

for k, v in DEFAULT_STATE.items():
    _bb._state[k] = v


def update(key: str, value) -> None:
    """Thread-safe state update."""
    with _bb._lock:
        _bb._state[key] = value
        logger.debug('Session update: %s', key)


def get(key: str, default=None):
    """Thread-safe state read."""
    # Reads don't lock per specification
    return _bb.get(key, default)


def snapshot() -> dict:
    """Return a copy of all session state."""
    return _bb.snapshot()


def get_blackboard() -> Blackboard:
    """Access the global blackboard instance."""
    return _bb
