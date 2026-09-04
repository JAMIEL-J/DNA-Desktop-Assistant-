# pipeline/plan_executor.py
# ──────────────────────────────────────────────────────────────────────
# Plan Executor — Runs multi-step LLM tool plans safely (v2)
# ──────────────────────────────────────────────────────────────────────

import inspect
import logging
import time
from typing import Any

from core.safety import (
    is_tool_blocked,
    is_tool_dangerous,
    is_command_dangerous,
    get_danger_warning,
)
from core.session import update as session_update, get as session_get

logger = logging.getLogger('dna.executor')


def validate_tool_safety(tool_name: str, args: dict[str, Any]) -> str | None:
    """Check if a tool call from the LLM is safe to execute.
    Returns None if safe, or a warning/block message if not.
    """
    if is_tool_blocked(tool_name):
        logger.critical('BLOCKED: tried to invoke blocked tool: %s', tool_name)
        return (
            f'I cannot execute "{tool_name}" — it is blocked for safety reasons. '
            'This action could damage your system.'
        )

    if is_tool_dangerous(tool_name):
        logger.warning('DANGEROUS: invoked dangerous tool: %s', tool_name)
        return get_danger_warning(tool_name)

    for key, value in (args or {}).items():
        if isinstance(value, str) and is_command_dangerous(value):
            logger.critical(
                'BLOCKED: Dangerous command in arg %s of tool %s: %s',
                key, tool_name, value[:100]
            )
            return (
                'I detected a potentially dangerous command and blocked it '
                'for your safety. Please try a different approach.'
            )

    return None


def invoke_tool(tool_name: str, args: dict[str, Any], tool_map: dict[str, Any]) -> str:
    """Execute one tool safely with filtered keyword arguments."""
    # ── Safety gate ──
    safety_msg = validate_tool_safety(tool_name, args)
    if safety_msg:
        return safety_msg

    tool_fn = tool_map.get(tool_name)
    if not tool_fn:
        return f'I could not find the tool named {tool_name}.'

    try:
        signature = inspect.signature(tool_fn)
        filtered_args = {
            key: value
            for key, value in (args or {}).items()
            if key in signature.parameters
        }
        
        # Update active skill
        from core.skill_registry import get_skill_for_tool
        skill = get_skill_for_tool(tool_name)
        if skill:
            session_update('active_skill', skill)
            
        result_val = str(tool_fn(**filtered_args))
        session_update('last_result', result_val)
        return result_val
    except TypeError as e:
        logger.warning('Tool argument mismatch for %s: %s', tool_name, e)
        return f'Sorry, I need a little more info for that. Could you be more specific?'
    except Exception as e:
        logger.error('Tool execution failed for %s: %s', tool_name, e, exc_info=True)
        return 'Sorry boss, I encountered an issue while trying to complete that task.'


def execute_plan(plan: list[dict[str, Any]], tool_map: dict[str, Any]) -> str:
    """Execute a JSON plan sequentially and return a spoken summary."""
    if not plan:
        return 'I could not build a valid plan for that.'

    # ── Pre-validate entire plan before executing anything ──
    for step in plan:
        tool_name = str(step.get('tool', 'unknown')).strip()
        args = step.get('args') or {}
        safety_msg = validate_tool_safety(tool_name, args)
        if safety_msg:
            return safety_msg

    previous_result = ''
    results: list[str] = []

    for step in plan:
        tool_name = str(step.get('tool', 'unknown')).strip()
        args = step.get('args') or {}
        use_prev = step.get('use_prev_result', False)

        if use_prev and previous_result:
            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    sig = inspect.signature(tool_fn)
                    # Prefer text-like params (query/question/text/input/prompt);
                    # never inject prior output into path/file params which
                    # previously corrupted run_analysis(path, question) calls.
                    preferred = ('question', 'query', 'text', 'input', 'prompt',
                                 'message', 'content', 'data', 'result',
                                 'previous_result')
                    injected = False
                    for name in preferred:
                        if name in sig.parameters and name not in args:
                            args[name] = previous_result
                            injected = True
                            break
                    if not injected:
                        for param_name in sig.parameters:
                            if param_name not in args and 'path' not in param_name and 'file' not in param_name:
                                args[param_name] = previous_result
                                break
                except ValueError:
                    pass

        result = invoke_tool(tool_name, args, tool_map)
        previous_result = result
        results.append(result)

    final = results[-1] if results else 'I could not complete that plan.'
    _ledger_run(plan, results)
    return final


# ════════════════════════════════════════════════════════════════════
# Pending Plan (Plan Mode) — propose first, execute on exact approval
# ════════════════════════════════════════════════════════════════════

_pending_plan = {'plan': None, 'timestamp': 0.0}
PLAN_TIMEOUT_SECS = 120.0
PLAN_CONFIRM_EXACT = {'proceed', 'go ahead', 'yes', 'confirm plan', 'run it', 'do it'}
PLAN_CANCEL_EXACT = {'cancel', 'never mind', 'drop it', 'no'}


def _short_args(args: dict) -> str:
    try:
        items = [f'{k}={str(v)[:40]}' for k, v in list((args or {}).items())[:3]]
        return ', '.join(items)
    except Exception:
        return ''


def summarize_plan(plan: list[dict[str, Any]]) -> str:
    """Human-readable numbered plan for the approval prompt."""
    lines = []
    for i, step in enumerate(plan or [], 1):
        tool = str(step.get('tool', 'unknown')).strip()
        arg_str = _short_args(step.get('args') or {})
        lines.append(f'{i}. {tool}' + (f' ({arg_str})' if arg_str else ''))
    return '\n'.join(lines)


def store_pending_plan(plan: list[dict[str, Any]]) -> str:
    """Hold a multi-step plan for approval. Returns the spoken proposal."""
    _pending_plan['plan'] = [dict(s) for s in plan]
    _pending_plan['timestamp'] = time.time()
    logger.info('Pending plan stored (%d steps).', len(plan))
    return ('Here is my plan, boss:\n' + summarize_plan(plan) +
            '\nSay proceed to run it, or cancel to drop it.')


def has_pending_plan() -> bool:
    """True while an unexpired plan awaits approval."""
    if not _pending_plan['plan']:
        return False
    if time.time() - _pending_plan['timestamp'] > PLAN_TIMEOUT_SECS:
        _pending_plan['plan'] = None
        _pending_plan['timestamp'] = 0.0
        return False
    return True


def check_pending_plan(command: str, tool_map: dict[str, Any]) -> str | None:
    """Consume exact approve/cancel replies for a pending plan.

    Returns the execution result / cancellation message, or None when the
    command is unrelated (plan is kept until timeout).
    """
    if not has_pending_plan():
        return None
    cleaned = (command or '').strip().lower()
    if cleaned in PLAN_CONFIRM_EXACT:
        plan = _pending_plan['plan'] or []
        _pending_plan['plan'] = None
        _pending_plan['timestamp'] = 0.0
        logger.info('User approved pending plan (%d steps).', len(plan))
        return execute_plan(plan, tool_map)
    if cleaned in PLAN_CANCEL_EXACT:
        _pending_plan['plan'] = None
        _pending_plan['timestamp'] = 0.0
        logger.info('User cancelled pending plan.')
        return 'No problem, boss. I dropped that plan.'
    return None


def _ledger_run(plan: list[dict[str, Any]], results: list[str]) -> None:
    """Append a run-ledger entry when a project is active (best-effort)."""
    try:
        active = session_get('active_project')
        if not active:
            return
        from core.projects import append_run
        lines = []
        for i, (step, res) in enumerate(zip(plan, results), 1):
            tool = str(step.get('tool', 'unknown'))
            lines.append(f'Step {i}: {tool}\nResult: {str(res)[:500]}')
        title = 'Plan: ' + ', '.join(str(s.get('tool', '?')) for s in plan[:4])
        append_run(active, title, '\n\n'.join(lines))
    except Exception as e:
        logger.debug('Run ledger skipped: %s', e)
