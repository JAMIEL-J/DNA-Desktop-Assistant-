# skills/playwright_skill.py
# ──────────────────────────────────────────────────────────────────────
# Playwright browser automation via Microsoft Playwright MCP server.
# Lazy singleton MCP client (spawns `npx @playwright/mcp@latest` on first
# tool call, never on import) with graceful degradation when Node/npx
# is unavailable. Auto-discovered through TOOLS by skill_registry.
# Schemas verified against @playwright/mcp v0.0.80 tools/list.
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import logging
import shutil
import threading
from typing import Any

# 2. internal
from core.mcp_host import MCPHost

logger = logging.getLogger('dna.skill.playwright')

_MCP_COMMAND = ["npx", "@playwright/mcp@latest"]

_client_lock = threading.Lock()
_client: MCPHost | None = None


def _get_client() -> MCPHost:
    """Return the shared Playwright MCP client, starting it on first use."""
    global _client
    with _client_lock:
        if _client is not None and _client.is_running:
            return _client
        host = MCPHost(_MCP_COMMAND)
        host.connect()  # start + initialize handshake (tolerant)
        _client = host
        return _client


def is_playwright_available() -> bool:
    """Fast check: Node/npx present (no browser spawned)."""
    return shutil.which("npx") is not None


def _format_content(res: Any) -> str:
    """Render MCP content blocks (list of {type,text} / {type,ref}) to speech-friendly text."""
    try:
        if res is None:
            return "Done."
        if isinstance(res, str):
            return res or "Done."
        if isinstance(res, dict):
            if res.get("isError"):
                inner = _format_content(res.get("content"))
                return f"Browser action reported an error: {inner}"
            if "content" in res:
                return _format_content(res["content"])
            return str(res)
        if isinstance(res, list):
            parts = []
            for block in res:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(str(block.get("text", "")))
                    elif "ref" in block:
                        parts.append(f"[{block.get('type', 'ref')}: {block.get('ref')}]")
                    else:
                        parts.append(str(block))
                else:
                    parts.append(str(block))
            text = "\n".join(p for p in parts if p).strip()
            return text or "Done."
        return str(res)
    except Exception as e:
        logger.error("playwright format failed: %s", e)
        return "Browser action completed."


def _call(tool: str, args: dict) -> str:
    """Invoke one Playwright MCP tool with graceful degradation."""
    if not is_playwright_available():
        return ("Playwright browser automation is unavailable right now "
                "(Node/npx not found). I can still do a regular web search instead.")
    try:
        client = _get_client()
        res = client.call_tool(tool, args)
        text = _format_content(res)
        # Cap spoken snapshots so TTS/UI stays readable.
        if len(text) > 1500:
            text = text[:1500] + "\n... (snapshot truncated, boss.)"
        return text
    except Exception as e:
        logger.error("playwright %s failed: %s", tool, e)
        return f"Sorry boss, the browser action '{tool}' ran into a problem: {str(e)[:200]}"


def browser_navigate(url: str) -> str:
    """Navigate the automated browser to a URL and report what loaded."""
    return _call("browser_navigate", {"url": url.strip()})


def browser_snapshot() -> str:
    """Capture the current page accessibility snapshot (elements + refs for click/type)."""
    return _call("browser_snapshot", {})


def browser_click(target: str, element: str = "") -> str:
    """Click a page element by its snapshot ref (target), with optional element description.

    Get `target` refs from browser_snapshot first.
    """
    args: dict[str, Any] = {"target": target}
    if element:
        args["element"] = element
    return _call("browser_click", args)


def browser_type(target: str, text: str, element: str = "", submit: bool = False) -> str:
    """Type text into a page element (target ref from snapshot). Set submit=True to press Enter after."""
    args: dict[str, Any] = {"target": target, "text": text}
    if element:
        args["element"] = element
    if submit:
        args["submit"] = True
    return _call("browser_type", args)


def browser_fill_form(fields: str) -> str:
    """Fill multiple form fields in one call.

    Args:
        fields: JSON list of {name, type, ref, value} objects, e.g.
            '[{"name": "email", "type": "textbox", "ref": "e12", "value": "boss@corp.com"}]'
    """
    import json as _json
    try:
        parsed = _json.loads(fields) if isinstance(fields, str) else fields
    except Exception:
        return ("Sorry boss, I could not parse those form fields. "
                "Give them as a JSON list of name/type/ref/value objects.")
    return _call("browser_fill_form", {"fields": parsed})


def browser_press_key(key: str) -> str:
    """Press a keyboard key (e.g. Enter, Tab, Escape, ArrowDown)."""
    return _call("browser_press_key", {"key": key})


def browser_navigate_back() -> str:
    """Go back one page in the automated browser history."""
    return _call("browser_navigate_back", {})


def browser_evaluate(function: str) -> str:
    """Run a JavaScript function in the page context and return its result."""
    return _call("browser_evaluate", {"function": function})


def browser_console_messages(level: str = "error") -> str:
    """Read browser console messages (level: error, warning, info, debug)."""
    return _call("browser_console_messages", {"level": level})


def browser_wait_for(text: str = "", time: float = 0) -> str:
    """Wait for text to appear (or a fixed number of seconds) before continuing."""
    args: dict[str, Any] = {}
    if text:
        args["text"] = text
    if time:
        args["time"] = time
    return _call("browser_wait_for", args)


def browser_close() -> str:
    """Close the automated browser page."""
    return _call("browser_close", {})


# Skill module contract (auto-discovered by core/skill_registry.py)
TOOLS = {
    'browser_navigate': browser_navigate,
    'browser_snapshot': browser_snapshot,
    'browser_click': browser_click,
    'browser_type': browser_type,
    'browser_fill_form': browser_fill_form,
    'browser_press_key': browser_press_key,
    'browser_navigate_back': browser_navigate_back,
    'browser_evaluate': browser_evaluate,
    'browser_console_messages': browser_console_messages,
    'browser_wait_for': browser_wait_for,
    'browser_close': browser_close,
}
