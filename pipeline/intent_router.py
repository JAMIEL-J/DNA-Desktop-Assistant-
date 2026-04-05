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
from pipeline.llm_agent import handle_complex_command
from skills.system_skill import TOOLS as SYSTEM_TOOLS
from skills.browser_skill import TOOLS as BROWSER_TOOLS
from skills.file_skill import TOOLS as FILE_TOOLS
from core.safety import (
    is_tool_dangerous,
    is_tool_blocked,
    get_danger_warning,
)

logger = logging.getLogger('dna.router')

# Win32: hide subprocess console windows
CREATE_NO_WINDOW = 0x08000000

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

    # ── Cancellation phrases ──
    cancel_patterns = [
        'cancel', 'no', 'nope', 'stop', 'abort', 'never mind',
        'don\'t', 'do not', 'negative', 'forget it', 'skip',
    ]
    if any(phrase in cleaned for phrase in cancel_patterns):
        logger.info('User cancelled pending: %s', pending_tool)
        _clear_pending()
        return 'Cancelled. No action was taken.'

    # ── Confirmation phrases ──
    confirm_patterns = [
        'confirm', 'yes', 'yeah', 'yep', 'sure', 'go ahead',
        'do it', 'proceed', 'okay', 'ok', 'affirmative',
        'confirm shutdown', 'confirm restart', 'confirm lock',
    ]
    if any(phrase in cleaned for phrase in confirm_patterns):
        tool_name = pending_tool
        args = _pending_confirmation['args']
        _clear_pending()

        logger.info('User CONFIRMED dangerous action: %s', tool_name)
        tool_fn = _EXTENDED_TOOLS.get(tool_name)
        if tool_fn:
            try:
                return tool_fn(**args)
            except Exception as e:
                logger.error('Confirmed tool %s failed: %s', tool_name, e)
                return f'Could not execute {tool_name}: {str(e)}'
        return f'Tool {tool_name} not found.'

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
    (re.compile(r'\block\s+(?:the\s+)?(?:screen|computer|pc)\b', re.I), 'lock_screen', lambda m: {}),

    # System Utilities
    (re.compile(r'\b(?:empty|clear)\s+(?:the\s+)?(?:recycle\s+)?bin\b', re.I), 'empty_recycle_bin', lambda m: {}),
    (re.compile(r'\b(?:system\s+status|pc\s+status|computer\s+status|how\s+is\s+my\s+(?:pc|computer)\s+doing)\b', re.I), 'get_system_status', lambda m: {}),

    # --- SEARCH & NAVIGATION ---
    (re.compile(r'\b(?:play|search)\s+(.+)\s+on\s+youtube\b', re.I), 'search_youtube', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bsearch\s+google\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bgoogle\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\bsearch\s+(?:for\s+)?(.+)', re.I), 'search_google', lambda m: {'query': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:open|visit|go\s+to)\s+([\w.-]+\.[a-z]{2,})\b', re.I), 'open_url', lambda m: {'url': m.group(1).strip()}),

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
    (re.compile(r'\b(?:close|exit|quit|kill)(?:[,\s]+)?(?:this\s+)?(?:window|app|application|it|current\s+app)\b', re.I),
     'close_active_window', lambda m: {}),
    (re.compile(r'\b(?:close|exit|quit|kill)(?:[,\s]+)?(.*)', re.I),
     'close_app', lambda m: {'app_name': _clean_arg(m.group(1))}),
]


def _clean_arg(text: str) -> str:
    """Strip trailing punctuation and whitespace from captured args."""
    return re.sub(r'[\s.,!?;:]+$', '', text).strip()


def _parse_delay(match) -> str:
    """Extract delay in seconds from a regex match."""
    raw = match.group(1) if match.lastindex and match.group(1) else '60'
    text = match.group(0).lower()
    seconds = int(raw)
    if 'minute' in text or 'min' in text:
        seconds *= 60
    return str(seconds)


# ════════════════════════════════════════════════════════════════════
# Volume / Brightness step functions
# ════════════════════════════════════════════════════════════════════

def _volume_up() -> str:
    """Increase volume by 10 percent."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        current = vol.GetMasterVolumeLevelScalar()
        new_level = min(1.0, current + 0.1)
        vol.SetMasterVolumeLevelScalar(new_level, None)
        return f'Volume increased to {round(new_level * 100)} percent.'
    except Exception as e:
        return f'Could not increase volume: {str(e)}'


def _volume_down() -> str:
    """Decrease volume by 10 percent."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        vol = device.EndpointVolume
        current = vol.GetMasterVolumeLevelScalar()
        new_level = max(0.0, current - 0.1)
        vol.SetMasterVolumeLevelScalar(new_level, None)
        return f'Volume decreased to {round(new_level * 100)} percent.'
    except Exception as e:
        return f'Could not decrease volume: {str(e)}'


def _brightness_up() -> str:
    """Increase brightness by 10 percent."""
    try:
        cmd_get = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True,
                                check=True, creationflags=CREATE_NO_WINDOW)
        current = int(result.stdout.strip() if result.stdout.strip() else '50')
        new_level = min(100, current + 10)
        cmd_set = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {new_level})"'
        subprocess.run(cmd_set, shell=True, check=True,
                       creationflags=CREATE_NO_WINDOW)
        return f'Brightness increased to {new_level} percent.'
    except Exception:
        return 'Could not increase brightness.'


def _brightness_down() -> str:
    """Decrease brightness by 10 percent."""
    try:
        cmd_get = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True,
                                check=True, creationflags=CREATE_NO_WINDOW)
        current = int(result.stdout.strip() if result.stdout.strip() else '50')
        new_level = max(0, current - 10)
        cmd_set = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {new_level})"'
        subprocess.run(cmd_set, shell=True, check=True,
                       creationflags=CREATE_NO_WINDOW)
        return f'Brightness decreased to {new_level} percent.'
    except Exception:
        return 'Could not decrease brightness.'


# ════════════════════════════════════════════════════════════════════
# Extended Tools Map — all skills merged
# ════════════════════════════════════════════════════════════════════

_EXTENDED_TOOLS = {
    **SYSTEM_TOOLS,
    **BROWSER_TOOLS,
    **FILE_TOOLS,
    'volume_up': _volume_up,
    'volume_down': _volume_down,
    'brightness_up': _brightness_up,
    'brightness_down': _brightness_down,
}


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

    cleaned = command.strip().lower()
    logger.debug('Routing command: "%s"', cleaned)

    # ── Step 1: Handle pending confirmations ──
    confirm_result = _check_confirmation(cleaned)
    if confirm_result is not None:
        return confirm_result

    # ── Step 2: Regex intent matching ──
    for pattern, tool_name, arg_extractor in SIMPLE_INTENTS:
        match = pattern.search(cleaned)
        if match:
            logger.info('Intent matched: %s', tool_name)

            # Safety: blocked tools never execute
            if is_tool_blocked(tool_name):
                logger.critical('BLOCKED tool via regex: %s', tool_name)
                return 'That action is blocked for safety reasons.'

            tool_fn = _EXTENDED_TOOLS.get(tool_name)
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
                return warning

            return tool_fn(**args)

    # ── Step 3: LLM fallback ──
    logger.info('No simple intent matched for: "%s"', cleaned)
    if not allow_llm:
        return None

    logger.info('Falling back to LLM agent for: "%s"', cleaned)
    return handle_complex_command(cleaned, _EXTENDED_TOOLS)
