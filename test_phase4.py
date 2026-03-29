"""Phase 4 Test: LLM fallback routing and Ollama integration behavior.

Run from project root:
    python test_phase4.py

This suite validates:
1. Regex-miss behavior with and without LLM fallback.
2. Thinking mode routing logic.
3. Fenced JSON cleanup and parse fallback.
4. Graceful handling when Ollama is unreachable.
5. Optional live smoke test when Ollama is running.
"""

# 1. stdlib
import json
import logging
import sys
import unittest
from unittest.mock import patch

# 2. third-party
import requests

# 3. internal
from pipeline.intent_router import route
from pipeline.llm_agent import (
    _clean_json_text,
    _parse_llm_json,
    handle_complex_command,
    needs_thinking,
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('dna.test.phase4')


class TestPhase4Routing(unittest.TestCase):
    """Deterministic tests for Phase 4 fallback behavior."""

    def test_route_without_llm_returns_none_for_unmatched(self):
        result = route('tell me a joke', allow_llm=False)
        self.assertIsNone(result)

    def test_route_with_llm_calls_fallback(self):
        with patch('pipeline.intent_router.handle_complex_command', return_value='LLM response') as mocked:
            result = route('tell me a joke', allow_llm=True)
            self.assertEqual(result, 'LLM response')
            mocked.assert_called_once()

    def test_needs_thinking(self):
        self.assertTrue(needs_thinking('compare these two files'))
        self.assertTrue(needs_thinking('explain this output'))
        self.assertFalse(needs_thinking('open notepad'))

    def test_clean_json_text_for_fenced_json(self):
        raw = '```json\n{"tool":"get_time","args":{}}\n```'
        cleaned = _clean_json_text(raw)
        self.assertEqual(cleaned, '{"tool":"get_time","args":{}}')

    def test_parse_json_fallback_for_invalid_output(self):
        parsed = _parse_llm_json('not-json-output')
        self.assertEqual(parsed, {'tool': 'unknown', 'args': {}})

    def test_handle_complex_command_connection_error(self):
        with patch('pipeline.llm_agent._call_ollama', side_effect=requests.exceptions.ConnectionError):
            result = handle_complex_command('tell me a joke', {'get_time': lambda: 'The time is now.'})
            self.assertIn('could not reach ollama', result.lower())

    def test_handle_complex_command_clarify_response(self):
        with patch(
            'pipeline.llm_agent._call_ollama',
            return_value={'tool': 'clarify', 'args': {'question': 'Which file should I open?'}},
        ):
            result = handle_complex_command('open the report', {'open_app': lambda app_name='': 'Opening app.'})
            self.assertEqual(result, 'Which file should I open?')


def run_optional_live_smoke() -> bool:
    """Run an optional live fallback check when Ollama is online.

    Returns:
        True when a live check was executed successfully, else False.
    """
    try:
        tags = requests.get('http://localhost:11434/api/tags', timeout=5)
        tags.raise_for_status()
    except Exception:
        print('\n[Live Smoke] Skipped: Ollama is not reachable on localhost:11434.')
        return False

    response = route('tell me a short joke', allow_llm=True)
    print('\n[Live Smoke] Response:', response)
    return bool(response and isinstance(response, str))


if __name__ == '__main__':
    print('=' * 60)
    print('  DNA Phase 4 Test: LLM Fallback + Ollama Checks')
    print('=' * 60)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPhase4Routing)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    live_ok = run_optional_live_smoke()

    print('\n' + '=' * 60)
    print(f'  Unit Tests: {result.testsRun - len(result.failures) - len(result.errors)} passed, '
          f'{len(result.failures)} failed, {len(result.errors)} errors')
    print(f'  Live Smoke: {"PASS" if live_ok else "SKIPPED"}')
    print('=' * 60)

    # Exit non-zero only on deterministic unit test failures/errors.
    if not result.wasSuccessful():
        sys.exit(1)
