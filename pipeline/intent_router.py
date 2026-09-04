# pipeline/intent_router.py
# ──────────────────────────────────────────────────────────────────────
# Intent Router — Regex-first, LLM-fallback command routing
# v2 — Confirmation flow for dangerous commands + safety integration
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import logging
import re
import subprocess
import time
from typing import Optional

# 2. internal
from pipeline.context_resolver import resolve_pronouns
from pipeline.llm_agent import handle_complex_command
from pipeline.plan_executor import execute_plan
from core.skill_registry import get_tool_map
from config import WORKFLOWS
from core.safety import (
    is_tool_dangerous,
    is_tool_blocked,
    get_danger_warning,
)
from core.personality import humanize_response

logger = logging.getLogger('dna.router')

# Win32: hide subprocess console windows
CREATE_NO_WINDOW = 0x08000000

DISMISS_PATTERNS = [
    re.compile(r"\bjarvis[\s,]+(?:close|out|stop|bye|sleep|quiet|done|off)\b", re.I),
    re.compile(r"\b(?:goodbye|go\s+to\s+sleep|stop\s+listening|that's\s+all)\b", re.I),
    re.compile(r"\b(?:dismiss|exit|deactivate)\b", re.I),
]

# ════════════════════════════════════════════════════════════════════
# Pending Confirmation State
# ════════════════════════════════════════════════════════════════════
# When a dangerous tool is triggered, we store the pending action here
# and wait for the user to confirm on their next voice command.

_pending_confirmation = {
    'tool_name': None,
    'args': {},
    'display_warning': '',
    'timestamp': 0.0,
}

# Confirmation expires after 30 seconds (user must respond promptly)
_CONFIRM_TIMEOUT_SECS = 30.0


def _set_pending(tool_name: str, args: dict, warning: str) -> None:
    """Store a pending dangerous action awaiting confirmation."""
    _pending_confirmation['tool_name'] = tool_name
    _pending_confirmation['args'] = args
    _pending_confirmation['display_warning'] = warning
    _pending_confirmation['timestamp'] = time.time()
    logger.info('Pending confirmation set for: %s', tool_name)


def _clear_pending() -> None:
    """Clear any pending confirmation."""
    _pending_confirmation['tool_name'] = None
    _pending_confirmation['args'] = {}
    _pending_confirmation['display_warning'] = ''
    _pending_confirmation['timestamp'] = 0.0


def _check_confirmation(command: str) -> Optional[str]:
    """Check if the command is a confirmation/cancellation of a pending action.

    Returns:
        - Tool result string if confirmed and executed
        - Cancellation message if cancelled
        - None if no pending action or command is unrelated
    """
    pending_tool = _pending_confirmation['tool_name']
    if not pending_tool:
        return None

    # Check if confirmation has expired
    elapsed = time.time() - _pending_confirmation['timestamp']
    if elapsed > _CONFIRM_TIMEOUT_SECS:
        logger.info('Pending confirmation expired for: %s (%.1fs)', pending_tool, elapsed)
        _clear_pending()
        return None

    cleaned = command.strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Handle common STT slips for confirmation words.
    cleaned = cleaned.replace('confirmm', 'confirm').replace('llock', 'lock')

    # Only standalone replies count as generic yes/no.
    # Previously any substring (e.g. "stop music" containing "stop")
    # hijacked a pending dangerous confirmation.
    is_explicit_confirm = bool(re.search(r'\bconfirm\s+(shutdown|restart|lock|kill)\b', cleaned))
    _CANCEL_EXACT = {
        'cancel', 'no', 'nope', 'stop', 'abort', 'never mind',
        'do not', 'dont', 'negative', 'forget it', 'skip',
        'cancel that', 'stop that', 'no thanks', 'no thank you',
    }
    _CONFIRM_EXACT = {
        'confirm', 'yes', 'yeah', 'yep', 'sure', 'go ahead',
        'do it', 'proceed', 'okay', 'ok', 'affirmative',
        'yes please', 'sure thing', 'confirm shutdown',
        'confirm restart', 'confirm lock', 'confirm kill',
    }

    # ── Cancellation phrases (exact match only) ──
    if cleaned in _CANCEL_EXACT:
        logger.info('User cancelled pending: %s', pending_tool)
        _clear_pending()
        return humanize_response('No problem, I\'ve cancelled that for you.')

    # ── Confirmation phrases (exact or explicit confirm <tool>) ──
    if is_explicit_confirm or cleaned in _CONFIRM_EXACT:
        tool_name = pending_tool
        args = _pending_confirmation['args']
        _clear_pending()

        logger.info('User CONFIRMED dangerous action: %s', tool_name)
        tool_fn = get_tool_map().get(tool_name)
        if tool_fn:
            try:
                from core.skill_registry import get_skill_for_tool
                from core.session import update as session_update
                skill = get_skill_for_tool(tool_name)
                if skill:
                    session_update('active_skill', skill)
                result = tool_fn(**args)
                return humanize_response(result)
            except Exception as e:
                logger.error('Confirmed tool %s failed: %s', tool_name, e)
                return humanize_response(f'Could not execute {tool_name}: {str(e)}')
        return humanize_response(f'Tool {tool_name} not found.')

    # Command is unrelated — keep pending (expires via timeout) and process normally.
    # Previously cleared silently, losing the user's dangerous-action context.
    logger.info('Unrelated command while pending (%s) — keeping pending, routing normally.', pending_tool)
    return None


# ════════════════════════════════════════════════════════════════════
# Regex-based Simple Intents
# ════════════════════════════════════════════════════════════════════
# Matched from top to bottom — first match wins.
# IMPORTANT: Specific patterns MUST come before generic catch-alls.

SIMPLE_INTENTS = [
    # Volume controls
    (re.compile(r'\b(?:set|change|turn)\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)', re.I),
     'set_volume', lambda m: {'level': m.group(1)}),
    (re.compile(r'\bvolume\s+(?:to\s+)?(\d+)', re.I),
     'set_volume', lambda m: {'level': m.group(1)}),
    (re.compile(r'\b(?:volume\s+up|raise\s+(?:the\s+)?volume|increase\s+(?:the\s+)?volume|louder)', re.I),
     'volume_up', lambda m: {}),
    (re.compile(r'\b(?:volume\s+down|lower\s+(?:the\s+)?volume|decrease\s+(?:the\s+)?volume|quieter)', re.I),
     'volume_down', lambda m: {}),
    (re.compile(r'\b(?:what(?:\'s| is)\s+(?:the\s+)?volume|current\s+volume|volume\s+level)', re.I),
     'get_volume', lambda m: {}),

    # Brightness controls
    (re.compile(r'\b(?:set|change|turn)\s+(?:the\s+)?brightness\s+(?:to\s+)?(\d+)', re.I),
     'set_brightness', lambda m: {'level': m.group(1)}),
    (re.compile(r'\bbrightness\s+(?:to\s+)?(\d+)', re.I),
     'set_brightness', lambda m: {'level': m.group(1)}),
    (re.compile(r'\b(?:brightness\s+up|raise\s+(?:the\s+)?brightness|increase\s+(?:the\s+)?brightness|brighter)', re.I),
     'brightness_up', lambda m: {}),
    (re.compile(r'\b(?:brightness\s+down|lower\s+(?:the\s+)?brightness|decrease\s+(?:the\s+)?brightness|dimmer|dim)', re.I),
     'brightness_down', lambda m: {}),
    (re.compile(r'\b(?:what(?:\'s| is)\s+(?:the\s+)?brightness|current\s+brightness|brightness\s+level)', re.I),
     'get_brightness', lambda m: {}),

    # Mute
    (re.compile(r'\bunmute\b', re.I), 'unmute', lambda m: {}),
    (re.compile(r'\bmute\b', re.I), 'mute', lambda m: {}),

    # Media controls
    (re.compile(r'\b(?:next\s+(?:track|song)|skip(?:\s+track)?)\b', re.I), 'media_next', lambda m: {}),
    (re.compile(r'\b(?:previous\s+(?:track|song)|go\s+back|last\s+(?:track|song))\b', re.I), 'media_previous', lambda m: {}),
    (re.compile(r'^(?:play|pause|play\s*pause|toggle\s+(?:play|music))$', re.I), 'media_play_pause', lambda m: {}),

    # Screenshot
    (re.compile(r'\b(?:take\s+(?:a\s+)?screenshot|screen\s*shot|screen\s*capture|capture\s+screen)\b', re.I), 'take_screenshot', lambda m: {}),

    # Time & Date
    (re.compile(r'\b(?:what(?:\'s| is)\s+(?:the\s+)?time|current\s+time|tell\s+(?:me\s+)?(?:the\s+)?time)\b', re.I), 'get_time', lambda m: {}),
    (re.compile(r'\b(?:what(?:\'s| is)\s+(?:the\s+)?date|today(?:\'s)?\s+date|what\s+day)\b', re.I), 'get_date', lambda m: {}),

    # Shutdown / Restart / Lock — DANGEROUS (will trigger confirmation)
    (re.compile(r'\b(?:shut\s*down|power\s+off|turn\s+off)\s*(?:in\s+(\d+)\s*(?:seconds?|secs?|minutes?|mins?))?', re.I), 'shutdown_computer', lambda m: {'delay': _parse_delay(m)}),
    (re.compile(r'\bcancel\s+(?:the\s+)?shut\s*down\b', re.I), 'cancel_shutdown', lambda m: {}),
    (re.compile(r'\brestart\s*(?:in\s+(\d+)\s*(?:seconds?|secs?|minutes?|mins?))?', re.I), 'restart_computer', lambda m: {'delay': _parse_delay(m)}),
    (re.compile(r'\block\s+(?:the\s+|my\s+|this\s+)?(?:screen|computer|pc|workstation)\b', re.I), 'lock_screen', lambda m: {}),

    # System Utilities
    (re.compile(r'\b(?:empty|clear)\s+(?:the\s+)?(?:recycle\s+)?bin\b', re.I), 'empty_recycle_bin', lambda m: {}),
    (re.compile(r'\b(?:system\s+(?:status|start|stat(?:us|rt|art))|pc\s+status|computer\s+status|how\s+is\s+my\s+(?:pc|computer)\s+doing)', re.I), 'get_system_status', lambda m: {}),
    (re.compile(r'\b(?:system\s+health|health\s+status|pc\s+health|computer\s+health|cpu\s+ram\s+disk)\b', re.I), 'get_system_health', lambda m: {}),
    (re.compile(r'\b(?:show|list|get|what(?:\'s| is))\s+(?:the\s+)?(?:top|heavy|highest)\s+(?:cpu\s+)?process(?:es)?\b', re.I), 'list_heavy_processes', lambda m: {}),
    (re.compile(r'\b(?:kill|terminate|end)\s+(?:the\s+)?(?:process|task)\s+(.+)', re.I), 'kill_process', lambda m: {'name': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:what\s+am\s+i\s+working\s+on|what\s+was\s+i\s+working\s+on|my\s+work\s+context)\b', re.I), 'get_work_context_summary', lambda m: {}),
    (re.compile(r'\b(?:work\s+follow\s*up|follow\s*up\s+on\s+my\s+work|how\s+can\s+you\s+assist\s+me|assist\s+me\s+with\s+work)\b', re.I), 'work_followup', lambda m: {}),

    # Memory Vault / Semantic Graph Commands
    (re.compile(r'\b(?:sync|update|refresh)\s+(?:my\s+)?memory(?:\s+vault)?\b', re.I), 'sync_memory_vault', lambda m: {}),
    (re.compile(r'\b(?:query|search|retrieve|what\s+(?:do\s+)?we\s+know\s+about|what(?:\'s| is)\s+in\s+(?:my\s+)?memory\s+about)\s+(.+)', re.I), 'query_memory_vault', lambda m: {'entity': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:remember\s+that|save\s+to\s+memory\s+that|memorize\s+that)\s+(.+)', re.I), 'memorize_fact', lambda m: {'category': 'General', 'fact': _clean_arg(m.group(1))}),

    # --- SEARCH & NAVIGATION ---
    (re.compile(r'\b(?:play|search)\s+(.+)\s+on\s+youtube\b', re.I), 'search_youtube', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bsearch\s+google\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bgoogle\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),

    # --- JOB SEARCH (Natural Voice Commands) ---
    (re.compile(r'\b(?:job\s+search|search\s+jobs?)\s+(?:for\s+)?(?:data\s+analyst|analyst)\b', re.I),
     'enter_job_search_mode', lambda m: {'role': 'data analyst'}),
    (re.compile(r'\b(?:job\s+search|search\s+jobs?)\s+(?:for\s+)?(?:data\s+scien\w*|scientist)\b', re.I),
     'enter_job_search_mode', lambda m: {'role': 'data scientist'}),
    (re.compile(r'\b(?:job\s+search|search\s+jobs?)\s+(?:for\s+)?(?:business\s+analyst|BA)\b', re.I),
     'enter_job_search_mode', lambda m: {'role': 'business analyst'}),
    (re.compile(r'\b(?:job\s+search|search\s+jobs?)\s+(?:for\s+)?(?:data\s+engineer|DE)\b', re.I),
     'enter_job_search_mode', lambda m: {'role': 'data engineer'}),
    (re.compile(r'\b(?:job\s+search|search\s+jobs?)\s+(?:for\s+)?(?:ml|machine\s+learning)\b', re.I),
     'enter_job_search_mode', lambda m: {'role': 'ml engineer'}),
    # Role within generic phrasing (e.g. "find data analyst jobs")
    (re.compile(r'\b(?:find|get|show|look\s+for)\s+(?:data\s+analyst|data\s+scientist|business\s+analyst|data\s+engineer|ml\s+engineer)\s+(?:jobs?|openings?|roles?)\b', re.I),
     'enter_job_search_mode', lambda m: {'role': re.search(r'(data\s+analyst|data\s+scientist|business\s+analyst|data\s+engineer|ml\s+engineer)', m.group(0), re.I).group(1).lower()}),
    # Generic job triggers via natural speech
    (re.compile(r'\b(?:show|find|get|check|are there|any)\b.+\b(?:jobs?|openings?|vacancies|hiring|positions?)\b', re.I),
     'enter_job_search_mode', lambda m: {}),
    (re.compile(r'\b(?:is there|are there).+(?:opening|job|hiring|vacancy)\b', re.I),
     'enter_job_search_mode', lambda m: {}),
    (re.compile(r'\bwhat.+(?:job|opening).+(?:available|out there)\b', re.I),
     'enter_job_search_mode', lambda m: {}),
    # Portal opening (explicit "browse" or "open portal" — NOT "search jobs for X")
    (re.compile(r'\bopen\s+(?:job|naukri|indeed|internshala)\s+portal\b', re.I),
     'open_job_portals', lambda m: {}),
    (re.compile(r'\bbrowse\s+jobs\b', re.I),
     'open_job_portals', lambda m: {}),

    # --- WEB SEARCH ---
    # Explicit web search: "search the web for X", "look up X online"
    (re.compile(r'\b(?:search\s+(?:the\s+)?web|web\s+search|look\s+up)\s+(?:for\s+)?(.+)', re.I),
     'web_search', lambda m: {'query': _clean_arg(m.group(1))}),
    # "does X have offers", "is X open today", "what is X price"
    (re.compile(r'\b(?:does|is|are|what(?:\'s|\s+is))\s+(.+?)\s+(?:have|having|offering|open|available|price|cost|rate)\b', re.I),
     'web_search', lambda m: {'query': m.group(0).strip()}),
    # "check if X", "find out about X online"
    (re.compile(r'\b(?:check\s+if|find\s+out)\s+(.+)', re.I),
     'web_search', lambda m: {'query': _clean_arg(m.group(1))}),
    # "read this page/url"
    (re.compile(r'\b(?:read|summarize|summarise)\s+(?:this\s+)?(?:page|url|link|website)\s+(.+)', re.I),
     'fetch_and_summarize', lambda m: {'url': _clean_arg(m.group(1))}),

    # --- NEWS ---
    # Topic-specific news
    (re.compile(r'\b(?:latest|today(?:\'s)?|recent|current)\s+(?:ai|artificial\s+intelligence|ml|machine\s+learning)\s+news\b', re.I),
     'get_ai_news', lambda m: {}),
    (re.compile(r'\bai\s+news\b', re.I),
     'get_ai_news', lambda m: {}),
    (re.compile(r'\b(?:latest|today(?:\'s)?|recent)\s+tech(?:nology)?\s+news\b', re.I),
     'get_tech_news', lambda m: {}),
    (re.compile(r'\btech\s+news\b', re.I),
     'get_tech_news', lambda m: {}),
    (re.compile(r'\b(?:india|indian|domestic)\s+news\b', re.I),
     'get_india_news', lambda m: {}),
    (re.compile(r'\b(?:cricket|ipl)\s+(?:score|news|update|result)\b', re.I),
     'get_cricket_score', lambda m: {}),
    (re.compile(r'\b(?:cricket|ipl)\s+(?:score|news|update)\b', re.I),
     'get_cricket_score', lambda m: {}),
    # Generic "what's the news", "give me headlines"
    (re.compile(r'\b(?:what(?:\'s|\s+is)\s+(?:the\s+)?(?:news|headline)|top\s+(?:news|stories|headline)|give\s+me\s+(?:the\s+)?(?:news|headline))\b', re.I),
     'get_headlines', lambda m: {}),
    # "news about X", "X news"
    (re.compile(r'\bnews\s+(?:about|on|regarding)\s+(.+)', re.I),
     'get_news', lambda m: {'topic': _clean_arg(m.group(1))}),
    (re.compile(r'\b(.+?)\s+news\b', re.I),
     'get_news', lambda m: {'topic': _clean_arg(m.group(1))}),

    # --- WEATHER ---
    (re.compile(r'\b(?:weather|temperature|temp)\s+(?:in|at|for|of)\s+(.+)', re.I),
     'get_weather', lambda m: {'city': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:what(?:\'s|\s+is)\s+(?:the\s+)?(?:weather|temperature|temp))\b', re.I),
     'get_weather', lambda m: {}),
    (re.compile(r'\b(?:how(?:\'s|\s+is)\s+(?:the\s+)?weather)\b', re.I),
     'get_weather', lambda m: {}),
    (re.compile(r'\b(?:forecast|weather\s+forecast)\s+(?:for\s+|in\s+)?(.+)', re.I),
     'get_forecast', lambda m: {'city': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:will\s+it\s+rain|is\s+it\s+(?:going\s+to\s+)?rain)\b', re.I),
     'get_forecast', lambda m: {}),

    # --- ORGANIZER SKILL ---
    (re.compile(r'\b(?:organize|clean\s+up|sort|tidy)\s+(?:my\s+|the\s+)?(?:desktop|files)\b', re.I),
     'preview_organize', lambda m: {}),
    (re.compile(r'\b(?:organize|clean\s+up|sort|tidy)\s+(?:my\s+|the\s+)?(?:download|downloads)\b', re.I),
     'organize_downloads', lambda m: {}),
    (re.compile(r'\b(?:organize|sort|tidy)\s+(?:the\s+)?folder\s+(.+)', re.I),
     'organize_folder', lambda m: {'path': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:undo|reverse|revert)\s+(?:the\s+)?(?:organiz|move|sort)', re.I),
     'undo_organize', lambda m: {}),
    (re.compile(r'\b(?:clean|remove)\s+(?:the\s+)?(?:empty|blank)\s+(?:folder|director)', re.I),
     'clean_empty_folders', lambda m: {}),

    # --- SCREEN SKILL ---
    # Read / describe screen
    (re.compile(r'\b(?:what(?:\'s|\s+is)\s+on\s+(?:my\s+)?screen)\b', re.I),
     'read_screen', lambda m: {'question': 'What is on this screen?'}),
    (re.compile(r'\b(?:describe|read|look\s+at)\s+(?:my\s+)?screen\b', re.I),
     'describe_screen', lambda m: {}),
    (re.compile(r'\b(?:any\s+|what\s+|is\s+there\s+an?\s+)?errors?\s+(?:on|showing|visible)\b', re.I),
     'find_error', lambda m: {}),
    (re.compile(r'\bwhat\s+(?:window|app)\s+(?:am\s+i|is)\s+(?:in|open|active)\b', re.I),
     'get_active_window', lambda m: {}),
    (re.compile(r'\b(?:list|show|what\s+are)\s+(?:my\s+|all\s+)?(?:open\s+)?(?:windows|apps)\b', re.I),
     'list_open_windows', lambda m: {}),
    # Typing commands
    (re.compile(r'\btype\s+(.+)\s+(?:in|into|on)\s+claude\b', re.I),
     'type_into_claude', lambda m: {'text': _clean_arg(m.group(1))}),
    (re.compile(r'\btype\s+(.+)\s+(?:in|into)\s+(?:vs\s*code|vscode|code)\b', re.I),
     'type_into_vscode', lambda m: {'text': _clean_arg(m.group(1))}),
    (re.compile(r'\btype\s+(.+)\s+and\s+(?:send|submit|enter)\b', re.I),
     'type_and_send', lambda m: {'text': _clean_arg(m.group(1))}),
    (re.compile(r'\btype\s+(.+)', re.I),
     'type_text', lambda m: {'text': _clean_arg(m.group(1))}),

    # --- CONVERSATIONAL QUESTIONS (voice answers via chat skill) ---
    # These MUST come after all specific tool patterns (time, date, volume,
    # system status, etc.) but BEFORE generic catch-alls.

    # Question words: "what is X", "who is X", "how does X work", etc.
    (re.compile(r'\b(?:what|who|when|where|why|how)\s+(?:is|are|was|were|do|does|did|can|could|would|should|will|has|have|had)\b.{3,}', re.I),
     'chat', lambda m: {'question': m.group(0).strip()}),

    # "tell me about X", "explain X", "describe X", "define X"
    (re.compile(r'\b(?:tell\s+me\s+(?:about|the|some)?|explain|describe|define|summarize|summarise)\s+(.{3,})', re.I),
     'chat', lambda m: {'question': m.group(0).strip()}),

    # Follow-ups: "what about X", "how about X", "and X?"
    (re.compile(r'\b(?:what\s+about|how\s+about|and\s+what\s+about|what\s+else)\s+(.+)', re.I),
     'chat', lambda m: {'question': m.group(0).strip()}),

    # "do you know X", "can you tell me X"
    (re.compile(r'\b(?:do\s+you\s+know|can\s+you\s+tell\s+me|could\s+you\s+tell\s+me)\s+(.+)', re.I),
     'chat', lambda m: {'question': m.group(0).strip()}),

    # Conversational "search X" → voice answer (NOT browser)
    # Explicit "search google" / "google X" already matched above → browser.
    (re.compile(r'\bsearch\s+(?:for\s+)?(.{3,})', re.I),
     'chat', lambda m: {'question': _clean_arg(m.group(1))}),

    # "search it on google" / "open it in google" — explicit browser override
    (re.compile(r'\b(?:search|look)\s+(?:it|that|this)\s+(?:on|in)\s+google\b', re.I),
     'search_google', lambda m: {'query': ''}),

    # Clear conversation: "forget the conversation", "clear chat", "new topic"
    (re.compile(r'\b(?:forget|clear|reset|wipe)\s+(?:the\s+)?(?:conversation|chat|history|context)\b', re.I),
     'clear_chat_history', lambda m: {}),
    (re.compile(r'\b(?:new\s+topic|fresh\s+start|start\s+over)\b', re.I),
     'clear_chat_history', lambda m: {}),

    # Open URL (must be before generic open catch-all)
    (re.compile(r'\b(?:open|visit|go\s+to)\s+([\w.-]+\.[a-z]{2,})\b', re.I), 'open_url', lambda m: {'url': m.group(1).strip()}),

    # --- DATASET LOADING & ANALYSIS ---
    # "load the churn dataset", "hey load churn data", "use superstore dataset", "load dataset churn"
    (re.compile(r'\b(?:load|use|bring\s+up)\s+(?:the\s+|my\s+)?(.+?)\s+(?:data|dataset|csv|file)\b', re.I),
     'load_dataset', lambda m: {'keyword': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:load|use|bring\s+up)\s+(?:data|dataset|csv|file)\s+(?:for\s+)?(.+)\b', re.I),
     'load_dataset', lambda m: {'keyword': _clean_arg(m.group(1))}),

    # "analyze my data and show the top earners" (no keyword, with optional question)
    # MUST come before keyword pattern so "my" / "the" aren't captured as keywords
    (re.compile(r'\b(?:analy[sz]e|check|summarize|look at)\s+(?:my|the)\s+(?:data|date)(?:\s+(?:and\s+)?(.+))?$', re.I),
     'quick_analyze', lambda m: {'question': _clean_arg(m.group(1)) if m.group(1) else 'Give me a summary'}),
    # "analyze the churn data file and say which..." → keyword='churn', question='say which...'
    (re.compile(r'\b(?:analy[sz]e|check|summarize|look at)\s+(?:the\s+|my\s+)?(\w+)\s+(?:data|date)(?:\s+file)?(?:\s+(?:and\s+)?(.+))?$', re.I),
     'quick_analyze', lambda m: {'keyword': _clean_arg(m.group(1)), 'question': _clean_arg(m.group(2)) if m.group(2) else 'Give me a summary'}),
    (re.compile(r'\b(?:what(?:\'s| is)\s+in\s+(?:my\s+|the\s+)?data)\b', re.I),
     'quick_analyze', lambda m: {}),
    # --- DATA RECALL (cross-session) ---
    # "open the recent data we analyzed" / "recall the last dataset" / "load previous data"
    (re.compile(r'\b(?:open|load|recall|resume|bring\s+up|go\s+back\s+to|show)\s+(?:the\s+|my\s+)?(?:recent|last|previous|earlier)\s+(?:data|dataset|file)(?:\s+(?:we\s+)?(?:analy[sz]ed|worked\s+on|used|checked))?(?:\s+(?:and\s+)?(.+))?$', re.I),
     'recall_data', lambda m: {'question': _clean_arg(m.group(1)) if m.group(1) else ''}),
    # "what was the last data I analyzed"
    (re.compile(r'\b(?:what|which)\s+(?:was|is)\s+(?:the\s+)?(?:last|recent|previous)\s+(?:data|dataset|file)\b', re.I),
     'recall_data', lambda m: {}),

    # --- FOLDER COMMANDS (High Priority) ---
    (re.compile(r'\b(?:open|show|explorer|start|launch)\s+(?:the\s+|my\s+)?(.+)\s+folder\b', re.I),
     'open_folder', lambda m: {'directory': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:open|show|explorer|start|launch)\s+(?:the\s+|my\s+)?(downloads?|desktop|documents?|music|videos?|pictures?|photos?)\b', re.I),
     'open_folder', lambda m: {'directory': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:list|show)\s+(?:my\s+)?(?:files\s+(?:in|on)\s+(?:the\s+)?)?(downloads?|desktop|documents?)\b', re.I),
     'list_files', lambda m: {'directory': _clean_arg(m.group(1))}),

    # --- NEWS / HEADLINE FOLLOW-UPS ---
    (re.compile(r'\b(?:explain|details?\s+on|tell\s+me\s+more\s+about|elaborate\s+on)\s+(?:headline\s+)?(?:number\s+)?(\d+|one|two|three|four|five|1|2|3|4|5)\b', re.I),
     'chat', lambda m: {'question': f"Explain headline #{m.group(1)} from the news you just read to me."}),
    (re.compile(r'\b(?:what\s+were\s+the\s+news|what\s+news\s+did\s+you\s+read|news\s+you\s+read\s+before|summarize\s+the\s+news)\b', re.I),
     'chat', lambda m: {'question': "Summarize the technology news headlines you read to me earlier."}),

    # --- GENERIC catch-alls (MUST BE LAST) ---
    # Require explicit application trigger or single word target, avoiding phrases like 'microsoft is open competing'
    (re.compile(r'\b(?:open|launch|start|run)\s+(?:app|application|program|software)?\s*([a-zA-Z0-9_\-\s]{1,20})$', re.I),
     'open_app', lambda m: {'app_name': _clean_arg(m.group(1))}),

    # ── Explorer-safe close (MUST be before generic close_app) ──
    # "close file explorer", "close explorer", "close files", "quit explorer"
    (re.compile(r'\b(?:close|exit|quit|kill)\s+(?:the\s+)?(?:file\s+)?explorer\b', re.I),
     'close_explorer_windows', lambda m: {}),
    (re.compile(r'\b(?:close|exit|quit|kill)\s+(?:the\s+)?files\b', re.I),
     'close_explorer_windows', lambda m: {}),

    # ── Shell recovery ──
    (re.compile(r'\b(?:recover|restore|restart|fix)\s+(?:the\s+)?(?:windows\s+)?(?:shell|desktop|taskbar)\b', re.I),
     'recover_explorer_shell', lambda m: {}),

    # ── Active window close ──
    (re.compile(r'\b(?:close|exit|quit|kill)(?:[,\s]+)?(?:this\s+)?(?:window|app|application|it|current\s+app)\b', re.I),
     'close_active_window', lambda m: {}),

    # ── Generic close (catch-all) ──
    (re.compile(r'\b(?:close|exit|quit|kill)(?:[,\s]+)?(.*)', re.I),
     'close_app', lambda m: {'app_name': _clean_arg(m.group(1))}),
]


def _clean_arg(text: str) -> str:
    """Strip trailing punctuation, whitespace, and redundant clauses from captured args."""
    # Stop at the first comma or ' and ' or ' then ' if it exists
    # This prevents catching hallucinated repetitions as part of the app name
    split_text = re.split(r'[,]| and | then ', text, flags=re.I)
    clean = split_text[0].strip()
    return re.sub(r'[\s.,!?;:]+$', '', clean).strip()


def _parse_delay(match) -> str:
    """Extract delay in seconds from a regex match."""
    raw = match.group(1) if match.lastindex and match.group(1) else '60'
    text = match.group(0).lower()
    seconds = int(raw)
    if 'minute' in text or 'min' in text:
        seconds *= 60
    return str(seconds)


def _check_workflow(command: str) -> Optional[str]:
    """Execute a predefined workflow plan when a trigger phrase is spoken."""
    if not command:
        return None

    cleaned = command.strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # STT often hears "work mode" as near-homophones like "work more".
    workflow_aliases = {
        'work more': 'work mode',
        'work mood': 'work mode',
        'workmode': 'work mode',
        'focus more': 'focus mode',
        'focus mood': 'focus mode',
    }

    for alias, canonical in workflow_aliases.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', cleaned):
            plan = WORKFLOWS.get(canonical)
            if plan:
                logger.info('Workflow matched via alias: %s -> %s', alias, canonical)
                result = execute_plan(plan, get_tool_map())
                return humanize_response(result)

    for trigger, plan in WORKFLOWS.items():
        pattern = r'\b' + re.escape(trigger.lower()) + r'\b'
        if re.search(pattern, cleaned):
            logger.info('Workflow matched: %s', trigger)
            result = execute_plan(plan, get_tool_map())
            return humanize_response(result)
    return None


def match_simple_intent(command: str) -> tuple | None:
    """Match a command against SIMPLE_INTENTS without executing anything.

    Returns (tool_name, args) for the first match, else None. Used by
    agents (e.g. TITAN) that need to translate free text into a tool call.
    """
    cleaned = (command or "").strip().lower()
    if not cleaned:
        return None
    for pattern, tool_name, arg_extractor in SIMPLE_INTENTS:
        try:
            match = pattern.search(cleaned)
        except Exception:
            continue
        if match:
            try:
                return tool_name, arg_extractor(match)
            except Exception:
                continue
    return None


def is_dismiss_command(text: str) -> bool:
    """Return True if the command asks DNA to leave active session mode."""
    if not text or not text.strip():
        return False
    cleaned = text.strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return any(pattern.search(cleaned) for pattern in DISMISS_PATTERNS)


# ════════════════════════════════════════════════════════════════════
# Project Commands — Cowork-style persistent workspaces
# ════════════════════════════════════════════════════════════════════

def _check_project_command(command: str) -> Optional[str]:
    """Handle start/switch/list/close/note/plan-mode commands.

    Returns a response string when matched, else None.
    """
    from core.session import update as session_update

    m = re.search(r'\b(?:start|open|switch to|change to|change project to)\s+project\s+([a-z0-9][a-z0-9\-_ ]{0,39})', command)
    if m:
        raw = m.group(1).strip()
        try:
            from core.projects import set_active_project
            clean = set_active_project(raw)
            session_update('active_skill', 'sys')
            return humanize_response(f"Project {clean} is ready, boss. Everything we do now stays in this workspace.")
        except ValueError:
            return humanize_response("Boss, that project name did not work. Use letters, numbers, and dashes.")

    if re.search(r'\b(?:list|show|what are)\s+(?:my\s+)?projects\b', command):
        from core.projects import list_projects
        names = list_projects()
        if not names:
            return humanize_response("Boss, there are no projects yet. Say start project followed by a name.")
        return humanize_response("Your projects, boss: " + ", ".join(names) + ".")

    if re.search(r'\b(?:close|exit|leave)\s+project\b', command):
        from core.projects import set_active_project
        set_active_project(None)
        return humanize_response("Closed the project, boss. Back in global mode.")

    m = re.search(r'\b(?:note to project|remember in this project|note for this project)\s*[:\-]?\s*(.+)', command)
    if m:
        text = m.group(1).strip()
        try:
            from core.projects import get_active_project, append_memory
            active = get_active_project()
            if not active:
                return humanize_response("Boss, start a project first, then I will keep notes in it.")
            if not text:
                return humanize_response("Boss, what should I note down in this project?")
            append_memory(active, text)
            return humanize_response(f"Noted in {active}, boss.")
        except ValueError:
            return humanize_response("Boss, that project name did not work.")

    m = re.search(r'\bplan mode\s+(on|off)\b', command)
    if m:
        session_update('plan_mode', m.group(1) == 'on')
        state = 'on' if m.group(1) == 'on' else 'off'
        return humanize_response(f"Plan mode {state}, boss.")

    m = re.search(r'\b(?:use\s+)?local[\s\-]?only\s+(on|off)\b', command)
    if m:
        flag = m.group(1) == 'on'
        session_update('local_only', flag)
        try:
            from pipeline.memory import save_preference
            save_preference('local_only', '1' if flag else '0')
        except Exception:
            pass
        state = 'on — cloud model off, templates and local only' if flag else 'off — cloud model back on'
        return humanize_response(f"Local-only mode {state}, boss.")

    if re.search(r'\buse\s+cloud\b', command):
        session_update('local_only', False)
        try:
            from pipeline.memory import save_preference
            save_preference('local_only', '0')
        except Exception:
            pass
        return humanize_response("Cloud model back on, boss.")

    return None





# ════════════════════════════════════════════════════════════════════
# Main Router
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
# Context Bridge — Feed skill results into chat memory for follow-ups
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
# Skill → Agent attribution for UI terminal logs.
# Direct skill executions (regex path, interceptors) run no agent, so
# without this their results never appear in any agent terminal.
# ════════════════════════════════════════════════════════════════════
_AGENT_FOR_SKILL = {
    'sys': 'TITAN', 'app_operator': 'TITAN',
    'org': 'VANGUARD', 'file': 'VANGUARD',
    'jobs': 'FORGE', 'career_ops': 'FORGE',
    'data': 'CIPHER',
    'chat': 'JARVIS', 'memory': 'JARVIS', 'learning': 'JARVIS',
    'web': 'HERMES', 'browser': 'HERMES', 'playwright': 'HERMES',
    'news': 'HERMES', 'weather': 'HERMES',
    'screen': 'ARGUS',
}


def _broadcast_skill_log(skill: str | None, tool_name: str, result: object) -> None:
    """Mirror a direct skill execution into its owner's agent terminal."""
    agent = _AGENT_FOR_SKILL.get(skill or '')
    if not agent:
        return
    try:
        from ui.window import broadcast_agent_log
        text = str(result or '')
        broadcast_agent_log(agent, f"[{tool_name}] {text[:140]}", "success")
    except Exception:
        pass


# Skills whose results should be remembered so follow-up questions work.
# E.g., "AI news" → result → "tell me more about the first one" → LLM knows context.
_CONTEXTUAL_SKILLS = {    'get_ai_news', 'get_tech_news', 'get_india_news', 'get_cricket_score',
    'get_headlines', 'get_news', 'morning_news_brief',
    'web_search', 'fetch_and_summarize',
    'get_weather', 'get_forecast',
    'enter_job_search_mode', 'next_jobs', 'previous_jobs',
    'chat',  # chat already handles its own, but this is a safety net
    'read_screen', 'describe_screen', 'find_error',
    'quick_analyze', 'analyze_data', 'recall_data', 'load_dataset',  # data analysis follow-ups
}


def _inject_context(user_command: str, skill_result: str, tool_name: str) -> None:
    """Inject a skill's command + result into chat history for follow-ups.

    Only injects for contextual skills — skips trivial commands like
    volume, time, brightness that don't need follow-up memory.
    """
    if tool_name not in _CONTEXTUAL_SKILLS:
        return
    if not skill_result or len(skill_result) < 10:
        return

    try:
        from skills.chat_skill import _add_to_history
        _add_to_history('user', user_command)
        _add_to_history('assistant', skill_result)
        logger.debug('Context injected for follow-up: %s (%d chars)', tool_name, len(skill_result))
    except Exception as e:
        logger.debug('Context injection skipped: %s', e)


_nexus_instance = None

def _get_nexus():
    global _nexus_instance
    if _nexus_instance is None:
        from core.session import get_blackboard
        from core.nexus import NexusOrchestrator
        _nexus_instance = NexusOrchestrator(get_blackboard())
    return _nexus_instance


def route(command: str, allow_llm: bool = True) -> Optional[str]:
    """Route a voice command to the appropriate tool.

    Flow:
      1. Check if there's a pending confirmation and handle it
      2. Match against regex intents (top-down, first match wins)
      3. If the matched tool is DANGEROUS → store pending, return warning
      4. If no regex match → fall back to LLM agent (with safety guards)
    """
    if not command or not command.strip():
        return None

    # Resolve pronouns using session state
    cleaned = command.strip().lower()

    # Phonetic STT normalization map for Whisper mishearings
    _PHONETIC_MAP = [
        (r'\borgas\b', 'nexus'),
        (r'\bmode details\b', 'more details'),
        (r'\bsummer restart\b', 'system restart'),
        (r'\blet s pull up\b', 'let us pull up'),
    ]
    for pattern, repl in _PHONETIC_MAP:
        cleaned = re.sub(pattern, repl, cleaned)

    cleaned = resolve_pronouns(cleaned)
    logger.debug('Routing command: "%s"', cleaned)

    # ── Step 1: Handle pending confirmations ──
    confirm_result = _check_confirmation(cleaned)
    if confirm_result is not None:
        return confirm_result

    # ── Step 1.4: Pending plan approval (Plan Mode) ──
    try:
        from pipeline.plan_executor import check_pending_plan
        plan_result = check_pending_plan(cleaned, get_tool_map())
        if plan_result is not None:
            return humanize_response(plan_result)
    except Exception as e:
        logger.debug('Pending plan check skipped: %s', e)

    # ── Step 1.5: Workflow template matching ──
    workflow_result = _check_workflow(cleaned)
    if workflow_result is not None:
        _broadcast_skill_log('chat', 'workflow', workflow_result)
        return workflow_result

    # ── Step 1.6: Project workspace commands ──
    project_result = _check_project_command(cleaned)
    if project_result is not None:
        return project_result

    # ── Step 1.7: Organizer pending confirmation ──
    # The organizer skill has its own yes/no flow (separate from dangerous tools).
    try:
        from skills.organizer_skill import has_pending, confirm_organize, cancel_organize
        if has_pending():
            from core.session import update as session_update
            if re.search(r'^(?:yes|yeah|go ahead|do it|confirm|proceed|sure|ok|okay)$', cleaned):
                session_update('active_skill', 'org')
                return humanize_response(confirm_organize())
            if re.search(r'^(?:no|nope|cancel|stop|never mind|don\'t|dont)$', cleaned):
                session_update('active_skill', 'org')
                return humanize_response(cancel_organize())
    except ImportError:
        pass

    # ── Step 1.8: Job search session commands ──
    # When in job search mode, intercept navigation commands.
    try:
        from skills.job_search_skill import (
            is_job_search_active, next_jobs, previous_jobs,
            open_job, save_job, search_role, exit_job_search,
        )
        if is_job_search_active():
            from core.session import update as session_update
            session_update('active_skill', 'jobs')
            # Next batch
            if re.search(r'\bnext\b', cleaned):
                return humanize_response(next_jobs())
            # Previous batch
            if re.search(r'\b(?:previous|back|prev)\b', cleaned):
                return humanize_response(previous_jobs())
            # Open job by number
            m = re.search(r'\bopen\s+(?:number\s+|job\s+)?(\d+)\b', cleaned)
            if m:
                return humanize_response(open_job(int(m.group(1))))
            # Save/bookmark job by number
            m = re.search(r'\b(?:save|bookmark)\s+(?:number\s+|job\s+)?(\d+)\b', cleaned)
            if m:
                return humanize_response(save_job(int(m.group(1))))
            # Save current
            if re.search(r'\b(?:save|bookmark)\s+(?:this|that|it)\b', cleaned):
                return humanize_response(save_job(1))
            # Switch role
            m = re.search(r'\bsearch\s+(?:for\s+)?(data analyst|data scientist|business analyst|data engineer|ml engineer)\b', cleaned)
            if m:
                return humanize_response(search_role(m.group(1)))
            # Exit job search
            if re.search(r'\b(?:exit|stop|end|quit|leave)\s+job\s+search\b', cleaned):
                return humanize_response(exit_job_search())
    except ImportError:
        pass

    # ── Step 1.9: Data analysis follow-up interceptor ──
    # Only intercept when explicitly targeting the active dataset or data query
    try:
        from core.session import get as session_get
        active_file = session_get('active_file')
        if active_file:
            _EXPLICIT_DATA_PATTERNS = [
                re.compile(r'\b(?:analyze|analyse|query|filter|group|sort|dataset|table|sql|csv|excel)\b', re.I),
                re.compile(r'\b(?:what is|calculate|show|get)\s+(?:the\s+)?(?:salary|headcount|row|column|count|average|total|sum|max|min)\s+(?:in|of|from)\s+(?:the\s+)?(?:data|file|table|dataset)\b', re.I),
            ]
            if any(p.search(cleaned) for p in _EXPLICIT_DATA_PATTERNS):
                logger.info('Explicit data command matched for active file: %s', active_file)
                from skills.data_engine import run_analysis
                from core.session import update as session_update
                session_update('active_skill', 'data')
                result = run_analysis(active_file, cleaned)
                response = humanize_response(result)
                _inject_context(cleaned, result, 'analyze_data')
                _broadcast_skill_log('data', 'analyze_data', result)
                return response
    except ImportError:
        pass

    # Avoid LLM fallback for standalone confirm/cancel when no action is pending.
    if re.fullmatch(r'(?:confirm(?:\s+(?:lock|restart|shutdown))?|cancel|abort|never\s+mind)', cleaned):
        return humanize_response('There is no pending action to confirm right now.')

    # ── Step 1.95: Gateway Classification ──
    from pipeline.gateway_classifier import classify
    category = classify(cleaned)
    if category == 'B':
        logger.info('Gateway classified command as Category B (reasoning). Direct to NEXUS.')
        if not allow_llm:
            return None
        nexus = _get_nexus()
        bb_msg = nexus.execute(cleaned)
        return bb_msg.payload.get("result")

    # ── Step 2: Regex intent matching ──
    for pattern, tool_name, arg_extractor in SIMPLE_INTENTS:
        match = pattern.search(cleaned)
        if match:
            logger.info('Intent matched: %s', tool_name)

            # Safety: blocked tools never execute
            if is_tool_blocked(tool_name):
                logger.critical('BLOCKED tool via regex: %s', tool_name)
                return humanize_response('That action is blocked for safety reasons.')

            tool_fn = get_tool_map().get(tool_name)
            if not tool_fn:
                logger.error('Tool not found: %s', tool_name)
                return f'I understood {tool_name} but the tool is missing.'

            args = arg_extractor(match)
            logger.debug('Arguments: %s', args)

            # Safety: dangerous tools require confirmation
            if is_tool_dangerous(tool_name):
                warning = get_danger_warning(tool_name)
                _set_pending(tool_name, args, warning)
                logger.warning('Dangerous tool "%s" requires confirmation', tool_name)
                return humanize_response(warning)

            try:
                # Update active skill
                from core.skill_registry import get_skill_for_tool
                from core.session import update as session_update
                skill = get_skill_for_tool(tool_name)
                if skill:
                    session_update('active_skill', skill)

                # Clear stale active_file when executing unrelated skills
                # (keeps data context from bleeding into unrelated commands)
                if tool_name not in ('quick_analyze', 'analyze_data', 'chat', 'clear_chat_history'):
                    session_update('active_file', None)

                # System tools run through TITAN so the swarm role is real:
                # per-agent logs, UI attribution, and blackboard history.
                if skill == 'sys':
                    try:
                        titan = _get_nexus().titan
                    except Exception as e:
                        logger.debug('TITAN unavailable, direct execution: %s', e)
                        titan = None
                    if titan is not None:
                        session_update('active_agent', 'TITAN')
                        try:
                            bb_msg = titan.execute(
                                cleaned, {"tool_name": tool_name, "tool_args": args})
                            payload = bb_msg.payload or {}
                            result = payload.get('result', '')
                            if bb_msg.status == 'error' or 'error' in payload:
                                return 'Sorry boss, I ran into a problem while executing that command.'
                            response = humanize_response(result)
                            _inject_context(cleaned, result, tool_name)
                            return response
                        except Exception as e:
                            logger.error('TITAN execution failed for %s: %s', tool_name, e, exc_info=True)
                            return 'Sorry boss, I ran into a problem while executing that command.'
                    # else: fall through to direct execution below

                result = tool_fn(**args)
                response = humanize_response(result)

                # ── Feed skill results into chat history for follow-ups ──
                # This enables: "AI news" → [headlines] → "tell me more about #1"
                # Without this, the LLM has no idea what DNA just said.
                _inject_context(cleaned, result, tool_name)
                _broadcast_skill_log(skill, tool_name, result)

                return response
            except Exception as e:
                logger.error('Regex tool execution failed for %s: %s', tool_name, e, exc_info=True)
                return 'Sorry boss, I ran into a problem while executing that command.'

    # ── Step 3: LLM fallback ──
    logger.info('No simple intent matched for Category A command: "%s". Falling back to NEXUS.', cleaned)
    if not allow_llm:
        return None

    nexus = _get_nexus()
    bb_msg = nexus.execute(cleaned)
    return bb_msg.payload.get("result")

