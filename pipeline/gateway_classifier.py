# pipeline/gateway_classifier.py
import re

CATEGORY_A_PATTERNS = [
    re.compile(r'\b(volume|mute|brightness|screenshot|lock|shutdown|restart|sleep|bluetooth|wifi)\b', re.I),
    re.compile(r'\b(open|launch|start|close|exit|quit|kill)\s+', re.I),
    re.compile(r'\b(downloads?|desktop|documents?|folder|files?)\b', re.I),
    re.compile(r'\b(what.*time|what.*date|current time|today.*date|what.*day)\b', re.I),
    re.compile(r'\b(weather|temperature|forecast|rain)\b', re.I),
    re.compile(r'\b(news|headlines?|rss)\b', re.I),
    re.compile(r'\b(play|pause|stop|next track|previous track)\b', re.I),
]

def classify(command: str) -> str:
    """Returns 'A' (deterministic) or 'B' (reasoning/LLM)."""
    if not command:
        return 'B'
    cmd_lower = command.lower()
    
    # Direct agent commands (e.g. "hello hermes", "cipher run job search", "status of all agents") MUST go to Category B (NEXUS)
    agent_names = ['nexus', 'cipher', 'forge', 'argus', 'hermes', 'titan', 'vanguard', 'jarvis']
    if any(agent in cmd_lower for agent in agent_names) or 'status' in cmd_lower or 'agents' in cmd_lower or 'report' in cmd_lower:
        return 'B'

    # Browser-automation verbs need the live browser (NEXUS -> HERMES -> Playwright),
    # never the deterministic regex path (e.g. "open ... and click ..." must not
    # hit the generic open_app catch-all).
    automation_verbs = ['playwright', 'automate', 'browser automation', 'click the', 'click on',
                        'fill form', 'fill the form', 'type into', 'press key', 'take snapshot',
                        'page snapshot', 'select option']
    if any(verb in cmd_lower for verb in automation_verbs):
        return 'B'

    for pattern in CATEGORY_A_PATTERNS:
        if pattern.search(command):
            return 'A'
    return 'B'  # Everything else goes to NEXUS orchestrator
