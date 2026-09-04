# core/nexus.py
import logging
import time
import uuid
import json
from datetime import datetime
from typing import Optional
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
    def __init__(self, blackboard: Optional[Blackboard] = None):
        if blackboard is None:
            from core.blackboard import get_global_blackboard
            blackboard = get_global_blackboard()
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

    @staticmethod
    def _titan_context(task: str, task_id: str) -> dict:
        """Translate free text into TITAN's tool_name/tool_args context.

        Falls back to a bare task_id when no deterministic intent matches —
        TITAN then answers honestly instead of fake-executing.
        """
        ctx: dict = {"task_id": task_id}
        try:
            from pipeline.intent_router import match_simple_intent
            matched = match_simple_intent(task)
        except Exception:
            matched = None
        if matched:
            tool_name, args = matched
            try:
                from core.safety import is_tool_dangerous
                if is_tool_dangerous(tool_name):
                    # Never auto-execute dangerous tools from NEXUS: the
                    # voice confirmation flow lives in the router.
                    ctx["refused_dangerous"] = tool_name
                    return ctx
            except Exception:
                pass
            ctx["tool_name"] = tool_name
            ctx["tool_args"] = args
        return ctx

    def execute(self, task: str, context: dict | None = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or f"task_{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()
        try:
            # Check context / intent hints for routing to specialist sub-agents
            active_file = self.blackboard.get("active_file")
            task_lower = (task or "").lower()
            result = None
            # Swarm Agent Status Roll Call Query
            if any(phrase in task_lower for phrase in ['status of all agents', 'agent status', 'all agents status', 'agent roll call', 'swarm status']):
                diag = self.diagnose()
                agents_summary = ", ".join([f"{name} ({info['status']})" for name, info in diag['agents'].items()])
                result = f"All 7 sub-agents are online and ready, boss: {agents_summary}."
            # Explicit sub-agent targeting (e.g., "CIPHER run job search", "ARGUS check screen")
            # Require actionable words unless it's a greeting/status check
            words = set(task_lower.split())
            action_keywords = {'run', 'execute', 'search', 'analyze', 'check', 'start', 'fetch', 'scan', 'do', 'get', 'process', 'find', 'look', 'open'}
            has_action = bool(words & action_keywords)
            is_greeting = any(g in task_lower for g in ['hello', 'hi', 'hey', 'status', 'who are you', 'report']) or len(words) <= 3

            active_subagent = "JARVIS"
            if result is None and 'cipher' in task_lower:
                active_subagent = "CIPHER"
                logger.info("[%s] Explicit command signal targeting CIPHER Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! CIPHER data analyst agent online and ready for SQL, dataset profiling, or analytical reports."
                else:
                    msg = self.cipher.execute(task, {"task_id": task_id, "file_path": active_file})
                    result = msg.payload.get("result", "")
            elif 'argus' in task_lower:
                active_subagent = "ARGUS"
                logger.info("[%s] Explicit command signal targeting ARGUS Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! ARGUS vision agent online and standing by for screen inspections."
                else:
                    msg = self.argus.execute(task, {"task_id": task_id})
                    result = msg.payload.get("result", "")
            elif 'hermes' in task_lower:
                active_subagent = "HERMES"
                logger.info("[%s] Explicit command signal targeting HERMES Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! HERMES web agent online and ready for web intelligence and scraping."
                else:
                    msg = self.hermes.execute(task, {"task_id": task_id})
                    result = msg.payload.get("result", "")
            elif 'vanguard' in task_lower:
                active_subagent = "VANGUARD"
                logger.info("[%s] Explicit command signal targeting VANGUARD Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! VANGUARD security agent online and ready."
                else:
                    msg = self.vanguard.execute(task, {"task_id": task_id})
                    result = msg.payload.get("result", "")
            elif 'forge' in task_lower:
                active_subagent = "FORGE"
                logger.info("[%s] Explicit command signal targeting FORGE Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! FORGE career agent online and ready for resume and job matching tasks."
                else:
                    msg = self.forge.execute(task, {"task_id": task_id})
                    result = msg.payload.get("result", "")
            elif 'jarvis' in task_lower:
                active_subagent = "JARVIS"
                logger.info("[%s] Explicit command signal targeting JARVIS Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! JARVIS conversational core online and ready."
                else:
                    msg = self.jarvis.execute(task, {"task_id": task_id})
                    result = msg.payload.get("result", "")
            elif 'titan' in task_lower:
                active_subagent = "TITAN"
                logger.info("[%s] Explicit command signal targeting TITAN Agent", self.agent_id)
                if is_greeting and not has_action:
                    result = "Hello boss! TITAN system control online and ready for volume, brightness, apps, and power."
                else:
                    msg = self.titan.execute(task, self._titan_context(task, task_id))
                    result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['volume', 'brightness', 'mute', 'unmute',
                                               'shutdown', 'restart', 'lock screen',
                                               'wifi', 'bluetooth', 'battery']):
                active_subagent = "TITAN"
                logger.info("[%s] Routing task to TITAN System Agent", self.agent_id)
                msg = self.titan.execute(task, self._titan_context(task, task_id))
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['screen', 'screenshot', 'error on screen', 'look at']):
                active_subagent = "ARGUS"
                logger.info("[%s] Routing task to ARGUS Vision Agent", self.agent_id)
                msg = self.argus.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['job', 'jobs', 'resume', 'hiring']):
                active_subagent = "FORGE"
                logger.info("[%s] Routing task to FORGE Career Agent", self.agent_id)
                msg = self.forge.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['dataset', 'data analysis']):
                active_subagent = "CIPHER"
                logger.info("[%s] Routing task to CIPHER Data Agent", self.agent_id)
                msg = self.cipher.execute(task, {"task_id": task_id, "file_path": active_file})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['search', 'latest', 'episode', 'news', 'find', 'google', 'browse',
                                                     'click', 'fill form', 'fill the', 'type into', 'press key',
                                                     'automate', 'browser automation', 'playwright', 'snapshot']):
                active_subagent = "HERMES"
                logger.info("[%s] Routing task to HERMES Web Agent", self.agent_id)
                msg = self.hermes.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif any(w in task_lower for w in ['what is', 'who is', 'explain', 'tell me', 'why', 'how to', 'chat']):
                active_subagent = "NEXUS"
                logger.info("[%s] Routing task to NEXUS Chat Agent", self.agent_id)
                msg = self.jarvis.execute(task, {"task_id": task_id})
                result = msg.payload.get("result", "")
            elif result is None:
                tool_map = get_tool_map()
                result = handle_complex_command(task, tool_map)
            
            # Update session state with active sub-agent for UI attribution
            try:
                from core.session import update as session_update
                session_update('active_agent', active_subagent)
            except Exception:
                pass

            # Broadcast execution log output to target sub-agent UI terminal
            try:
                from ui.window import broadcast_agent_log
                broadcast_agent_log(active_subagent, f"Task completed: {result}", "success")
            except Exception:
                pass
            
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
