"""
core/window_monitor.py
Proactive Window Awareness Monitor
Watches the active window in background, alerts DNA when user switches
to a recognised context (job portal, data file, AI chat, etc.)
"""

import logging
import threading
import time

from config import WINDOW_MONITOR_INTERVAL, WINDOW_ALERT_DELAY
from core.session import get as session_get

logger = logging.getLogger('dna.core.window_monitor')

# ── Window Context Map ────────────────────────────────────────────────────────
# key: substring to match in window title (lowercase)
# value: (context_label, proactive_message or None)
# None = recognised but don't proactively speak (too generic)

WINDOW_CONTEXTS = {
    # Job portals
    "internshala":      ("job_portal",
                         "Looks like you are on Internshala. "
                         "Want me to search for fresher Data Analyst openings?"),
    "naukri":           ("job_portal",
                         "Naukri is open. Want me to pull up job listings for you?"),
    "linkedin":         ("job_portal",
                         "LinkedIn is open. Shall I check for Data Analyst openings?"),
    "indeed":           ("job_portal",
                         "You are on Indeed. Want me to search for fresher DA roles?"),

    # AI tools
    "claude":           ("ai_chat",
                         "Claude is open. Want me to type something for you?"),
    "chatgpt":          ("ai_chat",
                         "ChatGPT is open. Want me to type a prompt?"),
    "gemini":           ("ai_chat", None),

    # Dev tools
    "visual studio code": ("coding",
                           "VS Code is open. Want me to run a script or open a file?"),
    "vscode":             ("coding", None),
    "github":             ("coding",
                           "GitHub is open. Need help with anything?"),
    "jupyter":            ("data",
                           "Jupyter is open. Want me to help with your notebook?"),

    # Data tools
    "excel":            ("data",
                         "Excel is open. Want me to summarise or chart this data?"),
    "tableau":          ("data", None),
    "power bi":         ("data", None),

    # Productivity
    "notion":           ("notes", None),
    "gmail":            ("email",
                         "Gmail is open. Want me to help with anything?"),
    "outlook":          ("email", None),

    # Generic browser — too broad to alert
    "chrome":           ("browser", None),
    "firefox":          ("browser", None),
    "edge":             ("browser", None),
}


# ── Monitor ───────────────────────────────────────────────────────────────────

class WindowMonitor(threading.Thread):
    """
    Background daemon that watches the active window.
    Fires a proactive spoken alert when user lands on a recognised context
    and stays there for WINDOW_ALERT_DELAY seconds.
    """

    def __init__(self):
        super().__init__(daemon=True, name='DNAWindowMonitor')
        self._last_window     = ""
        self._window_since    = 0.0
        self._alerted_windows = set()   # don't repeat alerts this session
        self._active          = True

    def run(self):
        # Lazy import — pygetwindow may not be installed
        try:
            import pygetwindow as gw
            self._gw = gw
        except ImportError:
            logger.warning('pygetwindow not installed. Window monitoring disabled.')
            return

        logger.info('Window monitor started (interval=%ds, delay=%ds)',
                     WINDOW_MONITOR_INTERVAL, WINDOW_ALERT_DELAY)

        while self._active:
            try:
                self._check()
            except Exception:
                pass
            time.sleep(WINDOW_MONITOR_INTERVAL)

    def _check(self):
        win = self._gw.getActiveWindow()
        if not win or not win.title:
            return

        title = win.title.lower().strip()

        # Window changed — reset timer
        if title != self._last_window:
            self._last_window  = title
            self._window_since = time.time()
            return

        # User has been on this window long enough
        elapsed = time.time() - self._window_since
        if elapsed < WINDOW_ALERT_DELAY:
            return

        # Already alerted for this window this session
        if title in self._alerted_windows:
            return

        # Don't interrupt if DNA is speaking or not listening
        if session_get('is_speaking') or not session_get('is_listening'):
            return

        # Match against known contexts
        for keyword, (context, message) in WINDOW_CONTEXTS.items():
            if keyword in title and message:
                try:
                    from pipeline.tts import speak
                    speak(message)
                except Exception as e:
                    logger.error('Window monitor TTS failed: %s', e)
                self._alerted_windows.add(title)
                break

    def reset_alerts(self):
        """Call this to allow alerts to fire again (e.g. new session)."""
        self._alerted_windows.clear()

    def stop(self):
        self._active = False


# ── Expose current context for LLM ───────────────────────────────────────────

def get_current_context() -> str:
    """
    Return a short context string about the active window.
    Injected into LLM prompt so it knows what the user is doing.
    Example: "User is currently in VS Code (coding context)."
    """
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        if not win or not win.title:
            return ""
        title = win.title.lower()
        for keyword, (context, _) in WINDOW_CONTEXTS.items():
            if keyword in title:
                return f"User is currently in {win.title} ({context} context)."
        return f"User is currently in {win.title}."
    except Exception:
        return ""
