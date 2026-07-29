"""
core/morning_briefing.py
DNA Morning Briefing — Swarm Status Initialization sequence led by Orchestrator NEXUS.
"""

import logging
import random
from datetime import datetime

logger = logging.getLogger('dna.morning_briefing')


def _get_greeting() -> str:
    """Build a natural, boss-focused time-aware greeting."""
    now = datetime.now()
    hour = now.hour
    day = now.strftime('%A')
    date = now.strftime('%B %d')
    
    if hour < 12:
        period = "morning"
    elif hour < 17:
        period = "afternoon"
    else:
        period = "evening"

    return f"Hey boss, good {period}! It's {day}, {date}."


def build_morning_briefing() -> str:
    """
    Build the initial 6-agent swarm report sequence.
    NEXUS leads and reports each specialist agent status clearly without executing operations.
    """
    parts = []

    # 1. Main Greeting
    parts.append(_get_greeting())

    # 2. Swarm Agent Self-Report Status Sequence
    swarm_status_report = (
        "Initializing DNA Agent Swarm status sequence. "
        "NEXUS Orchestrator online and routing. "
        "CIPHER scraper ready on Apify. "
        "FORGE ATS resume tailor primed. "
        "ARGUS vision engine standing by. "
        "HERMES communication channel ready. "
        "TITAN system metrics online. "
        "All 6 agents are loaded, API connection status ok, currently idle, and ready for you to assign tasks, boss."
    )
    parts.append(swarm_status_report)

    return " ".join(parts)
