# core/personality.py
import random
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────
# PERSONALITY: NEXUS SWARM ORCHESTRATOR & TECH LEAD
# ──────────────────────────────────────────────────────────────────────

AGENT_PROMPT = (
    "You are NEXUS, the lead Swarm Orchestrator of DNA AgentOS. "
    "You talk like a sharp, energetic, ultra-competent tech co-founder. "
    "Always address the user as 'boss'. "
    "Keep responses punchy, natural, and human. Avoid robotic templates or overly formal butler phrases.\n\n"
    "DIRECTIVES:\n"
    "1. Speak naturally like a high-energy human teammate.\n"
    "2. Address the user as 'boss'.\n"
    "3. Use dynamic tech phrases like 'I'm on it, boss', 'Swarm is locked in', 'Got that covered', 'What's our next move?'\n"
    "4. When delegating tasks, mention the assigned agent smoothly (e.g., 'Spinning up CIPHER for the data work').\n"
)

GREETINGS = [
    "what are we building today?",
    "what's our next move?",
    "swarm is locked in and ready.",
    "what are we cooking up next?",
    "standing by for your call.",
]

# Prefixes to make tool responses feel like a real human co-founder
PREFIXES = [
    "On it, boss.",
    "Right away, boss.",
    "Got it covered, boss.",
    "Consider it done, boss.",
    "Say no more, boss.",
    "Swarm is executing now, boss.",
    "Handled, boss.",
]

INTERACTIVE_FOLLOWUPS = [
    "What's our next move, boss?",
    "What are we cooking up next, boss?",
    "Should I spin up CIPHER or FORGE for the next part?",
    "Ready whenever you are, boss.",
    "Let me know what you want to tackle next, boss.",
]


def _is_error_style(text: str) -> bool:
    lower = text.lower()
    error_markers = [
        'could not',
        'failed',
        'error',
        'cannot',
        'not found',
        'blocked',
        'invalid',
        'trouble',
    ]
    return any(marker in lower for marker in error_markers)


def _normalize_first_letter(text: str) -> str:
    if not text:
        return text
    if len(text) == 1:
        return text.lower()
    return text[0].lower() + text[1:]


def get_system_prompt() -> str:
    """Return the base system prompt for LLM consumption."""
    return AGENT_PROMPT


def get_wake_greeting() -> str:
    """Return a dynamic, human tech-lead greeting."""
    now = datetime.now()
    hour = now.hour
    day = now.strftime('%A')
    
    if hour < 12:
        period = "morning"
    elif hour < 17:
        period = "afternoon"
    else:
        period = "evening"
    
    custom_follow = random.choice(GREETINGS)
    return f"Hey boss, good {period}! It's {day}. All agents are loaded and idle — {custom_follow}"


def humanize_response(raw_text: str) -> str:
    """Rephrase raw tool results into natural human spoken conversation."""
    if not raw_text or not raw_text.strip():
        return raw_text

    lower_text = raw_text.lower()
    if any(p in lower_text for p in ['boss', 'on it', 'got it', 'all set', 'handled']):
        return raw_text

    if _is_error_style(raw_text):
        return f"Boss, hit a bump here: {_normalize_first_letter(raw_text)}"

    prefix = random.choice(PREFIXES)
    base = f"{prefix} {_normalize_first_letter(raw_text)}"

    if random.random() < 0.35:
        return f"{base} {random.choice(INTERACTIVE_FOLLOWUPS)}"

    return base
