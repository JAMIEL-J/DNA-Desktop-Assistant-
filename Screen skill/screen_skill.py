"""
skills/screen_skill.py
DNA Screen Awareness, Smart Typing, and Vision Skill
Capabilities:
  1. type_text          - type into active or named window
  2. read_screen        - screenshot → Gemma 4 vision → spoken answer
  3. click_and_type     - focus window + click input + type
  4. find_and_type      - find text on screen then type near it (for forms)
"""

import pyautogui
import pygetwindow as gw
import google.generativeai as genai
import base64, io, time, re, os
from PIL import Image
from config import GEMINI_API_KEY, GEMINI_MODEL, SCREENSHOTS_DIR

genai.configure(api_key=GEMINI_API_KEY)

# ── Vision helper ─────────────────────────────────────────────────────────────

def _screenshot_to_base64() -> tuple[str, bytes]:
    """Take screenshot, return (base64_string, raw_bytes)."""
    screenshot = pyautogui.screenshot()
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    raw = buf.getvalue()
    return base64.b64encode(raw).decode(), raw

def _ask_gemma_vision(question: str, b64_image: str) -> str:
    """Send screenshot + question to Gemma 4 31B vision."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content([
        {"text": (
            "You are a screen reader assistant for a voice assistant called DNA. "
            "The user cannot see the screen — you describe it for them. "
            f"Answer this question about the screen: {question}. "
            "Keep your answer under 3 spoken sentences. "
            "If there is an error, quote it exactly. "
            "Plain text only. No markdown. No bullet points."
        )},
        {"inline_data": {"mime_type": "image/png", "data": b64_image}}
    ])
    # Strip thought block if thinking mode was on
    raw = response.text.strip()
    raw = re.sub(r'<\|channel\>thought.*?<channel\|>', '', raw, flags=re.DOTALL).strip()
    return raw


# ── Tool 1: Read Screen ───────────────────────────────────────────────────────

def read_screen(question: str = "What is on my screen?") -> str:
    """Take screenshot and answer a question about it using Gemma 4 vision."""
    try:
        b64, raw = _screenshot_to_base64()
        answer = _ask_gemma_vision(question, b64)

        # Save screenshot for reference (optional)
        if SCREENSHOTS_DIR:
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            path = os.path.join(SCREENSHOTS_DIR, f"screen_{int(time.time())}.png")
            with open(path, "wb") as f:
                f.write(raw)

        return answer
    except Exception as e:
        return f"Could not read the screen: {str(e)}"


def describe_screen() -> str:
    """Describe everything visible on the screen."""
    return read_screen("Describe everything you can see on this screen in detail.")


def find_error_on_screen() -> str:
    """Look for any error messages on the screen."""
    return read_screen(
        "Is there any error message, warning, or exception visible? "
        "If yes, quote it exactly. If no, say no errors found."
    )


# ── Tool 2: Type Text ─────────────────────────────────────────────────────────

def type_text(text: str, press_enter: bool = False) -> str:
    """Type text at the current cursor position."""
    try:
        time.sleep(0.2)
        pyautogui.typewrite(text, interval=0.03)
        if press_enter:
            pyautogui.press('enter')
        return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
    except Exception as e:
        return f"Could not type: {str(e)}"


def type_and_send(text: str) -> str:
    """Type text and press Enter — useful for chat inputs."""
    return type_text(text, press_enter=True)


def click_and_type(text: str, window_title: str = None,
                   press_enter: bool = False) -> str:
    """
    Focus a window, click to set cursor, then type.
    If window_title is None, types into current active window.
    """
    try:
        if window_title:
            matches = gw.getWindowsWithTitle(window_title)
            if not matches:
                return f"Could not find a window called {window_title}."
            win = matches[0]
            win.activate()
            time.sleep(0.4)  # let focus settle

        # Click centre of active window to ensure cursor
        active = gw.getActiveWindow()
        if active:
            cx = active.left + active.width // 2
            cy = active.top + active.height // 2
            pyautogui.click(cx, cy)
            time.sleep(0.2)

        pyautogui.typewrite(text, interval=0.03)
        if press_enter:
            pyautogui.press('enter')

        target = window_title or (active.title if active else "active window")
        return f"Typed into {target}."
    except Exception as e:
        return f"Could not type into window: {str(e)}"


def type_into_claude(text: str) -> str:
    """Find Claude window, focus it, click input, and type."""
    return click_and_type(text, window_title="Claude", press_enter=False)


def type_into_vscode(text: str) -> str:
    """Type into VS Code active editor."""
    return click_and_type(text, window_title="Visual Studio Code")


# ── Tool 3: Window Info ───────────────────────────────────────────────────────

def get_active_window() -> str:
    """Return the name of the currently active window."""
    try:
        win = gw.getActiveWindow()
        if win:
            return f"You are currently in {win.title}."
        return "Could not detect the active window."
    except Exception as e:
        return f"Window detection failed: {str(e)}"


def list_open_windows() -> str:
    """List all currently open windows."""
    try:
        wins = [w.title for w in gw.getAllWindows()
                if w.title and w.title.strip()]
        wins = list(dict.fromkeys(wins))[:8]  # deduplicate, top 8
        if not wins:
            return "No open windows detected."
        return "Open windows: " + ", ".join(wins) + "."
    except Exception as e:
        return f"Could not list windows: {str(e)}"


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "read_screen":      read_screen,
    "describe_screen":  describe_screen,
    "find_error":       find_error_on_screen,
    "type_text":        type_text,
    "type_and_send":    type_and_send,
    "click_and_type":   click_and_type,
    "type_into_claude": type_into_claude,
    "type_into_vscode": type_into_vscode,
    "get_active_window":get_active_window,
    "list_open_windows":list_open_windows,
}
