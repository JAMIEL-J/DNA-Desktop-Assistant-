# 1. stdlib
import inspect
import json
import logging
import re
from typing import Any

# 2. third-party
import requests

# 3. internal
from config import (
    OLLAMA_CTX_NORMAL,
    OLLAMA_CTX_THINKING,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)

logger = logging.getLogger('dna.llm')


THINKING_TASKS = [
    'summarise webpage',
    'summarize webpage',
    'explain',
    'compare',
    'analyse',
    'analyze',
]


def needs_thinking(command: str) -> bool:
    """Return True when a command benefits from deeper reasoning."""
    lowered = (command or '').lower()
    return any(task in lowered for task in THINKING_TASKS)


def _clean_json_text(raw: str) -> str:
    """Strip markdown code fences and surrounding whitespace."""
    text = (raw or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
        text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _extract_message_content(payload: dict[str, Any]) -> str:
    """Extract message content from Ollama response variants."""
    if isinstance(payload.get('message'), dict):
        return str(payload['message'].get('content', '')).strip()
    if isinstance(payload.get('response'), str):
        return payload['response'].strip()
    return ''


def _parse_llm_json(raw: str) -> dict[str, Any]:
    """Parse LLM JSON output with a safe fallback."""
    cleaned = _clean_json_text(raw)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {'tool': 'unknown', 'args': {}}


def _build_system_prompt(tool_names: list[str]) -> str:
    """Build strict JSON prompt for single-tool or small plan outputs."""
    tools = ', '.join(sorted(tool_names))
    return (
        'You are DNA, an offline Windows 11 desktop assistant. '
        'Reply with JSON only and no markdown. '\
        'Valid outputs: '\
        '{"tool":"tool_name","args":{...}} or '\
        '{"plan":[{"tool":"tool_name","args":{},"use_prev_result":false}]}. '\
        'Use only available tools. If unclear, return '\
        '{"tool":"clarify","args":{"question":"Your short clarification question."}}. '\
        'If nothing fits, return {"tool":"unknown","args":{}}. '\
        f'Available tools: {tools}.'
    )


def _call_ollama(command: str, tool_names: list[str]) -> dict[str, Any]:
    """Call Ollama and return the parsed JSON decision."""
    thinking = needs_thinking(command)
    messages = [
        {'role': 'system', 'content': _build_system_prompt(tool_names)},
        {'role': 'user', 'content': command},
    ]

    response = requests.post(
        OLLAMA_URL,
        json={
            'model': OLLAMA_MODEL,
            'messages': messages,
            'stream': False,
            'think': thinking,
            'options': {
                'num_ctx': OLLAMA_CTX_THINKING if thinking else OLLAMA_CTX_NORMAL,
                'temperature': OLLAMA_TEMPERATURE,
                'num_parallel': 1,
            },
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    raw = _extract_message_content(payload)
    if not raw:
        return {'tool': 'unknown', 'args': {}}
    return _parse_llm_json(raw)


def _invoke_tool(tool_name: str, args: dict[str, Any], tool_map: dict[str, Any]) -> str:
    """Execute one tool safely with filtered keyword arguments."""
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
        return str(tool_fn(**filtered_args))
    except TypeError as e:
        logger.warning('Tool argument mismatch for %s: %s', tool_name, e)
        return f'I need a bit more detail to run {tool_name}. Please try that again with specifics.'
    except Exception as e:
        logger.error('Tool execution failed for %s: %s', tool_name, e, exc_info=True)
        return f'Could not complete that: {str(e)}'


def _execute_plan(plan: list[dict[str, Any]], tool_map: dict[str, Any]) -> str:
    """Execute a small JSON plan sequentially and return a spoken summary."""
    if not plan:
        return 'I could not build a valid plan for that.'

    previous_result = ''
    results: list[str] = []

    for step in plan:
        tool_name = str(step.get('tool', 'unknown')).strip()
        args = step.get('args') or {}
        if step.get('use_prev_result') and previous_result:
            args = {**args, 'path': previous_result}

        result = _invoke_tool(tool_name, args, tool_map)
        previous_result = result
        results.append(result)

    return results[-1] if results else 'I could not complete that plan.'


def handle_complex_command(command: str, tool_map: dict[str, Any]) -> str:
    """Route non-regex commands through Ollama and execute chosen tool(s)."""
    try:
        tool_names = list(tool_map.keys())
        decision = _call_ollama(command, tool_names)

        if 'plan' in decision and isinstance(decision['plan'], list):
            return _execute_plan(decision['plan'], tool_map)

        tool_name = str(decision.get('tool', 'unknown')).strip()
        args = decision.get('args') if isinstance(decision.get('args'), dict) else {}

        if tool_name == 'clarify':
            question = str(args.get('question', 'Could you clarify what you want me to do?')).strip()
            return question or 'Could you clarify what you want me to do?'
        if tool_name == 'unknown':
            return 'I am not sure which action fits that request yet. Please be more specific.'

        return _invoke_tool(tool_name, args, tool_map)
    except requests.exceptions.ConnectionError:
        return 'I could not reach Ollama. Please make sure Ollama is running.'
    except requests.exceptions.Timeout:
        return 'The language model took too long to respond. Please try again.'
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 'unknown'
        return f'Ollama returned an HTTP {status} error. Please check the model and service.'
    except Exception as e:
        logger.error('Complex command handling failed: %s', e, exc_info=True)
        return f'Could not complete that: {str(e)}'
