# core/blackboard.py
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, List
from datetime import datetime

@dataclass
class BlackboardMessage:
    agent_id: str              # e.g. "CIPHER", "JARVIS"
    action: str                # e.g. "analysis_complete", "query_result"
    payload: dict              # the actual data (structured JSON)
    status: str = "success"    # "success" | "error" | "partial"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    task_id: Optional[str] = None  # correlation ID for multi-step tasks

class Blackboard:
    """Thread-safe shared state store. Single-writer lock prevents concurrent stomping."""
    def __init__(self):
        self._state: dict = {}
        self._lock = threading.Lock()
        self._history: List[BlackboardMessage] = []

    def get(self, key: str, default=None) -> Any:
        """Any agent can read. No lock required for reads."""
        return self._state.get(key, default)

    def post(self, msg: BlackboardMessage) -> None:
        """Write access. Acquires lock to prevent concurrent writes."""
        with self._lock:
            self._state[msg.action] = msg.payload
            self._state["last_agent"] = msg.agent_id
            self._state["last_update"] = msg.timestamp
            self._history.append(msg)

    def snapshot(self) -> dict:
        """Returns compact state dict (~100 tokens) for orchestrator context."""
        return dict(self._state)
