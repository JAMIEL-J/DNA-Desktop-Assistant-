# agents/cipher_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage
from skills.data_engine import run_analysis

logger = logging.getLogger('dna.agent.cipher')

class CipherAgent(AgentBase):
    """CIPHER — Data Analyst Agent.
    
    Model Assignment: DeepSeek V4 Flash (via NVIDIA NIM) / OpenRouter fallback.
    Design Rule: Compute-Then-Narrate (DuckDB aggregation before LLM analysis).
    Responsibilities: SQL execution, dataset profiling, analytical reports.
    """
    def __init__(self, blackboard: Blackboard):
        super().__init__("CIPHER", blackboard)
        self.state = AgentState.READY

    def diagnose(self) -> dict:
        return {"status": "ready", "detail": "CIPHER data engine agent is online."}

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_cipher"
        start_time = time.perf_counter()

        logger.info("[%s] Processing data task: %r", self.agent_id, task)
        self.log_event(f"Processing analytical query: '{task}'", "info")

        try:
            active_file = (context or {}).get("file_path") or self.blackboard.get("active_file")
            
            if active_file:
                self.log_event(f"Running data engine analysis on active file: {active_file}", "info")
                result = run_analysis(active_file, task)
                self.log_event("Data analysis completed successfully.", "success")
            else:
                result = "Please specify or load a dataset file path for me to analyze, boss."
                self.log_event("No active dataset specified for analytical query.", "warn")

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "active_file": active_file,
                "latency_ms": latency_ms
            }

            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="data_analysis_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)

            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            logger.warning("[%s] NVIDIA execution failed/rate-limited: %s. Attempting OpenRouter Gemma 4 fallback.", self.agent_id, e)
            try:
                from pipeline.openrouter_client import call_openrouter_fallback
                fallback_resp = call_openrouter_fallback(
                    prompt=f"Perform data task: {task}",
                    system_instruction="You are CIPHER, expert data analyst.",
                    context=self.blackboard.snapshot()
                )
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                msg = BlackboardMessage(
                    agent_id=self.agent_id,
                    action="data_analysis_complete",
                    payload={"result": fallback_resp, "fallback_used": True, "latency_ms": latency_ms},
                    status="success",
                    task_id=task_id
                )
                self.blackboard.post(msg)
                self.transition(AgentState.READY)
                return msg
            except Exception as fb_err:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                logger.error("[%s] Both primary and OpenRouter fallback failed: %s", self.agent_id, fb_err, exc_info=True)
                payload = {"error": str(fb_err), "latency_ms": latency_ms}
                msg = BlackboardMessage(
                    agent_id=self.agent_id,
                    action="data_analysis_failed",
                    payload=payload,
                    status="error",
                    task_id=task_id
                )
                self.blackboard.post(msg)

                self.transition(AgentState.READY)
                return msg
