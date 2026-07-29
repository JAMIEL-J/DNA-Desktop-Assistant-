# core/nexus.py
import logging
import time
import uuid
import json
from datetime import datetime
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage
from pipeline.llm_agent import handle_complex_command
from core.skill_registry import get_tool_map

from agents.jarvis_agent import JarvisAgent
from agents.cipher_agent import CipherAgent
from agents.titan_agent import TitanAgent
from agents.argus_agent import ArgusAgent
from agents.hermes_agent import HermesAgent
from agents.vanguard_agent import VanguardAgent
from agents.forge_agent import ForgeAgent

logger = logging.getLogger('dna.nexus')

class NexusOrchestrator(AgentBase):
    def __init__(self, blackboard: Blackboard):
        super().__init__("NEXUS", blackboard)
        self.state = AgentState.READY
        # Register Specialist Agents
        self.jarvis = JarvisAgent(blackboard)
        self.cipher = CipherAgent(blackboard)
        self.titan = TitanAgent(blackboard)
        self.argus = ArgusAgent(blackboard)
        self.hermes = HermesAgent(blackboard)
        self.vanguard = VanguardAgent(blackboard)
        self.forge = ForgeAgent(blackboard)

    def diagnose(self) -> dict:
        return {
            "status": "ready",
            "detail": "NEXUS orchestrator is online and active with 7 specialist sub-agents.",
            "agents": {
                "JARVIS": self.jarvis.diagnose(),
                "CIPHER": self.cipher.diagnose(),
                "TITAN": self.titan.diagnose(),
                "ARGUS": self.argus.diagnose(),
                "HERMES": self.hermes.diagnose(),
                "VANGUARD": self.vanguard.diagnose(),
                "FORGE": self.forge.diagnose(),
            }
        }

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or f"task_{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()
        try:
            # Check context / intent hints for routing to specialist sub-agents
            active_file = self.blackboard.get("active_file")
            task_lower = (task or "").lower()
            # Swarm Agent Status Roll Call Query
            if any(phrase in task_lower for phrase in ['status of all agents', 'agent status', 'all agents status', 'agent roll call', 'swarm status']):
                diag = self.diagnose()
                agents_summary = ", ".join([f"{name} ({info['status']})" for name, info in diag['agents'].items()])
                result = f"All 7 sub-agents are online and ready, boss: {agents_summary}."
            # Explicit sub-agent targeting (e.g., "CIPHER run job search", "ARGUS check screen")
            elif 'cipher' in task_lower:
                logger.info("[%s] Explicit command signal targeting CIPHER Agent", self.agent_id)
                msg = self.cipher.execute(task, {"task_id": task_id, "file_path": active_file})
                result = msg.payload.get("result", "")
            elif 'argus' in task_lower:
                logger.info("[%s] Explicit command signal targeting ARGUS Agent", self.agent_id)
                msg = self.argus.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif 'hermes' in task_lower:
                logger.info("[%s] Explicit command signal targeting HERMES Agent", self.agent_id)
                msg = self.hermes.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif 'vanguard' in task_lower:
                logger.info("[%s] Explicit command signal targeting VANGUARD Agent", self.agent_id)
                msg = self.vanguard.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif 'forge' in task_lower:
                logger.info("[%s] Explicit command signal targeting FORGE Agent", self.agent_id)
                msg = self.forge.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif 'jarvis' in task_lower:
                logger.info("[%s] Explicit command signal targeting JARVIS Agent", self.agent_id)
                msg = self.jarvis.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['screen', 'screenshot', 'error on screen', 'look at']):
                logger.info("[%s] Routing task to ARGUS Vision Agent", self.agent_id)
                msg = self.argus.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['job', 'jobs', 'resume', 'hiring']):
                logger.info("[%s] Routing task to CIPHER / FORGE Agent", self.agent_id)
                msg = self.cipher.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['what is', 'who is', 'explain', 'tell me', 'why', 'how to', 'chat']):
                logger.info("[%s] Routing task to JARVIS Chat Agent", self.agent_id)
                msg = self.jarvis.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            else:
                tool_map = get_tool_map()
                result = handle_complex_command(task, tool_map)
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            payload = {
                "result": result,
                "latency_ms": latency_ms
            }
            
            # Post success message to Blackboard
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="nexus_execution_complete",
                payload=payload,
                status="success",
                task_id=task_id
            )
            self.blackboard.post(msg)
            
            # Emit structured JSON telemetry log (Section 15)
            telemetry = {
                "agent_id": self.agent_id,
                "task_id": task_id,
                "action": "execute_task",
                "status": "success",
                "latency_ms": latency_ms,
                "tokens_in": 0,
                "tokens_out": 0,
                "model": "gemini-3.5-flash-lite",
                "provider": "google",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            logger.info("TELEMETRY: %s", json.dumps(telemetry))
            
            self.transition(AgentState.READY)
            return msg

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("[%s] Execution failed: %s", self.agent_id, e, exc_info=True)
            payload = {"error": str(e), "latency_ms": latency_ms}
            msg = BlackboardMessage(
                agent_id=self.agent_id,
                action="nexus_execution_failed",
                payload=payload,
                status="error",
                task_id=task_id
            )
            self.blackboard.post(msg)
            
            # Emit telemetry error
            telemetry = {
                "agent_id": self.agent_id,
                "task_id": task_id,
                "action": "execute_task",
                "status": "error",
                "latency_ms": latency_ms,
                "tokens_in": 0,
                "tokens_out": 0,
                "model": "gemini-3.5-flash-lite",
                "provider": "google",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            logger.info("TELEMETRY: %s", json.dumps(telemetry))
            
            self.transition(AgentState.READY)
            return msg
