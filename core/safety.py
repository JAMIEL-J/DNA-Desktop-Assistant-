# core/safety.py
# ──────────────────────────────────────────────────────────────────────
# DNA Safety & Security Layer
# Prevents destructive operations from executing without confirmation,
# blocks OS-critical path access, and sanitises all subprocess commands.
# ──────────────────────────────────────────────────────────────────────

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger('dna.safety')

# ── 1. PROTECTED SYSTEM PATHS ──────────────────────────────────────
# These paths must NEVER be targets of delete / move / overwrite ops.
_WINDOWS_DIR = os.environ.get('SYSTEMROOT', r'C:\Windows')
_PROGRAM_FILES = os.environ.get('PROGRAMFILES', r'C:\Program Files')
_PROGRAM_FILES_X86 = os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')
_SYSTEM_DRIVE = os.environ.get('SYSTEMDRIVE', 'C:')

# Paths where the entire directory tree is protected (path + all descendants)
TREE_PROTECTED_PATHS = [
    Path(_WINDOWS_DIR),                          # C:\Windows (includes System32, SysWOW64)
    Path(_PROGRAM_FILES),                        # C:\Program Files
    Path(_PROGRAM_FILES_X86),                    # C:\Program Files (x86)
    Path(os.environ.get('ProgramData', r'C:\ProgramData')),
]

# Paths that are protected at the EXACT level only (not their user-facing children)
# e.g. we block "C:\" itself but NOT "C:\Users\ADMIN\Desktop"
EXACT_PROTECTED_PATHS = [
    Path(_SYSTEM_DRIVE + '\\'),                  # Root of system drive (C:\)
    Path.home() / 'AppData',                     # AppData root
    Path.home() / 'AppData' / 'Local',           # AppData\Local
    Path.home() / 'AppData' / 'Roaming',         # AppData\Roaming
    Path.home() / 'AppData' / 'LocalLow',        # AppData\LocalLow
]

# File extensions we should never touch
PROTECTED_EXTENSIONS = {
    '.sys', '.dll', '.msi', '.drv', '.ocx',
    '.bat', '.cmd', '.ps1', '.vbs', '.reg',          # Script files
    '.efi', '.inf', '.cat',                           # Driver/boot files
}

# ── 2. DANGEROUS TOOL NAMES ────────────────────────────────────────
# Tools that require explicit user confirmation before execution.
DANGEROUS_TOOLS = {
    'shutdown_computer',
    'restart_computer',
    'empty_recycle_bin',
    'lock_screen',
}

# Tools the LLM is NEVER allowed to call (even if it tries)
BLOCKED_TOOLS = {
    'format_disk',       # Doesn't exist yet — but block preemptively
    'delete_system',
    'rm_rf',
    'wipe',
}

# ── 3. DANGEROUS SHELL PATTERNS ────────────────────────────────────
# Regex patterns that indicate a subprocess command is dangerous.
DANGEROUS_CMD_PATTERNS = [
    re.compile(r'\bformat\s+[A-Za-z]:', re.I),           # format C:
    re.compile(r'\brd\s+/s', re.I),                      # rd /s (recursive dir delete)
    re.compile(r'\brmdir\s+/s', re.I),                   # rmdir /s
    re.compile(r'\bdel\s+/[sfq]', re.I),                 # del /s /f /q
    re.compile(r'\bRemove-Item\b.*-Recurse', re.I),      # PowerShell rm -r
    re.compile(r'\brm\s+-r', re.I),                      # Unix-style rm -r
    re.compile(r'\bsfc\s+/scannow', re.I),               # System file checker
    re.compile(r'\bdism\b', re.I),                       # DISM (image management)
    re.compile(r'\bbcdedit\b', re.I),                    # Boot config editor
    re.compile(r'\breg\s+(delete|add)', re.I),            # Registry modification
    re.compile(r'\bnet\s+user\b', re.I),                 # User account management
    re.compile(r'\bnet\s+stop\b', re.I),                 # Service stopping
    re.compile(r'\bsc\s+(delete|stop)', re.I),            # Service control
    re.compile(r'\bdiskpart\b', re.I),                   # Disk partitioning
    re.compile(r'\bchkdsk\b.*?/[rfx]', re.I),            # Disk repair
    re.compile(r'\bwmic\b.*?delete', re.I),              # WMI deletion
    re.compile(r'\bpowershell\b.*?(Invoke-WebRequest|iwr|curl|wget)', re.I),  # Downloads
    re.compile(r'\bSet-ExecutionPolicy\b', re.I),        # PS execution policy
]

# Characters that enable shell injection
INJECTION_CHARS = re.compile(r'[&|;`$><\'"\\]')


# ── 4. PUBLIC API ──────────────────────────────────────────────────

def is_path_protected(target: str | Path) -> bool:
    """Return True if `target` falls inside any protected system path.

    Uses two-tier checking:
      - TREE_PROTECTED: path OR any descendant is blocked
      - EXACT_PROTECTED: only the exact path itself is blocked
    """
    try:
        target_path = Path(target).resolve()

        # Tier 1: Tree-protected — block path and ALL children
        for protected in TREE_PROTECTED_PATHS:
            try:
                prot_resolved = protected.resolve()
                if target_path == prot_resolved:
                    return True
                target_path.relative_to(prot_resolved)
                return True  # target is inside the protected tree
            except (ValueError, OSError):
                continue

        # Tier 2: Exact-protected — block ONLY the exact path (not children)
        for protected in EXACT_PROTECTED_PATHS:
            try:
                prot_resolved = protected.resolve()
                if target_path == prot_resolved:
                    return True
            except OSError:
                continue

        # Check extension
        if target_path.suffix.lower() in PROTECTED_EXTENSIONS:
            return True

        return False
    except Exception:
        # If we can't resolve the path, be safe and block
        return True


def is_tool_dangerous(tool_name: str) -> bool:
    """Return True if the tool requires user confirmation."""
    return tool_name in DANGEROUS_TOOLS


def is_tool_blocked(tool_name: str) -> bool:
    """Return True if the tool must NEVER execute."""
    return tool_name in BLOCKED_TOOLS


def is_command_dangerous(cmd: str) -> bool:
    """Return True if a shell command matches known-dangerous patterns."""
    if not cmd:
        return False
    for pattern in DANGEROUS_CMD_PATTERNS:
        if pattern.search(cmd):
            logger.warning('BLOCKED dangerous command pattern: %s', cmd[:120])
            return True
    return False


def sanitise_app_name(name: str) -> Optional[str]:
    """Sanitise an application name to prevent injection.

    Returns the cleaned name or None if it looks malicious.
    """
    if not name or not name.strip():
        return None

    cleaned = name.strip()

    # Block shell injection characters
    if INJECTION_CHARS.search(cleaned):
        logger.warning('BLOCKED app name with injection chars: %s', cleaned)
        return None

    # Block excessively long names (likely hallucination)
    if len(cleaned) > 120:
        logger.warning('BLOCKED oversized app name (%d chars)', len(cleaned))
        return None

    # Block if it looks like a path traversal
    if '..' in cleaned or cleaned.startswith('/') or cleaned.startswith('\\'):
        logger.warning('BLOCKED path-traversal app name: %s', cleaned)
        return None

    return cleaned


def get_danger_warning(tool_name: str) -> str:
    """Return a human-readable warning for a dangerous tool."""
    warnings = {
        'shutdown_computer': (
            '⚠️ WARNING: This will shut down your computer. '
            'All unsaved work will be lost. '
            'Say "confirm shutdown" to proceed or "cancel" to abort.'
        ),
        'restart_computer': (
            '⚠️ WARNING: This will restart your computer. '
            'All unsaved work will be lost. '
            'Say "confirm restart" to proceed or "cancel" to abort.'
        ),
        'empty_recycle_bin': (
            '⚠️ WARNING: This will permanently delete all items in your Recycle Bin. '
            'This action cannot be undone. '
            'Say "confirm" to proceed or "cancel" to abort.'
        ),
        'lock_screen': (
            '⚠️ NOTE: This will lock your screen. '
            'You will need to enter your password to unlock. '
            'Say "confirm lock" to proceed or "cancel" to abort.'
        ),
    }
    return warnings.get(tool_name, f'⚠️ WARNING: {tool_name} requires confirmation.')
