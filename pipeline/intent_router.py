# 1. stdlib
import logging
import re
import subprocess
from typing import Optional

# 2. internal
from pipeline.llm_agent import handle_complex_command
from skills.system_skill import TOOLS as SYSTEM_TOOLS
from skills.browser_skill import TOOLS as BROWSER_TOOLS
from skills.file_skill import TOOLS as FILE_TOOLS

logger = logging.getLogger('dna.router')

# Regex-based simple intents -- matched from top to bottom, first match wins
# IMPORTANT: Specific patterns MUST come before generic catch-alls (open_app)
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

    # Shutdown / Restart / Lock
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
    # 1. Explicit folder commands: "open projects folder", "show my downloads folder"
    (re.compile(r'\b(?:open|show|explorer|start|launch)\s+(?:the\s+|my\s+)?(.+)\s+folder\b', re.I),
     'open_folder', lambda m: {'directory': _clean_arg(m.group(1))}),

    # 2. Known folders (shorthand): "open downloads", "show documents"
    (re.compile(r'\b(?:open|show|explorer|start|launch)\s+(?:the\s+|my\s+)?(downloads?|desktop|documents?|music|videos?|pictures?|photos?)\b', re.I),
     'open_folder', lambda m: {'directory': _clean_arg(m.group(1))}),

    # 3. List folder: "list my downloads"
    (re.compile(r'\b(?:list|show)\s+(?:my\s+)?(?:files\s+(?:in|on)\s+(?:the\s+)?)?(downloads?|desktop|documents?)\b', re.I),
     'list_files', lambda m: {'directory': _clean_arg(m.group(1))}),

    # --- GENERIC catch-alls (MUST BE LAST) ---
    (re.compile(r'\b(?:open|launch|start|run)\s+(.+)', re.I),
     'open_app', lambda m: {'app_name': _clean_arg(m.group(1))}),
    (re.compile(r'\b(?:close|exit|quit|kill)\s+(.+)', re.I),
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
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True, check=True)
        current = int(result.stdout.strip() if result.stdout.strip() else '50')
        new_level = min(100, current + 10)
        cmd_set = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {new_level})"'
        subprocess.run(cmd_set, shell=True, check=True)
        return f'Brightness increased to {new_level} percent.'
    except Exception:
        return 'Could not increase brightness.'


def _brightness_down() -> str:
    """Decrease brightness by 10 percent."""
    try:
        cmd_get = 'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True, check=True)
        current = int(result.stdout.strip() if result.stdout.strip() else '50')
        new_level = max(0, current - 10)
        cmd_set = f'PowerShell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {new_level})"'
        subprocess.run(cmd_set, shell=True, check=True)
        return f'Brightness decreased to {new_level} percent.'
    except Exception:
        return 'Could not decrease brightness.'


# Extended tools map -- all skills merged
_EXTENDED_TOOLS = {
    **SYSTEM_TOOLS,
    **BROWSER_TOOLS,
    **FILE_TOOLS,
    'volume_up': _volume_up,
    'volume_down': _volume_down,
    'brightness_up': _brightness_up,
    'brightness_down': _brightness_down,
}


def route(command: str, allow_llm: bool = True) -> Optional[str]:
    """Route a voice command to the appropriate tool."""
    if not command or not command.strip():
        return None

    cleaned = command.strip().lower()
    logger.debug('Routing command: "%s"', cleaned)

    for pattern, tool_name, arg_extractor in SIMPLE_INTENTS:
        # Search for pattern anywhere in the string
        match = pattern.search(cleaned)
        if match:
            logger.info('Intent matched: %s', tool_name)
            tool_fn = _EXTENDED_TOOLS.get(tool_name)
            if not tool_fn:
                logger.error('Tool not found: %s', tool_name)
                return f'I understood {tool_name} but the tool is missing.'

            args = arg_extractor(match)
            logger.debug('Arguments: %s', args)
            return tool_fn(**args)

    logger.info('No simple intent matched for: "%s"', cleaned)
    if not allow_llm:
        return None

    logger.info('Falling back to LLM agent for: "%s"', cleaned)
    return handle_complex_command(cleaned, _EXTENDED_TOOLS)
