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
    for pattern in CATEGORY_A_PATTERNS:
        if pattern.search(command):
            return 'A'
    return 'B'  # Everything else goes to NEXUS orchestrator
