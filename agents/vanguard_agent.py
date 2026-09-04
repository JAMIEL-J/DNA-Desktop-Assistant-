# agents/vanguard_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage

try:
    from skills.organizer_skill import organize_downloads, organize_folder
except Exception:
    organize_downloads = organize_folder = None

try:
    from skills.file_skill import list_files
except Exception:
    list_files = None

logger = logging.getLogger('dna.agent.vanguard')

class VanguardAgent(AgentBase):
    """VANGUARD — File & Storage Agent.
    
    Model Assignment: Mistral Nemotron (fuzzy resolver) / Direct Python.
    Responsibilities: File system operations, download organization, workspace indexing.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("VANGUARD", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        status = "ready" if organize_downloads else "degraded"
        return {"status": status, "detail": f"VANGUARD storage agent is {status}."}

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_vanguard"
        start_time = time.perf_counter()

        logger.info("[%s] Processing storage task: %r", self.agent_id, task)
        self.log_event(f"Processing storage task: '{task}'", "info")

        try:
            task_lower = task.lower()
            if "download" in task_lower and organize_downloads:
                result = organize_downloads()
            elif "list" in task_lower and list_files:
                path = (context or {}).get("path", ".")
                result = list_files(path)
            elif organize_folder:
                path = (context or {}).get("path", ".")
                result = organize_folder(path)
            else:
                result = "Storage skills are currently unavailable."

            self.log_event(f"Storage task done: {str(result)[:120]}...", "success")

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="storage_task_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] Storage task failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="storage_task_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg
