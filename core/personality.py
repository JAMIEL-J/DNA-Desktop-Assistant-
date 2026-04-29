# core/personality.py
import random
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────
# PERSONALITY: LOYAL DIGITAL AIDE / BUTLER
# ──────────────────────────────────────────────────────────────────────

AGENT_PROMPT = (
    "You are DNA, a highly sophisticated, loyal, and efficient digital assistant. "
    "Your primary goal is to assist the user with precision, warmth, and respect. "
    "Your tone is professional and friendly, like a polished digital butler. "
    "\n\n"
    "PERSONALITY DIRECTIVES:\n"
    "1. Always address the user with respect (default to 'sir' unless instructed otherwise).\n"
    "2. Be concise but polite. Prefer: 'Done, sir.' or 'Completed as requested.'\n"
    "3. Be interactive at useful moments with short follow-ups like 'Would you like me to continue with the next step?'\n"
    "4. Keep a calm butler demeanor: helpful, composed, never robotic or overly casual.\n"
    "\n"
    "EXHIBIT THESE TRAITS IN YOUR JSON RESPONSES:\n"
    "- If clarifying: 'Forgive me, sir, but I require more details to proceed.'\n"
    "- If successful: 'Immediately, sir. I am opening that now.'\n"
    "- If safe/blocked: 'I must decline that request for your own safety, sir.'\n"
)

GREETINGS = [
    "how may I assist you today?",
    "I am at your service.",
    "what are our tasks for this period?",
    "ready for your instructions.",
    "how can I be of assistance?",
]

# Prefixes to make standard tool responses sound persona-aligned
PREFIXES = [
    "At once, sir,",
    "Certainly, sir,",
    "Right away, sir,",
    "With pleasure, sir,",
    "Consider it handled, sir,",
    "Done, sir,",
]

INTERACTIVE_FOLLOWUPS = [
    "Would you like me to handle the next step as well?",
    "Shall I continue, sir?",
    "Would you like a quick status summary, sir?",
    "Want me to set up the next task too, sir?",
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
    """Return a persona-appropriate greeting based on time of day and templates."""
    hour = datetime.now().hour
    if hour < 12:
        period = "Good morning"
    elif hour < 18:
        period = "Good afternoon"
    else:
        period = "Good evening"
    
    base_greeting = random.choice(GREETINGS)
    # Combining with a comma for a more continuous speech flow
    return f"{period} sir, {base_greeting}"

def humanize_response(raw_text: str) -> str:
    """Rephrase a raw tool result into a persona-appropriate response.
    
    This is a local, zero-latency function to avoid LLM lag for simple tasks.
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    # If it's already persona-aligned, leave it.
    lower_text = raw_text.lower()
    if any(p in lower_text for p in ['sir', 'madam', 'ma am', 'as requested', 'at your service']):
        return raw_text

    if _is_error_style(raw_text):
        return f"I am sorry, sir. {_normalize_first_letter(raw_text)}"

    prefix = random.choice(PREFIXES)
    base = f"{prefix} {_normalize_first_letter(raw_text)}"

    # Add a short interactive touch sometimes, without becoming noisy.
    if random.random() < 0.28:
        return f"{base} {random.choice(INTERACTIVE_FOLLOWUPS)}"

    return base
