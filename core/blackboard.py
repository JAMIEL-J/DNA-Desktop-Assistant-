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

    def get_recent_history(self, limit: int = 5) -> List[dict]:
        """Returns formatted recent sub-agent execution outputs for LLM prompt context."""
        with self._lock:
            recent_msgs = self._history[-limit:]
            formatted = []
            for msg in recent_msgs:
                res_str = ""
                if isinstance(msg.payload, dict):
                    res_str = str(msg.payload.get("result") or msg.payload.get("error") or msg.payload)
                else:
                    res_str = str(msg.payload)

                # Cap individual message snippet length to avoid blowing prompt context
                if len(res_str) > 300:
                    res_str = res_str[:300] + "..."

                formatted.append({
                    "agent_id": msg.agent_id,
                    "action": msg.action,
                    "result": res_str,
                    "timestamp": msg.timestamp
                })
            return formatted

# Global singleton Blackboard instance for cross-module skill access
_GLOBAL_BLACKBOARD = Blackboard()

def get_global_blackboard() -> Blackboard:
    """Returns the shared global Blackboard instance."""
    return _GLOBAL_BLACKBOARD
