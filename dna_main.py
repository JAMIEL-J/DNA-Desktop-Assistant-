# 1. stdlib
import logging
import sys
from pathlib import Path

# 2. internal
from config import BASE_DIR, LOG_PATH

# --- Logging setup (before any other imports) ---
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_PATH), encoding='utf-8'),
    ],
)
logger = logging.getLogger('dna.main')


def main():
    """DNA main loop: Wake → Listen → Transcribe → Route → Speak."""
    from pipeline.wake_word import wait_for_wake_word, listen_and_record
    from pipeline.stt import transcribe
    from pipeline.tts import speak
    from pipeline.intent_router import route
    from core.session import update

    logger.info('=' * 50)
    logger.info('  DNA Voice Assistant Starting...')
    logger.info('=' * 50)

    # Confirm TTS is working with a startup greeting
    speak('DNA is online. Say hey Jarvis to wake me up.')
    logger.info('Startup complete. Entering main loop.')

    while True:
        try:
            # Step 1: Wait for wake word
            update('is_listening', False)
            detected = wait_for_wake_word()

            if not detected:
                continue

            # Step 2: Play acknowledgment and record command
            update('is_listening', True)
            speak('Yes?')

            audio = listen_and_record()
            if audio is None or len(audio) == 0:
                speak('I did not catch that.')
                continue

            # Step 3: Transcribe
            text = transcribe(audio)
            if not text:
                speak('I did not understand that.')
                continue

            logger.info('Command: "%s"', text)
            update('last_command', text)

            # Step 4: Route to tool
            result = route(text)

            if not result or not result.strip():
                speak('I could not process that command. Please try again.')
                continue

            # Step 5: Speak the result
            logger.info('Result: "%s"', result)
            speak(result)

        except KeyboardInterrupt:
            logger.info('Shutting down DNA...')
            speak('Goodbye.')
            break
        except Exception as e:
            logger.error('Main loop error: %s', e, exc_info=True)
            speak('Something went wrong. I am still listening.')


if __name__ == '__main__':
    main()
