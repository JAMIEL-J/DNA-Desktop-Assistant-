# agents/jarvis_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage
from skills.chat_skill import chat, get_history_context, clear_chat_history

logger = logging.getLogger('dna.agent.jarvis')

class JarvisAgent(AgentBase):
    """JARVIS — Conversational & Persona Agent.
    
    Model Assignment: Gemini 3.5 Flash-Lite (Primary) / OpenRouter Gemma 4 fallback.
    Responsibilities: Conversational Q&A, multi-turn follow-ups, voice summaries.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("JARVIS", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        return {"status": "ready", "detail": "JARVIS chat agent is online."}

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_jarvis"
        start_time = time.perf_counter()

        logger.info("[%s] Processing query: %r", self.agent_id, task)

        try:
            # Delegate to conversational chat skill engine
            answer = chat(task)

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": answer,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="chat_response",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] Query execution failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="chat_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg
