"""
core/morning_briefing.py
DNA Morning Briefing — Unified startup greeting with context-aware updates.

Assembles a single, natural, flowing spoken greeting that includes:
  1. Time-aware greeting (Good morning / afternoon / evening)
  2. Day & date context
  3. Weather (if configured)
  4. Quick news (1-2 top headlines)
  5. Job updates (if any new ones)
  6. App suggestion (if pattern detected)

Instead of 5 separate speak() calls, this builds ONE coherent briefing.
"""

import logging
import random
from datetime import datetime

logger = logging.getLogger('dna.morning_briefing')


# ── Greeting Templates ────────────────────────────────────────────────────────

_MORNING = [
    "Good morning sir. It's {day}, {date}.",
    "Good morning sir. Today is {day}, {date}.",
    "Morning sir. We're at {day}, {date}.",
]

_AFTERNOON = [
    "Good afternoon sir. It's {day}, {date}.",
    "Afternoon sir. Today is {day}, {date}.",
]

_EVENING = [
    "Good evening sir. It's {day}, {date}.",
    "Evening sir. Today is {day}, {date}.",
]

_LATE_NIGHT = [
    "Good evening sir. It's quite late, {time} on {day}.",
    "Evening sir. It's {time}, {day} night.",
]


def _get_greeting() -> str:
    """Build a natural time-aware greeting with date context."""
    now = datetime.now()
    hour = now.hour
    day = now.strftime('%A')          # Monday, Tuesday, ...
    date = now.strftime('%B %d')      # May 12
    time_str = now.strftime('%I:%M %p').lstrip('0')  # 1:06 PM

    if hour < 12:
        template = random.choice(_MORNING)
    elif hour < 17:
        template = random.choice(_AFTERNOON)
    elif hour < 22:
        template = random.choice(_EVENING)
    else:
        template = random.choice(_LATE_NIGHT)

    return template.format(day=day, date=date, time=time_str)


def _get_weather_line() -> str:
    """Get a compact weather line for the briefing."""
    try:
        from skills.weather_skill import morning_weather
        return morning_weather() or ""
    except Exception as e:
        logger.debug('Weather skipped: %s', e)
        return ""


def _get_news_line() -> str:
    """Get LIVE AI/tech headlines with briefs for the startup briefing."""
    try:
        from skills.news_skill import morning_news_brief
        return morning_news_brief() or ""
    except Exception as e:
        logger.debug('News skipped: %s', e)
        return ""


def _get_job_line() -> str:
    """Get job update if any new openings found today."""
    try:
        from config import JOBS_ON_STARTUP
        if not JOBS_ON_STARTUP:
            return ""
        from skills.job_search_skill import morning_job_check
        return morning_job_check() or ""
    except Exception as e:
        logger.debug('Job check skipped: %s', e)
        return ""


def _get_suggestion_line() -> str:
    """Get app suggestion if a usage pattern is detected."""
    try:
        from config import (
            SUGGESTIONS_ENABLED, STARTUP_SUGGESTIONS_ENABLED,
            STARTUP_SUGGESTION_MIN_COUNT, STARTUP_SUGGESTION_MIN_CONFIDENCE,
            STARTUP_SUGGESTION_COOLDOWN_MINUTES,
        )
        from pipeline.memory import get_scored_startup_suggestion

        if not SUGGESTIONS_ENABLED or not STARTUP_SUGGESTIONS_ENABLED:
            return ""

        top_app = get_scored_startup_suggestion(
            min_count=STARTUP_SUGGESTION_MIN_COUNT,
            min_confidence=STARTUP_SUGGESTION_MIN_CONFIDENCE,
            cooldown_minutes=STARTUP_SUGGESTION_COOLDOWN_MINUTES,
        )
        if top_app:
            return f"You usually open {top_app} around this time. Say open {top_app} if you'd like."
        return ""
    except Exception as e:
        logger.debug('Suggestion skipped: %s', e)
        return ""


# ── Main Briefing Builder ─────────────────────────────────────────────────────

def build_morning_briefing() -> str:
    """
    Build a single, flowing morning briefing string.

    Example output:
    "Good morning sir. It's Monday, May 12.
     It is currently 31 degrees and partly cloudy in Chennai.
     In AI news, OpenAI releases GPT-5. In India, PM Modi visits Japan.
     By the way, 3 new Data Analyst fresher openings posted today.
     You usually open VS Code around this time. Say open VS Code if you'd like."
    """
    parts = []

    # 1. Greeting (always)
    parts.append(_get_greeting())

    # 2. Weather
    weather = _get_weather_line()
    if weather:
        parts.append(weather)

    # 3. News
    news = _get_news_line()
    if news:
        parts.append(news)

    # 4. Jobs
    jobs = _get_job_line()
    if jobs:
        parts.append(jobs)

    # 5. Suggestion
    suggestion = _get_suggestion_line()
    if suggestion:
        parts.append(suggestion)

    # 6. Ready prompt
    ready_prompts = [
        "I am at your service.",
        "Ready for your instructions.",
        "How can I assist you today?",
        "What shall we work on?",
    ]
    parts.append(random.choice(ready_prompts))

    return " ".join(parts)
