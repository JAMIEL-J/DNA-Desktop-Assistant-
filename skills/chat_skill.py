# skills/chat_skill.py
# ──────────────────────────────────────────────────────────────────────
# Chat Skill — Conversational voice answers with follow-up memory
# Routes questions through Gemini / Ollama and returns spoken answers.
# ──────────────────────────────────────────────────────────────────────

import importlib
import logging
import re
import threading
import time
from collections import deque

import requests

from config import (
    GOOGLE_API_KEY,
    CLOUD_LLM_MODEL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)

logger = logging.getLogger('dna.skill.chat')

# ── Conversation Memory ─────────────────────────────────────────────
# Short-term history for follow-up support. Clears after 5 min idle.

_history_lock = threading.Lock()
_history: deque = deque(maxlen=20)  # 10 user + 10 assistant messages
_last_interaction: float = 0.0
_CONTEXT_TIMEOUT = 300.0  # seconds


SYSTEM_PROMPT = (
    "You are DNA, a highly intelligent and loyal voice assistant. "
    "Answer the user's question directly and conversationally.\n\n"
    "RULES:\n"
    "1. Keep responses SHORT — 1 to 4 sentences maximum. This will be spoken aloud.\n"
    "2. Be informative, accurate, and concise. No bullet points, no markdown, no formatting.\n"
    "3. Use natural phrasing suitable for voice output.\n"
    "4. If you truly don't know, say so honestly rather than guessing.\n"
    "5. Address the user as 'sir' occasionally for a respectful butler tone.\n"
    "6. For follow-up questions, use the conversation history for context.\n"
    "7. Never start with 'Sure!' or 'Great question!' — just answer directly.\n"
    "8. Do NOT use asterisks, hashtags, backticks, or any markdown.\n"
)


def _get_history() -> list[dict]:
    """Return conversation history, clearing if stale."""
    global _last_interaction
    with _history_lock:
        if _last_interaction > 0 and (time.time() - _last_interaction) > _CONTEXT_TIMEOUT:
            _history.clear()
            logger.info('Conversation history auto-cleared (idle timeout)')
        return list(_history)


def _add_to_history(role: str, content: str) -> None:
    """Append a message to conversation history."""
    global _last_interaction
    with _history_lock:
        _history.append({'role': role, 'content': content})
        _last_interaction = time.time()


def _clean_answer(text: str) -> str:
    """Strip markdown artifacts and enforce voice-friendly length."""
    if not text:
        return text
    # Remove markdown formatting
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.replace('**', '').replace('*', '').replace('#', '').replace('`', '')
    # Remove numbered list prefixes
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    # Collapse whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Cap at ~5 sentences for voice
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 5:
        text = ' '.join(sentences[:5])
    return text


def _call_google_chat(question: str, history: list[dict]) -> str:
    """Call Gemini for a conversational answer with history."""
    genai = importlib.import_module('google.genai')
    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Build multi-turn contents for Gemini
    contents = []
    for msg in history:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({'role': role, 'parts': [{'text': msg['content']}]})
    contents.append({'role': 'user', 'parts': [{'text': question}]})

    response = client.models.generate_content(
        model=CLOUD_LLM_MODEL,
        contents=contents,
        config={
            'system_instruction': SYSTEM_PROMPT,
            'temperature': 0.7,
        },
    )
    return (getattr(response, 'text', '') or '').strip()


def _call_ollama_chat(question: str, history: list[dict]) -> str:
    """Call local Ollama for a conversational answer with history."""
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({'role': 'user', 'content': question})

    response = requests.post(
        OLLAMA_URL,
        json={
            'model': OLLAMA_MODEL,
            'messages': messages,
            'stream': False,
            'options': {'temperature': 0.7, 'num_ctx': 2048},
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload.get('message'), dict):
        return str(payload['message'].get('content', '')).strip()
    return str(payload.get('response', '')).strip()


def chat(question: str = '') -> str:
    """Answer a question conversationally with follow-up support."""
    if not question or not question.strip():
        return 'What would you like to know, sir?'

    try:
        history = _get_history()
        _add_to_history('user', question)

        # Cloud-first, local fallback
        if GOOGLE_API_KEY:
            try:
                answer = _call_google_chat(question, history)
            except Exception as e:
                logger.error('Google chat failed: %s. Falling back to Ollama.', e)
                answer = _call_ollama_chat(question, history)
        else:
            answer = _call_ollama_chat(question, history)

        answer = _clean_answer(answer)

        if not answer:
            answer = "I am not quite sure about that, sir. Could you rephrase?"

        _add_to_history('assistant', answer)
        logger.info('Chat answer: %s', answer[:120])
        return answer

    except requests.exceptions.ConnectionError:
        return "Sorry sir, I cannot reach my brain right now. Make sure the AI service is running."
    except requests.exceptions.Timeout:
        return "That took too long, sir. Could you try again?"
    except Exception as e:
        logger.error('Chat failed: %s', e, exc_info=True)
        return "Sorry sir, I had trouble answering that. Could you try again?"


def clear_chat_history() -> str:
    """Clear the conversation history for a fresh start."""
    with _history_lock:
        _history.clear()
    logger.info('Conversation history manually cleared')
    return 'Conversation history cleared, sir. Fresh start.'


def get_history_context(limit: int = 5) -> str:
    """Return recent history as a formatted string for LLM context."""
    history = _get_history()
    if not history:
        return ""
    
    lines = []
    for msg in list(history)[-limit:]:
        role = "User" if msg['role'] == 'user' else "DNA"
        content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
        lines.append(f"{role}: {content}")
    
    return "\n".join(lines)


TOOLS = {
    'chat': chat,
    'clear_chat_history': clear_chat_history,
}
