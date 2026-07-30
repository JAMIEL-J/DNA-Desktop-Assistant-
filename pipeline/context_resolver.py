# pipeline/context_resolver.py
# ──────────────────────────────────────────────────────────────────────
# Context Resolver — Session state + pronoun resolution (v2)
# ──────────────────────────────────────────────────────────────────────

import re
import logging
from core.session import get

logger = logging.getLogger('dna.context')

def resolve_pronouns(command: str) -> str:
    """Replace pronouns in the command with active context."""
    if not command:
        return command

    active_app = get('active_app')
    active_file = get('active_file')
    
    # Check Blackboard if no active app/file is set
    bb_history = []
    try:
        from core.blackboard import get_global_blackboard
        bb_history = get_global_blackboard().get_recent_history(1)
    except Exception:
        pass

    if not active_app and not active_file and not bb_history:
        return command

    resolved_command = command

    # 1. Explicit app pronouns
    if active_app:
        app_pronouns = [r'\bthis app\b', r'\bthat app\b', r'\bthe app\b']
        for p in app_pronouns:
            resolved_command = re.sub(p, lambda m: active_app, resolved_command, flags=re.I)

    # 2. Explicit file/folder pronouns
    if active_file:
        file_pronouns = [r'\bthis file\b', r'\bthat file\b', r'\bthe file\b', 
                         r'\bthis folder\b', r'\bthat folder\b', r'\bthe folder\b']
        for p in file_pronouns:
            resolved_command = re.sub(p, lambda m: active_file, resolved_command, flags=re.I)

    # 3. Ambiguous pronouns (it, this, that)
    ambiguous_pronouns = [r'\bit\b', r'\bthis\b', r'\bthat\b']
    has_ambiguous = any(re.search(p, resolved_command, flags=re.I) for p in ambiguous_pronouns)
    
    if has_ambiguous:
        app_verbs = [r'\bclose\b', r'\bexit\b', r'\bquit\b', r'\bkill\b']
        file_verbs = [r'\bsummarise\b', r'\bsummarize\b', r'\banalyze\b', r'\banalyse\b', r'\bread\b', r'\blist\b', r'\bopen\b']
        
        is_app_context = any(re.search(v, resolved_command, flags=re.I) for v in app_verbs)
        is_file_context = any(re.search(v, resolved_command, flags=re.I) for v in file_verbs)
        
        target = None
        if is_app_context and active_app:
            target = active_app
        elif is_file_context and active_file:
            target = active_file
        
        if not target:
            # Fallbacks: check active_file, active_app, or last sub-agent output from Blackboard
            if active_file:
                target = active_file
            elif active_app:
                target = active_app
            else:
                try:
                    from core.blackboard import get_global_blackboard
                    bb = get_global_blackboard()
                    history = bb.get_recent_history(1)
                    if history:
                        target = f"the recent {history[0].get('agent_id')} result ({history[0].get('result')})"
                except Exception:
                    pass

        if target:
            # Target is substituted once (or at most for the first match of each ambiguous pronoun)
            for p in ambiguous_pronouns:
                resolved_command = re.sub(p, lambda m: target, resolved_command, count=1, flags=re.I)

    if resolved_command != command:
        logger.info('Context resolved: "%s" -> "%s"', command, resolved_command)
        
    return resolved_command
