# 1. stdlib
import logging
import threading

logger = logging.getLogger('dna.session')

_lock = threading.Lock()
_state = {
    'active_file': None,
    'active_app': None,
    'last_result': None,
    'last_df': None,
    'last_command': None,
    'is_listening': False,
}


def update(key: str, value) -> None:
    """Thread-safe state update."""
    with _lock:
        _state[key] = value
        logger.debug('Session update: %s', key)


def get(key: str, default=None):
    """Thread-safe state read."""
    with _lock:
        return _state.get(key, default)


def snapshot() -> dict:
    """Return a copy of all session state."""
    with _lock:
        return dict(_state)
