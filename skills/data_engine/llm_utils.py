# skills/data_engine/llm_utils.py
import json
import logging
import importlib
import re
import requests

from config import OLLAMA_MODEL, OLLAMA_URL, OLLAMA_TIMEOUT, GOOGLE_API_KEY, CLOUD_LLM_MODEL

logger = logging.getLogger('dna.data_engine.llm_utils')


def _extract_code_from_response(raw: str) -> str:
    """Strip LLM reasoning/thinking text and extract only executable code.

    Gemini (and some Ollama models) may prefix the actual code with
    chain-of-thought reasoning (bullet points, analysis, etc.).
    This function strips all of that and returns only the code.
    """
    if not raw:
        return ''

    text = raw.strip()

    # 1. Strip markdown fences (```sql ... ``` or ```python ... ```)
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove opening fence line
        lines = lines[1:]
        # Remove closing fence if present
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()

    # 2. If there are still markdown fences embedded in the middle, extract them
    fence_match = re.search(r'```(?:sql|python|py)?\s*\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # 3. Strip reasoning/thinking lines.
    #    Reasoning lines typically start with: *, -, bullet indentation, or
    #    look like natural-language sentences (contain ":" followed by explanation).
    #    Actual code lines start with SQL keywords or Python variable assignments.
    lines = text.split('\n')
    code_lines = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (preserve them only if we're already in code)
        if not stripped:
            if in_code_block:
                code_lines.append(line)
            continue

        # Reasoning indicators: lines starting with *, -, or indented bullets
        if stripped.startswith('*') or stripped.startswith('- '):
            in_code_block = False
            continue

        # Backtick-wrapped inline code at end of reasoning (e.g., `SELECT ...`)
        backtick_match = re.match(r'^`([^`]+)`$', stripped)
        if backtick_match:
            # This is likely the actual code wrapped in backticks
            code_lines = [backtick_match.group(1)]
            in_code_block = True
            continue

        # If line looks like code (starts with SQL keyword, Python assignment,
        # or function call), keep it
        is_code = (
            # SQL patterns
            re.match(r'^(SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|DROP|ALTER|EXPLAIN)\b', stripped, re.IGNORECASE)
            or re.match(r'^(FROM|WHERE|GROUP|ORDER|HAVING|LIMIT|JOIN|UNION|SET)\b', stripped, re.IGNORECASE)
            # Python patterns
            or re.match(r'^[a-zA-Z_]\w*\s*=', stripped)  # variable assignment
            or re.match(r'^(if|for|while|def|class|try|except|return|elif|else:)', stripped)
            or re.match(r'^(result|df|avg|count|num|total|max|min|sum|len)\b', stripped)
            or re.match(r'^[a-zA-Z_]\w*\(', stripped)  # function call
            or re.match(r'^[a-zA-Z_]\w*\[', stripped)  # indexing
        )

        if is_code:
            in_code_block = True
            code_lines.append(line)
        elif in_code_block:
            # If we're in a code block and line doesn't look like reasoning, keep it
            # (could be a continuation line, string, etc.)
            if not (stripped.startswith('*') or stripped.startswith('- ')):
                code_lines.append(line)
        # else: skip reasoning line

    # Deduplicate consecutive identical lines (LLM sometimes echoes the same
    # code both in backtick-wrapped and bare form)
    deduped = []
    for line in code_lines:
        if not deduped or line.strip() != deduped[-1].strip():
            deduped.append(line)
    code_lines = deduped

    result = '\n'.join(code_lines).strip()

    # 4. If extraction produced nothing, fall back to the last non-empty line
    #    (the LLM often puts the final answer at the end)
    if not result:
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('*') and not stripped.startswith('-'):
                # Remove surrounding backticks if present
                result = stripped.strip('`').strip()
                break

    return result


def _call_llm_for_code(prompt: str) -> str:
    """Call Google API or Ollama to generate raw SQL or Python code."""
    try:
        # Cloud path
        if GOOGLE_API_KEY:
            genai = importlib.import_module('google.genai')

            client = genai.Client(api_key=GOOGLE_API_KEY)
            response = client.models.generate_content(
                model=CLOUD_LLM_MODEL,
                contents=prompt,
                config={'temperature': 0.0},
            )
            content = (getattr(response, 'text', '') or '').strip()
        else:
            # Local Ollama path
            response = requests.post(
                OLLAMA_URL,
                json={
                    'model': OLLAMA_MODEL,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'stream': False,
                    'options': {'temperature': 0.0},
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            content = str(response.json().get('message', {}).get('content', '')).strip()

        # Extract only the executable code, stripping any reasoning text
        return _extract_code_from_response(content)
    except Exception as e:
        logger.error('NL2Code generation failed: %s', e)
        return ''


def call_llm_for_json(prompt: str) -> dict:
    """Call LLM and parse response as JSON (for analyst module)."""
    try:
        if GOOGLE_API_KEY:
            genai = importlib.import_module('google.genai')
            client = genai.Client(api_key=GOOGLE_API_KEY)
            response = client.models.generate_content(
                model=CLOUD_LLM_MODEL,
                contents=prompt,
                config={'temperature': 0.0},
            )
            raw = (getattr(response, 'text', '') or '').strip()
        else:
            response = requests.post(
                OLLAMA_URL,
                json={
                    'model': OLLAMA_MODEL,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'stream': False,
                    'options': {'temperature': 0.0},
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            raw = str(response.json().get('message', {}).get('content', '')).strip()

        if not raw:
            return {}

        # Clean JSON markdown blocks
        cleaned = raw
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned = '\n'.join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed text
            match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            return {}
    except Exception as e:
        logger.error('call_llm_for_json failed: %s', e)
        return {}

