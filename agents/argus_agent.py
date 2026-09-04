# agents/argus_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage

try:
    from skills.screen_skill import read_screen, describe_screen
except Exception:
    read_screen = describe_screen = None

try:
    from skills.screen_skill import find_error_on_screen as find_error
except Exception:
    find_error = None

logger = logging.getLogger('dna.agent.argus')

class ArgusAgent(AgentBase):
    """ARGUS — Vision & Screen Agent.
    
    Model Assignment: Nemotron 3 Ultra (via NVIDIA NIM) / Moondream local fallback.
    Responsibilities: Screen OCR, active window UI inspection, visual error debugging.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("ARGUS", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        status = "ready" if read_screen else "degraded"
        return {"status": status, "detail": f"ARGUS vision agent is {status}."}

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_argus"
        start_time = time.perf_counter()

        logger.info("[%s] Processing vision task: %r", self.agent_id, task)
        self.log_event(f"Processing screen vision task: '{task}'", "info")

        try:
            task_lower = task.lower()
            if "error" in task_lower and find_error:
                self.log_event("Scanning screen for visual errors...", "info")
                result = find_error()
            elif "describe" in task_lower and describe_screen:
                self.log_event("Capturing and describing desktop screen...", "info")
                result = describe_screen()
            elif read_screen:
                self.log_event("Reading text from active screen...", "info")
                result = read_screen()
            else:
                result = "Screen vision skills are unavailable in current environment."

            self.log_event(f"Vision analysis completed: {result[:100]}...", "success")

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="vision_task_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] Vision task failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="vision_task_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg
