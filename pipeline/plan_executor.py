# pipeline/plan_executor.py
# ──────────────────────────────────────────────────────────────────────
# Plan Executor — Runs multi-step LLM tool plans safely (v2)
# ──────────────────────────────────────────────────────────────────────

import inspect
import logging
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
        result_val = str(tool_fn(**filtered_args))
        session_update('last_result', result_val)
        return result_val
    except TypeError as e:
        logger.warning('Tool argument mismatch for %s: %s', tool_name, e)
        return f'Sorry, I need a little more info for that. Could you be more specific?'
    except Exception as e:
        logger.error('Tool execution failed for %s: %s', tool_name, e, exc_info=True)
        return f'Could not complete that: {str(e)}'


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
                    # Find the first string parameter that isn't provided
                    for param_name, param in sig.parameters.items():
                        if param_name not in args:
                            args[param_name] = previous_result
                            break
                except ValueError:
                    pass

        result = invoke_tool(tool_name, args, tool_map)
        previous_result = result
        results.append(result)

    return results[-1] if results else 'I could not complete that plan.'
