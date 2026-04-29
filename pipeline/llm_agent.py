# pipeline/llm_agent.py
# ──────────────────────────────────────────────────────────────────────
# LLM Agent — Routes complex commands through Ollama
# v2 — Safety-hardened: blocks dangerous tools, sanitises LLM output
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import inspect
import importlib
import json
import logging
import re
from typing import Any, cast

# 2. third-party
import requests

# 3. internal
from config import (
    OLLAMA_CTX_NORMAL,
    OLLAMA_CTX_THINKING,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
    GOOGLE_API_KEY,
    CLOUD_LLM_MODEL,
)
from core.safety import (
    is_tool_blocked,
    is_tool_dangerous,
    is_command_dangerous,
    get_danger_warning,
)
from pipeline.plan_executor import execute_plan, invoke_tool
from pipeline.memory import get_preferences
from core.personality import get_system_prompt, humanize_response

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
    """Remove markdown formatting and extract the JSON block if preceded by text."""
    # First, try to extract anything between { and } or [ and ] 
    # to handle "thinking" text injected before the JSON.
    text = (raw or '').strip()
    # Match the outermost {} or [] block
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        text = match.group(1)

    text = text.replace('```json', '')
    text = text.replace('```', '')
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
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from LLM. Raw text: %r | Error: %s", raw, e)
    return {'tool': 'unknown', 'args': {}}


def _build_system_prompt(tool_names: list[str]) -> str:
    """Build strict JSON prompt for single-tool or small plan outputs.

    The safety layer adds explicit instructions to NEVER attempt
    file deletion, system modification, or format operations.
    """
    tools = ', '.join(sorted(tool_names))
    persona = get_system_prompt()
    base_prompt = (
        f'{persona}\n'
        'PERSONALITY EXAMPLES:\n'
        '- Instead of "Acknowledged, opening application" say "Immediately, sir. I am opening that now."\n'
        '- Instead of "I require clarification" say "Forgive me, sir, but I require more details to proceed."\n'
        '- Instead of "Task completed successfully" say "It is done, sir."\n'
        '\n'
        'RESPONSE FORMAT: Reply with JSON only and no markdown. '
        'Valid outputs: '
        '{"tool":"tool_name","args":{...}} or '
        '{"plan":[{"tool":"tool_name","args":{},"use_prev_result":false}]}. '
        'Use only available tools. If unclear, return '
        '{"tool":"clarify","args":{"question":"Your friendly clarification question."}}. '
        'If nothing fits, return {"tool":"unknown","args":{}}. '
        '\n\n'
        '⚠️ SAFETY RULES (NEVER violate these):\n'
        '1. NEVER attempt to delete, format, or modify system files.\n'
        '2. NEVER use shutdown_computer or restart_computer unless the user explicitly asks.\n'
        '3. NEVER construct shell commands, paths, or scripts.\n'
        '4. If unsure about the user intent, choose "clarify" instead of guessing.\n'
        '5. Only use tools from the list below.\n'
        '\n'
    )

    prefs = get_preferences()
    if prefs:
        prefs_str = "\n".join([f"- {k}: {v}" for k, v in prefs.items()])
        base_prompt += f'USER PREFERENCES:\n{prefs_str}\n\n'

    base_prompt += f'Available tools: {tools}.'
    return base_prompt


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
            'keep_alive': OLLAMA_KEEP_ALIVE,
            'options': {
                'num_ctx': OLLAMA_CTX_THINKING if thinking else OLLAMA_CTX_NORMAL,
                'temperature': OLLAMA_TEMPERATURE,
                'num_parallel': 1,
                'use_mmap': True,
                'use_mlock': False,
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

def _call_google(command: str, tool_names: list[str]) -> dict[str, Any]:
    """Call Google's Gemini API."""
    genai = importlib.import_module('google.genai')

    system_instruction = _build_system_prompt(tool_names)
    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=CLOUD_LLM_MODEL,
        contents=command,
        config={
            'system_instruction': system_instruction,
            'temperature': OLLAMA_TEMPERATURE,
        },
    )
    return _parse_llm_json(getattr(response, 'text', '') or '')

def _call_llm(command: str, tool_names: list[str]) -> dict[str, Any]:
    """Route LLM call to Google if key is present, otherwise Ollama."""
    import sys
    
    # Fast path to the correct LLM
    if GOOGLE_API_KEY:
        try:
            decision = _call_google(command, tool_names)
        except Exception as e:
            logger.error("Google API failed: %s. Falling back to Ollama.", e)
            decision = _call_ollama(command, tool_names)
    else:
        decision = _call_ollama(command, tool_names)
        
    # ── Validate the tool name against available tools ──
    plan = decision.get('plan')
    if plan and isinstance(plan, list):
        for step in plan:
            step_tool = str(step.get('tool', '')).strip()
            if step_tool and step_tool not in tool_names and step_tool not in ('clarify', 'unknown'):
                logger.warning('LLM hallucinated tool "%s" — not in available tools', step_tool)
                return {'tool': 'unknown', 'args': {}}
    else:
        dec_tool = str(decision.get('tool', '')).strip()
        if dec_tool and dec_tool not in tool_names and dec_tool not in ('clarify', 'unknown'):
            logger.warning('LLM hallucinated tool "%s" — not in available tools', dec_tool)
            return {'tool': 'unknown', 'args': {}}

    return decision




def handle_complex_command(command: str, tool_map: dict[str, Any]) -> str:
    """Route non-regex commands through LLM and execute chosen tool(s)."""
    try:
        tool_names = list(tool_map.keys())
        decision = _call_llm(command, tool_names)

        if 'plan' in decision and isinstance(decision['plan'], list):
            return humanize_response(execute_plan(decision['plan'], tool_map))

        tool_name = str(decision.get('tool', 'unknown')).strip()
        raw_args = decision.get('args')
        args: dict[str, Any] = cast(dict[str, Any], raw_args) if isinstance(raw_args, dict) else {}

        if tool_name == 'clarify':
            question = str(args.get('question', 'Could you clarify what you want me to do?')).strip()
            return humanize_response(question or 'Could you clarify what you want me to do?')
        if tool_name == 'unknown':
            return humanize_response("Hmm, I'm not quite sure what you need. Could you say that differently?")

        return humanize_response(invoke_tool(tool_name, args, tool_map))
    except requests.exceptions.ConnectionError:
        return humanize_response("Sorry, I can't reach my brain right now. Make sure the AI service is running.")
    except requests.exceptions.Timeout:
        return humanize_response('Sorry, that took too long. Could you try again?')
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 'unknown'
        text = e.response.text if e.response is not None else 'No response content'
        logger.error('Ollama HTTP error %s: %s', status, text)
        return humanize_response('Sorry, something went wrong on my end. Let me know if you want to try again.')
    except Exception as e:
        logger.error('Complex command handling failed: %s', e, exc_info=True)
        return humanize_response('Sorry, I ran into an issue with that. Could you try again?')
