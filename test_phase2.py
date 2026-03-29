"""Phase 2 Test: Intent Router (no microphone needed)."""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

from pipeline.intent_router import route

# Test commands to verify regex routing
TEST_COMMANDS = [
    ('set volume to 50', 'set_volume'),
    ('volume 75', 'set_volume'),
    ('volume up', 'volume_up'),
    ('volume down', 'volume_down'),
    ("what's the volume", 'get_volume'),
    ('mute', 'mute'),
    ('unmute', 'unmute'),
    ('play', 'media_play_pause'),
    ('pause', 'media_play_pause'),
    ('next track', 'media_next'),
    ('skip', 'media_next'),
    ('previous song', 'media_previous'),
    ('open notepad', 'open_app'),
    ('open chrome', 'open_app'),
    ('close notepad', 'close_app'),
    ('take a screenshot', 'take_screenshot'),
    ("what's the time", 'get_time'),
    ('what is the date', 'get_date'),
    ('lock the screen', 'lock_screen'),
    ('tell me the time', 'get_time'),
    ('launch calculator', 'open_app'),
    # This should NOT match (returns None)
    ('what is your name', None),
    ('tell me a joke', None),
]

if __name__ == '__main__':
    print('=' * 60)
    print('  DNA Phase 2 Test: Intent Router')
    print('=' * 60)
    print()

    passed = 0
    failed = 0

    for command, expected_tool in TEST_COMMANDS:
        result = route(command, allow_llm=False)

        if expected_tool is None:
            # Expect no match
            if result is None:
                status = '✓'
                passed += 1
            else:
                status = '✗'
                failed += 1
        else:
            # Expect a match (non-None result)
            if result is not None:
                status = '✓'
                passed += 1
            else:
                status = '✗'
                failed += 1

        result_preview = (result[:50] + '...') if result and len(result) > 50 else result
        print(f'  {status} "{command}"')
        print(f'    → {result_preview}')
        print()

    print('=' * 60)
    print(f'  Results: {passed} passed, {failed} failed out of {len(TEST_COMMANDS)}')
    print('=' * 60)
