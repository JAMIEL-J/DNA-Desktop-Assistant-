"""
skills/screen_skill.py
DNA Screen Awareness, Smart Typing, and Vision Skill
Capabilities:
  1. read_screen       - screenshot → Gemini/Ollama vision → spoken answer
  2. describe_screen   - full screen description
  3. find_error        - look for errors on screen
  4. type_text         - type into active or named window
  5. type_and_send     - type + press Enter
  6. click_and_type    - focus window + click input + type
  7. type_into_claude  - type into Claude window
  8. type_into_vscode  - type into VS Code
  9. get_active_window - current active window info
  10. list_open_windows - all open windows
"""

import base64
import importlib
import io
import logging
import os
import re
import time

import pyautogui

from config import (
    GOOGLE_API_KEY,
    CLOUD_LLM_MODEL,
    OLLAMA_URL,
    OLLAMA_VISION_MODEL,
    OLLAMA_TIMEOUT,
    SCREENSHOTS_DIR,
)

logger = logging.getLogger('dna.skill.screen')


# ── Vision helper ─────────────────────────────────────────────────────────────

def _screenshot_to_base64() -> tuple[str, bytes]:
    """Take screenshot, return (base64_string, raw_bytes)."""
    screenshot = pyautogui.screenshot()
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    raw = buf.getvalue()
    return base64.b64encode(raw).decode(), raw


def _ask_vision_google(question: str, screenshot_pil) -> str:
    """Send screenshot + question to Gemini Vision."""
    genai = importlib.import_module('google.genai')
    client = genai.Client(api_key=GOOGLE_API_KEY)

    strict_prompt = (
        "You are a screen reader assistant for a voice assistant called DNA. "
        "The user cannot see the screen — you describe it for them. "
        f"Answer this question about the screen: {question}. "
        "Keep your answer under 3 spoken sentences. "
        "If there is an error, quote it exactly. "
        "Plain text only. No markdown. No bullet points."
    )

    response = client.models.generate_content(
        model=CLOUD_LLM_MODEL,
        contents=[strict_prompt, screenshot_pil],
    )

    text = (getattr(response, 'text', '') or '').strip()
    # Strip thinking blocks and markdown artifacts
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'^\d+\.\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^(I need|The user|Combining|Looking at|Let me).*$',
                  '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = text.replace('**', '').replace('*', '').replace('`', '').replace('#', '')
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "I could not clearly read the screen."


def _ask_vision_ollama(question: str, b64_image: str) -> str:
    """Send screenshot + question to local Ollama vision model."""
    import requests

    response = requests.post(
        OLLAMA_URL,
        json={
            'model': OLLAMA_VISION_MODEL,
            'messages': [
                {
                    'role': 'user',
                    'content': question,
                    'images': [b64_image],
                }
            ],
            'stream': False,
            'options': {'temperature': 0.1},
        },
        timeout=OLLAMA_TIMEOUT * 2.5,
    )
    response.raise_for_status()
    data = response.json()
    return str(data.get('message', {}).get('content', '')).strip()


# ── Tool 1: Read Screen ───────────────────────────────────────────────────────

def read_screen(question: str = "What is on my screen?") -> str:
    """Take screenshot and answer a question about it using vision AI."""
    try:
        logger.info('Taking screenshot for screen reading...')
        screenshot_pil = pyautogui.screenshot()

        # Save screenshot for reference
        if SCREENSHOTS_DIR:
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            path = os.path.join(SCREENSHOTS_DIR, f"screen_{int(time.time())}.png")
            screenshot_pil.save(path)

        # Cloud-first, local fallback
        if GOOGLE_API_KEY:
            try:
                return _ask_vision_google(question, screenshot_pil)
            except Exception as e:
                logger.error('Google Vision failed: %s. Falling back to Ollama.', e)

        # Local Ollama path
        buf = io.BytesIO()
        screenshot_pil.save(buf, format='JPEG', quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()
        result = _ask_vision_ollama(question, b64)

        if not result:
            return "I took a look but could not clearly understand the screen."
        return result

    except Exception as e:
        logger.error('read_screen failed: %s', e, exc_info=True)
        return f"Could not read the screen right now: {str(e)}"


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
        logger.error('type_text failed: %s', e)
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
        import pygetwindow as gw

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
        logger.error('click_and_type failed: %s', e)
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
        import pygetwindow as gw
        win = gw.getActiveWindow()
        if win:
            return f"You are currently in {win.title}."
        return "Could not detect the active window."
    except Exception as e:
        logger.error('get_active_window failed: %s', e)
        return f"Window detection failed: {str(e)}"


def list_open_windows() -> str:
    """List all currently open windows."""
    try:
        import pygetwindow as gw
        wins = [w.title for w in gw.getAllWindows()
                if w.title and w.title.strip()]
        wins = list(dict.fromkeys(wins))[:8]  # deduplicate, top 8
        if not wins:
            return "No open windows detected."
        return "Open windows: " + ", ".join(wins) + "."
    except Exception as e:
        logger.error('list_open_windows failed: %s', e)
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
