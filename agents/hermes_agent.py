# agents/hermes_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage

try:
    from skills.web_skill import web_search, fetch_and_summarize
except Exception:
    web_search = fetch_and_summarize = None

logger = logging.getLogger('dna.agent.hermes')

class HermesAgent(AgentBase):
    """HERMES — Web & Browser Agent.
    
    Model Assignment: NVIDIA Nemotron (Secondary API Key — Tool Calling Specialist).
    Responsibilities: Web searches, page scraping, tool calling, online intelligence.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("HERMES", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        status = "ready" if web_search else "degraded"
        return {"status": status, "detail": f"HERMES web agent is {status}."}

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_hermes"
        start_time = time.perf_counter()

        logger.info("[%s] Processing web task: %r", self.agent_id, task)

        try:
            task_lower = (task or "").lower()
            if any(greeting in task_lower for greeting in ['hello', 'hi', 'hey', 'status', 'who are you']) and len(task.split()) <= 4:
                result = "Hello boss! HERMES web agent online and ready for search or web intelligence tasks."
            else:
                url = (context or {}).get("url")
                if url and fetch_and_summarize:
                    result = fetch_and_summarize(url)
                elif web_search:
                    result = web_search(task)
                else:
                    result = "Web search skills are currently unavailable."

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="web_task_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] Web task failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="web_task_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg
