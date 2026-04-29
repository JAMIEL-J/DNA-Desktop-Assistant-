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

    # ── Cancellation phrases ──
    cancel_patterns = [
        re.compile(r'\bcancel\b', re.I),
        re.compile(r'\bno\b', re.I),
        re.compile(r'\bnope\b', re.I),
        re.compile(r'\bstop\b', re.I),
        re.compile(r'\babort\b', re.I),
        re.compile(r'\bnever\s+mind\b', re.I),
        re.compile(r'\bdo\s+not\b', re.I),
        re.compile(r'\bdon\s*t\b', re.I),
        re.compile(r'\bnegative\b', re.I),
        re.compile(r'\bforget\s+it\b', re.I),
        re.compile(r'\bskip\b', re.I),
    ]
    if any(pattern.search(cleaned) for pattern in cancel_patterns):
        logger.info('User cancelled pending: %s', pending_tool)
        _clear_pending()
        return humanize_response('No problem, I\'ve cancelled that for you.')

    # ── Confirmation phrases ──
    confirm_patterns = [
        re.compile(r'\bconfirm\b', re.I),
        re.compile(r'\byes\b', re.I),
        re.compile(r'\byeah\b', re.I),
        re.compile(r'\byep\b', re.I),
        re.compile(r'\bsure\b', re.I),
        re.compile(r'\bgo\s+ahead\b', re.I),
        re.compile(r'\bdo\s+it\b', re.I),
        re.compile(r'\bproceed\b', re.I),
        re.compile(r'\bokay\b', re.I),
        re.compile(r'\bok\b', re.I),
        re.compile(r'\baffirmative\b', re.I),
        re.compile(r'\bconfirm\s+shutdown\b', re.I),
        re.compile(r'\bconfirm\s+restart\b', re.I),
        re.compile(r'\bconfirm\s+lock\b', re.I),
        re.compile(r'\bconfirm\s+kill\b', re.I),
    ]
    if any(pattern.search(cleaned) for pattern in confirm_patterns):
        tool_name = pending_tool
        args = _pending_confirmation['args']
        _clear_pending()

        logger.info('User CONFIRMED dangerous action: %s', tool_name)
        tool_fn = get_tool_map().get(tool_name)
        if tool_fn:
            try:
                result = tool_fn(**args)
                return humanize_response(result)
            except Exception as e:
                logger.error('Confirmed tool %s failed: %s', tool_name, e)
                return humanize_response(f'Could not execute {tool_name}: {str(e)}')
        return humanize_response(f'Tool {tool_name} not found.')

    # Command is unrelated — clear pending and process normally
    logger.info('Unrelated command while pending — clearing pending: %s', pending_tool)
    _clear_pending()
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

    # --- SEARCH & NAVIGATION ---
    (re.compile(r'\b(?:play|search)\s+(.+)\s+on\s+youtube\b', re.I), 'search_youtube', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bsearch\s+google\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bgoogle\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),

    # --- JOB SEARCH (before generic search catch-all) ---
    (re.compile(r'\b(?:show|find|get|check|search|are there|any).+(?:job|opening|vacancies|hiring|position)', re.I),
     'check_jobs', lambda m: {}),
    (re.compile(r'\b(?:job|opening|vacancies).+(?:data analyst|data science|analyst|fresher)', re.I),
     'check_jobs', lambda m: {}),
    (re.compile(r'\b(?:is there|are there).+(?:opening|job|hiring|vacancy)', re.I),
     'check_jobs', lambda m: {}),
    (re.compile(r'\bwhat.+(?:job|opening).+(?:available|out there)', re.I),
     'check_jobs', lambda m: {}),
    (re.compile(r'\bopen\s+(?:job|naukri|indeed|internshala)\s+portal', re.I),
     'open_job_portals', lambda m: {}),
    (re.compile(r'\b(?:browse|search)\s+jobs\b', re.I),
     'open_job_portals', lambda m: {}),

    # Generic search (catch-all — MUST be after specific search intents)
    (re.compile(r'\bsearch\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:open|visit|go\s+to)\s+([\w.-]+\.[a-z]{2,})\b', re.I), 'open_url', lambda m: {'url': m.group(1).strip()}),

    # --- DATA ANALYSIS ---
    # "analyze the churn data file" → keyword='churn'
    # "analyze the sales data" → keyword='sales'  
    (re.compile(r'\b(?:analy[sz]e|check|summarize|look at)\s+(?:the\s+|my\s+)?(\w+)\s+(?:data|date)(?:\s+file)?\b', re.I),
     'quick_analyze', lambda m: {'keyword': _clean_arg(m.group(1))}),
    # "analyze my data" (no keyword)
    (re.compile(r'\b(?:analy[sz]e|check|summarize|look at)\s+(?:my\s+|the\s+)?(?:data|date)\b', re.I),
     'quick_analyze', lambda m: {}),
    (re.compile(r'\b(?:what(?:\'s| is)\s+in\s+(?:my\s+|the\s+)?data)\b', re.I),
     'quick_analyze', lambda m: {}),

    # --- FOLDER COMMANDS (High Priority) ---
    (re.compile(r'\b(?:open|show|explorer|start|launch)\s+(?:the\s+|my\s+)?(.+)\s+folder\b', re.I),
     'open_folder', lambda m: {'directory': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:open|show|explorer|start|launch)\s+(?:the\s+|my\s+)?(downloads?|desktop|documents?|music|videos?|pictures?|photos?)\b', re.I),
     'open_folder', lambda m: {'directory': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:list|show)\s+(?:my\s+)?(?:files\s+(?:in|on)\s+(?:the\s+)?)?(downloads?|desktop|documents?)\b', re.I),
     'list_files', lambda m: {'directory': _clean_arg(m.group(1))}),

    # --- GENERIC catch-alls (MUST BE LAST) ---
    (re.compile(r'\b(?:open|launch|start|run)(?:[,\s]+)?(.*)', re.I),
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


def is_dismiss_command(text: str) -> bool:
    """Return True if the command asks DNA to leave active session mode."""
    if not text or not text.strip():
        return False
    cleaned = text.strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return any(pattern.search(cleaned) for pattern in DISMISS_PATTERNS)





# ════════════════════════════════════════════════════════════════════
# Main Router
# ════════════════════════════════════════════════════════════════════

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
    cleaned = resolve_pronouns(cleaned)
    logger.debug('Routing command: "%s"', cleaned)

    # ── Step 1: Handle pending confirmations ──
    confirm_result = _check_confirmation(cleaned)
    if confirm_result is not None:
        return confirm_result

    # ── Step 1.5: Workflow template matching ──
    workflow_result = _check_workflow(cleaned)
    if workflow_result is not None:
        return workflow_result

    # Avoid LLM fallback for standalone confirm/cancel when no action is pending.
    if re.fullmatch(r'(?:confirm(?:\s+(?:lock|restart|shutdown))?|cancel|abort|never\s+mind)', cleaned):
        return humanize_response('There is no pending action to confirm right now.')

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

            result = tool_fn(**args)
            return humanize_response(result)

    # ── Step 3: LLM fallback ──
    logger.info('No simple intent matched for: "%s"', cleaned)
    if not allow_llm:
        return None

    logger.info('Falling back to LLM agent for: "%s"', cleaned)
    return handle_complex_command(cleaned, get_tool_map())
