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
from datetime import datetime

import requests

from config import (
    GOOGLE_API_KEY,
    CLOUD_LLM_MODEL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)
from pipeline.memory import mirror_conversation

logger = logging.getLogger('dna.skill.chat')

# ── Conversation Memory ─────────────────────────────────────────────
# Short-term history for follow-up support. Clears after 5 min idle.

_history_lock = threading.Lock()
_history: deque = deque(maxlen=20)  # 10 user + 10 assistant messages
_last_interaction: float = 0.0
_CONTEXT_TIMEOUT = 300.0  # seconds
_session_timestamp: str | None = None


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
    global _last_interaction, _session_timestamp
    with _history_lock:
        if _last_interaction > 0 and (time.time() - _last_interaction) > _CONTEXT_TIMEOUT:
            _history.clear()
            _session_timestamp = None
            logger.info('Conversation history auto-cleared (idle timeout)')
        return list(_history)


def _add_to_history(role: str, content: str) -> None:
    """Append a message to conversation history."""
    global _last_interaction, _session_timestamp
    with _history_lock:
        if not _history:
            _session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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


_google_client = None

def _get_google_client():
    global _google_client
    if _google_client is None:
        import google.genai as genai
        _google_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _google_client

def _call_google_chat(question: str, history: list[dict], memory_context: str = "") -> str:
    """Call Gemini for a conversational answer with history."""
    client = _get_google_client()

    system_instruction = SYSTEM_PROMPT
    if memory_context:
        system_instruction += f"\n\nMEMORY CONTEXT FROM YOUR VAULT:\n{memory_context}\n\nUse the above memory context to answer the user's question if relevant."

    try:
        from pathlib import Path
        memory_file = Path("data/memory/corpus/persistent_memory.md")
        if memory_file.exists():
            mem_content = memory_file.read_text(encoding="utf-8").strip()
            if mem_content:
                system_instruction += f"\n\nPERSISTENT BRAIN MEMORY (OBSIDIAN):\n{mem_content}\n\nUse this information to answer user questions when relevant."
    except Exception:
        pass

    # Build multi-turn contents for Gemini
    contents = []
    for msg in history:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({'role': role, 'parts': [{'text': msg['content']}]})
    contents.append({'role': 'user', 'parts': [{'text': question}]})

    import tenacity
    from google.genai.errors import ServerError

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(ServerError),
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_exponential(multiplier=1, min=0.5, max=3),
        reraise=True
    )
    def generate_with_retry():
        return client.models.generate_content(
            model=CLOUD_LLM_MODEL,
            contents=contents,
            config={
                'system_instruction': system_instruction,
                'temperature': 0.7,
            },
        )

    response = generate_with_retry()
    return (getattr(response, 'text', '') or '').strip()


def _call_ollama_chat(question: str, history: list[dict], memory_context: str = "") -> str:
    """Call local Ollama for a conversational answer with history."""
    system_instruction = SYSTEM_PROMPT
    if memory_context:
        system_instruction += f"\n\nMEMORY CONTEXT FROM YOUR VAULT:\n{memory_context}\n\nUse the above memory context to answer the user's question if relevant."

    try:
        from pathlib import Path
        memory_file = Path("data/memory/corpus/persistent_memory.md")
        if memory_file.exists():
            mem_content = memory_file.read_text(encoding="utf-8").strip()
            if mem_content:
                system_instruction += f"\n\nPERSISTENT BRAIN MEMORY (OBSIDIAN):\n{mem_content}\n\nUse this information to answer user questions when relevant."
    except Exception:
        pass

    messages = [{'role': 'system', 'content': system_instruction}]
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
        return 'What would you like to know, boss?'

    try:
        # RAG: Retrieve context from semantic memory graph
        memory_context_list = []
        try:
            from pipeline.graph_processor import GraphProcessor
            gp = GraphProcessor()
            G = gp.load_graph()
            if G and G.number_of_nodes() > 0:
                question_lower = question.lower()
                for node_id, data in G.nodes(data=True):
                    label = data.get("label", "")
                    norm_label = data.get("norm_label", label.lower())
                    if norm_label and norm_label in question_lower:
                        triplets = gp.get_subgraph(norm_label)
                        relation_mappings = {
                            "conceptually_related_to": "is closely linked with",
                            "semantically_similar_to": "is associated with",
                            "references": "refers to",
                            "expert_in": "specializes in",
                            "relates_to": "is connected to",
                        }
                        for t in triplets:
                            src = t.get("source_label", t.get("source", ""))
                            rel_key = t.get("relation", "relates_to").strip().lower().replace(" ", "_")
                            tgt = t.get("target_label", t.get("target", ""))
                            rel_phrase = relation_mappings.get(rel_key, rel_key.replace("_", " "))
                            sentence = f"{src} {rel_phrase} {tgt}."
                            sentence = sentence[0].upper() + sentence[1:]
                            if sentence not in memory_context_list:
                                memory_context_list.append(f"- {sentence}")
        except Exception as e:
            logger.error('Failed to retrieve semantic context: %s', e)

        # Swarm Inter-Agent Memory: Retrieve recent sub-agent Blackboard executions
        try:
            from core.blackboard import get_global_blackboard
            bb = get_global_blackboard()
            recent_msgs = bb.get_recent_history(limit=5)
            if recent_msgs:
                memory_context_list.append("\nRECENT SWARM AGENT EXECUTION OUTPUTS & RECENT FINDINGS:")
                for item in recent_msgs:
                    agent = item.get("agent_id", "AGENT")
                    action = item.get("action", "action")
                    res = item.get("result", "")
                    memory_context_list.append(f"- [{agent}] ({action}): {res}")
        except Exception as e:
            logger.error('Failed to retrieve Blackboard context: %s', e)

        memory_context = "\n".join(memory_context_list) if memory_context_list else ""

        history = _get_history()
        _add_to_history('user', question)

        # Cloud-first, local fallback
        if GOOGLE_API_KEY:
            try:
                answer = _call_google_chat(question, history, memory_context)
            except Exception as e:
                logger.error('Google chat failed: %s. Falling back to Ollama.', e)
                answer = _call_ollama_chat(question, history, memory_context)
        else:
            answer = _call_ollama_chat(question, history, memory_context)

        answer = _clean_answer(answer)

        if not answer:
            answer = "I am not quite sure about that, boss. Could you rephrase?"

        _add_to_history('assistant', answer)
        try:
            mirror_conversation(list(_history), _session_timestamp)
        except Exception as e:
            logger.error('Failed to mirror conversation to corpus: %s', e)
        logger.info('Chat answer: %s', answer[:120])
        return answer

    except requests.exceptions.ConnectionError:
        return "Sorry boss, I cannot reach my brain right now. Make sure the AI service is running."
    except requests.exceptions.Timeout:
        return "That took too long, boss. Could you try again?"
    except Exception as e:
        logger.error('Chat failed: %s', e, exc_info=True)
        return "Sorry boss, I had trouble answering that. Could you try again?"


def clear_chat_history() -> str:
    """Clear the conversation history for a fresh start."""
    global _session_timestamp
    with _history_lock:
        _history.clear()
        _session_timestamp = None
    logger.info('Conversation history manually cleared')
    return 'Conversation history cleared, boss. Fresh start.'



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
