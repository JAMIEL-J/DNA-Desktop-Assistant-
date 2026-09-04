# agents/hermes_agent.py
import logging
import time
from core.agent_base import AgentBase, AgentState
from core.blackboard import Blackboard, BlackboardMessage

try:
    from skills.web_skill import web_search, fetch_and_summarize
except Exception:
    web_search = fetch_and_summarize = None

try:
    from skills import playwright_skill
except Exception:
    playwright_skill = None  # type: ignore

logger = logging.getLogger('dna.agent.hermes')

# Verbs that need a live browser (Playwright MCP), not just search/scrape.
_AUTOMATION_KEYWORDS = (
    'click', 'fill', 'type into', 'press key', 'press enter',
    'automate', 'browser automation', 'take snapshot', 'page snapshot',
    'select option', 'fill form', 'submit form',
)

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
        detail = f"HERMES web agent is {status}."
        try:
            if playwright_skill is not None and playwright_skill.is_playwright_available():
                detail += " Playwright browser automation ready."
        except Exception:
            pass
        return {"status": status, "detail": detail}

    @staticmethod
    def _is_browser_automation(task_lower: str, context: dict | None) -> bool:
        """True when the task needs a live browser, not just search/scrape."""
        if (context or {}).get("playwright_action"):
            return True
        return any(k in task_lower for k in _AUTOMATION_KEYWORDS)

    def _execute_browser_automation(self, task: str, context: dict | None) -> str:
        """Run one Playwright step: direct action from context, else open+observe.

        Multi-step flows compose across turns: navigate+snapshot first so the
        next turn has element refs for click/type. Never invents refs.
        """
        import re
        ctx = context or {}
        if playwright_skill is None:
            return "Browser automation is unavailable (playwright skill failed to load)."

        action = ctx.get("playwright_action")
        if action:
            fn = getattr(playwright_skill, str(action), None)
            if not callable(fn):
                return f"Sorry boss, I don't know the browser action '{action}'."
            self.log_event(f"Playwright action: {action}", "info")
            try:
                return str(fn(**(ctx.get("playwright_args") or {})))
            except TypeError as e:
                return f"Sorry boss, that browser action needs different details: {e}"

        url_match = re.search(r'https?://[^\s\'")]+', task or "")
        if url_match and playwright_skill.is_playwright_available():
            url = url_match.group(0)
            self.log_event(f"Opening {url} in automated browser.", "info")
            nav = playwright_skill.browser_navigate(url)
            snap = playwright_skill.browser_snapshot()
            return (f"{nav}\n\nLive page snapshot — tell me what to click or fill "
                    f"next, boss:\n{snap}")
        if "snapshot" in (task or "").lower():
            return playwright_skill.browser_snapshot()
        return ("Tell me which page to open first, boss — e.g. "
                "'open https://example.com and click login'.")

    def execute(self, task: str, context: dict = None) -> BlackboardMessage:
        self.transition(AgentState.BUSY)
        task_id = (context or {}).get("task_id") or "task_hermes"
        start_time = time.perf_counter()

        logger.info("[%s] Processing web task: %r", self.agent_id, task)
        self.log_event(f"Processing web query: '{task}'", "info")

        try:
            task_lower = (task or "").lower()
            if any(greeting in task_lower for greeting in ['hello', 'hi', 'hey', 'status', 'who are you']) and len(task.split()) <= 4:
                result = "Hello boss! HERMES web agent online and ready for search or web intelligence tasks."
            elif self._is_browser_automation(task_lower, context):
                self.log_event("Routing to Playwright browser automation.", "info")
                result = self._execute_browser_automation(task, context)
            else:
                url = (context or {}).get("url")
                if url and fetch_and_summarize:
                    self.log_event(f"Fetching URL content: {url}", "info")
                    result = fetch_and_summarize(url)
                elif web_search:
                    self.log_event(f"Executing web search skill for: '{task}'", "info")
                    result = web_search(task)
                else:
                    result = "Web search skills are currently unavailable."

            self.log_event(f"Search complete: {result[:120]}...", "success")

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
