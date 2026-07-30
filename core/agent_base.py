# core/agent_base.py
from abc import ABC, abstractmethod
from enum import Enum
from core.blackboard import Blackboard, BlackboardMessage

class AgentState(Enum):
    UNINITIALIZED = "uninitialized"
    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"

class AgentBase(ABC):
    def __init__(self, agent_id: str, blackboard: Blackboard, model_config: dict = None):
        self.agent_id = agent_id
        self.blackboard = blackboard
        self.model_config = model_config or {}
        self.state = AgentState.UNINITIALIZED
        self._scratchpad: dict = {}  # private memory

    @abstractmethod
    def diagnose(self) -> dict:
        """Run startup diagnostic. Returns {'status': 'ready'|'degraded', 'detail': '...'}."""
        pass

    @abstractmethod
    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        """Execute a task. Returns a BlackboardMessage with result payload."""
        pass

    def report_status(self) -> str:
        """Returns formatted status line for boot sequence."""
        return f"[{self.agent_id}] State: {self.state.value}"

    def transition(self, new_state: AgentState) -> None:
        """Transition agent to a new lifecycle state."""
        self.state = new_state

    def log_event(self, message: str, level: str = 'info') -> None:
        """Log event to python logger and broadcast to UI terminal for this specific agent."""
        import logging
        logger = logging.getLogger(f'dna.agent.{self.agent_id.lower()}')
        if level == 'error':
            logger.error(message)
        elif level == 'warning':
            logger.warning(message)
        else:
            logger.info(message)

        try:
            from ui.window import broadcast_agent_log
            broadcast_agent_log(self.name, message, level)
        except Exception:
            pass

