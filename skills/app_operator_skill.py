# skills/app_operator_skill.py
# ──────────────────────────────────────────────────────────────────────
# Universal desktop-app operator — app-agnostic primitives in the Cowork
# shape: open-if-needed, focus, drive via keyboard, read back state.
# No per-app code, no hardcoded hotkeys, no screen coordinates.
# All OS imports are lazy so the module loads even where
# pyautogui/pygetwindow are absent (graceful degradation at call time).
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import logging
import re
import time

logger = logging.getLogger('dna.skill.app_operator')

_HOTKEY_PART_RE = re.compile(r'^[a-z0-9_]+$')


def _find_windows(hint: str) -> list:
    """Fuzzy, case-insensitive window match. Returns [] when unavailable."""
    try:
        import pygetwindow as gw
    except Exception:
        return []
    try:
        hint_norm = (hint or "").strip().lower()
        if not hint_norm:
            return []
        wins = []
        for w in gw.getAllWindows():
            try:
                title = (w.title or "")
            except Exception:
                continue
            if not title.strip():
                continue
            t = title.lower()
            if hint_norm in t or t in hint_norm:
                wins.append(w)
        return wins
    except Exception as e:
        logger.debug("window search failed: %s", e)
        return []


def _is_process_running(process_names: list[str]) -> bool:
    """True if any named process is alive. False when psutil is unavailable."""
    try:
        import psutil
    except Exception:
        return False
    try:
        wanted = {p.lower() for p in process_names if p}
        for proc in psutil.process_iter(['name']):
            try:
                if (proc.info.get('name') or '').lower() in wanted:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def ensure_app_open(app_name: str, window_hint: str = "") -> str:
    """Ensure an app is running, launching it when needed.

    Checks open windows first, then the process table, then launches via
    open_app and polls for the window. App-agnostic: works for any app
    known to the alias/process maps (antigravity, spotify, vscode...).
    """
    from config import APP_PROCESS_MAP
    hint = (window_hint or app_name or "").strip()
    if not hint:
        return "Boss, tell me which app to open."

    if _find_windows(hint):
        return f"{app_name.title()} is already open, boss."

    candidates = [v for k, v in APP_PROCESS_MAP.items()
                  if hint.lower() in k.lower() or k.lower() in hint.lower()]
    seen = set()
    proc_names = [c for c in candidates if not (c in seen or seen.add(c))]
    if proc_names and _is_process_running(proc_names):
        return f"{app_name.title()} is already running, boss. Bringing it forward is next."

    try:
        from skills.system_skill import open_app
    except Exception as e:
        logger.error("open_app import failed: %s", e)
        return "Boss, the app launcher is unavailable right now."
    result = open_app(app_name)

    for _ in range(20):  # ~10s poll for the window to appear
        time.sleep(0.5)
        if _find_windows(hint):
            return f"{result} {app_name.title()} is now open, boss."
    return (f"{result} I launched it, boss, but its window is not visible yet — "
            f"it may still be starting.")


def focus_app_window(window_hint: str) -> str:
    """Focus a window by fuzzy title match (substring, case-insensitive).

    Unlike click_and_type this never clicks — focusing alone preserves
    editor/agent-bar context instead of destroying it with a center click.
    """
    if not (window_hint or "").strip():
        return "Boss, tell me which window to focus."
    matches = _find_windows(window_hint)
    if not matches:
        return (f"Boss, I could not find a window matching '{window_hint}'. "
                f"Is the app open?")
    try:
        matches[0].activate()
        time.sleep(0.4)
        return f"Focused '{matches[0].title}', boss."
    except Exception as e:
        logger.error("focus failed: %s", e)
        return f"Boss, I found the window but could not focus it: {e}"


def press_hotkey(keys: str) -> str:
    """Press a hotkey like 'ctrl+l' or 'ctrl+shift+p'. Generic across apps."""
    try:
        import pyautogui
    except Exception:
        return "Boss, keyboard control is unavailable on this machine."
    parts = [(p or "").strip().lower() for p in (keys or "").split("+")]
    parts = [p for p in parts if p]
    if not 1 <= len(parts) <= 4 or not all(_HOTKEY_PART_RE.match(p) and len(p) <= 12 for p in parts):
        return ("Boss, that hotkey looks invalid. Use a form like "
                "'ctrl+l' or 'ctrl+shift+p'.")
    try:
        if len(parts) == 1:
            pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)
        return f"Pressed {keys}, boss."
    except Exception as e:
        logger.error("hotkey failed: %s", e)
        return f"Boss, that keypress did not go through: {e}"


def focus_and_type(window_hint: str, text: str, press_enter: bool = False) -> str:
    """Focus a window (fuzzy) and type text into the focused control.

    No mouse click — safe for agent bars, editors, and chat inputs.
    Paths/names belonging to another app's project must be passed through
    verbatim in `text`; this tool never resolves folders itself.
    """
    if not (text or "").strip():
        return "Boss, there is no text to type."
    focused = focus_app_window(window_hint)
    if focused.startswith("Boss, I could not find") or "could not focus" in focused:
        return focused
    try:
        import pyautogui
    except Exception:
        return "Boss, keyboard control is unavailable on this machine."
    try:
        pyautogui.typewrite(text, interval=0.02)
        if press_enter:
            pyautogui.press('enter')
        preview = text[:60] + ('...' if len(text) > 60 else '')
        ending = " and sent." if press_enter else ", awaiting your send, boss."
        return f"Typed '{preview}'{ending}"
    except Exception as e:
        logger.error("focus_and_type failed: %s", e)
        return f"Boss, the typing did not go through: {e}"


# Skill module contract (auto-discovered by core/skill_registry.py)
TOOLS = {
    'ensure_app_open': ensure_app_open,
    'focus_app_window': focus_app_window,
    'press_hotkey': press_hotkey,
    'focus_and_type': focus_and_type,
}
