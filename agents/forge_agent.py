# agents/forge_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage

try:
    from skills.job_search_skill import enter_job_search_mode, search_role, ROLE_QUERIES
except Exception:
    enter_job_search_mode = search_role = None
    ROLE_QUERIES = {}

logger = logging.getLogger('dna.agent.forge')

class ForgeAgent(AgentBase):
    """FORGE — Career & Resume Agent.
    
    Model Assignment: Gemini 3.5 Flash-Lite.
    Responsibilities: Resume matching, job scraping, skill gap evaluation.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("FORGE", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        status = "ready" if enter_job_search_mode else "degraded"
        return {"status": status, "detail": f"FORGE career agent is {status}."}

    @staticmethod
    def _extract_role(task: str) -> str | None:
        """Pull a known role out of free text ('find DATA ANALYST jobs' → 'data analyst')."""
        lowered = (task or "").lower()
        for role in sorted((ROLE_QUERIES or {}), key=len, reverse=True):
            if role != "all" and role in lowered:
                return role
        return None

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_forge"
        start_time = time.perf_counter()

        logger.info("[%s] Processing career task: %r", self.agent_id, task)
        self.log_event(f"Processing career task: '{task}'", "info")

        try:
            role = (context or {}).get("role") or self._extract_role(task)
            if role and search_role:
                result = search_role(role)
            elif enter_job_search_mode:
                result = enter_job_search_mode()
            else:
                result = "Career operations skills are currently unavailable."

            self.log_event(f"Career task done: {str(result)[:120]}...", "success")

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="career_task_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] Career task failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="career_task_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg
