# skills/vision_skill.py
# ──────────────────────────────────────────────────────────────────────
# Vision Skill — Moondream screen reading
# Uses pyautogui to capture the active view and Ollama to parse it.
# ──────────────────────────────────────────────────────────────────────

import base64
import importlib
import logging
from io import BytesIO

import pyautogui
import requests

from config import OLLAMA_TIMEOUT, OLLAMA_URL, OLLAMA_VISION_MODEL, GOOGLE_API_KEY, CLOUD_LLM_MODEL

logger = logging.getLogger('dna.skill.vision')

def _call_google_vision(screenshot, question: str) -> str:
    """Use Gemini Cloud Vision API."""
    import re
    genai = importlib.import_module('google.genai')

    client = genai.Client(api_key=GOOGLE_API_KEY)
    strict_prompt = (
        question 
        + " Analyze the screen and identify the specific apps, interfaces, text, or coding environments visible. "
        + "Your FINAL answer must be ONLY one short sentence at the very end. "
        + "DO NOT output any reasoning, thinking, or introduction."
    )
    logger.info("Asking Google Gemini Vision: %s", question)
    response = client.models.generate_content(
        model=CLOUD_LLM_MODEL,
        contents=[strict_prompt, screenshot],
    )

    text = getattr(response, 'text', '') or ''
    
    # --- Post-processing: strip reasoning and markdown ---
    # Remove <think>...</think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove numbered lists like "1. **IDE**: ..."
    text = re.sub(r'^\d+\.\s+.*$', '', text, flags=re.MULTILINE)
    # Remove lines starting with "I need", "The user", "Combining", "Looking at"
    text = re.sub(r'^(I need|The user|Combining|Looking at|Let me).*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove all markdown: **, *, `, #
    text = text.replace('**', '').replace('*', '').replace('`', '').replace('#', '')
    # Collapse whitespace and take the last non-empty line (the actual answer)
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if lines:
        text = lines[-1]
    else:
        text = "I could not clearly read the screen."
    
    return text

def read_screen(question: str = "Describe in one short sentence what is clearly visible on the screen.") -> str:
    """Takes a screenshot of the current screen and asks the vision model to analyze it."""
    try:
        logger.info('Taking screenshot for vision analysis...')
        # 1. Take screenshot (Returns a PIL Image)
        screenshot = pyautogui.screenshot()
        
        # 2. Cloud Path
        if GOOGLE_API_KEY:
            return _call_google_vision(screenshot, question)
            
        # 3. Local (Ollama) Path
        buffered = BytesIO()
        screenshot.save(buffered, format='JPEG', quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

        logger.info('Asking local vision model (%s): %s', OLLAMA_VISION_MODEL, question)

        response = requests.post(
            OLLAMA_URL,
            json={
                'model': OLLAMA_VISION_MODEL,
                'messages': [
                    {
                        'role': 'user',
                        'content': question,
                        'images': [img_str],
                    }
                ],
                'stream': False,
                'options': {
                    'temperature': 0.1,
                },
            },
            timeout=OLLAMA_TIMEOUT * 2.5,
        )

        response.raise_for_status()

        data = response.json()
        result = str(data.get('message', {}).get('content', '')).strip()

        if not result:
            return 'I took a look but couldn\'t clearly understand the screen.'

        logger.debug('Vision response: %s', result)
        return result

    except requests.exceptions.RequestException as e:
        logger.error('Vision model API error: %s', e)
        return 'I could not connect to the vision model. Ensure Ollama is running and the moondream model is installed.'
    except Exception as e:
        logger.error('read_screen failed: %s', e, exc_info=True)
        return f'Could not read the screen right now: {str(e)}'


TOOLS = {
    'read_screen': read_screen,
}
