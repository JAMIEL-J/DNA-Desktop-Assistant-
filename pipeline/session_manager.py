from enum import Enum
import threading


class DNAState(Enum):
    SLEEPING = 'sleeping'
    ACTIVE = 'active'
    PROCESSING = 'processing'


_state_lock = threading.Lock()
_state = DNAState.SLEEPING


def get_state() -> DNAState:
    """Thread-safe state read for the main loop and background callers."""
    with _state_lock:
        return _state


def set_state(new_state: DNAState) -> DNAState:
    """Thread-safe state write. Returns the updated state."""
    global _state
    with _state_lock:
        _state = new_state
        return _state
