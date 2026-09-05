# agents/titan_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage
try:
    from skills.system_skill import TOOLS as SYSTEM_TOOLS
except Exception:
    SYSTEM_TOOLS = {}

logger = logging.getLogger('dna.agent.titan')

class TitanAgent(AgentBase):
    """TITAN — System Control Agent.
    
    Model Assignment: none — deterministic direct execution (fuzzy cases escalate to NEXUS).
    Responsibilities: OS volume, brightness, power controls, window execution.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("TITAN", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        return {"status": "ready", "detail": "TITAN system control agent is online."}

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_titan"
        start_time = time.perf_counter()

        logger.info("[%s] Executing system command: %r", self.agent_id, task)
        self.log_event(f"Executing system command: '{task}'", "info")

        try:
            refused = (context or {}).get("refused_dangerous")
            if refused:
                try:
                    from core.safety import get_danger_warning
                    result = get_danger_warning(refused)
                except Exception:
                    result = (f"Boss, '{refused}' needs voice confirmation. "
                              f"Say it plainly and confirm when asked.")
            else:
                tool_name = (context or {}).get("tool_name")
                tool_args = (context or {}).get("tool_args", {})

                if tool_name and tool_name in SYSTEM_TOOLS:
                    result = SYSTEM_TOOLS[tool_name](**tool_args)
                else:
                    result = (f"Boss, I couldn't map '{task}' to a system action. "
                              f"Try volume, brightness, mute, opening or closing an app by name.")

            self.log_event(f"System action done: {str(result)[:120]}...", "success")

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="system_action_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] System control failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="system_action_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg
