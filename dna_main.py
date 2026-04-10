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
    from pipeline.memory import init_db, log_command
    from core.session import update as session_update, get as session_get
    from core.skill_registry import discover_skills
    from core.proactive import start_proactive_monitors
    from ui.tray import start_tray
    from core.personality import get_wake_greeting

    logger.info('=' * 50)
    logger.info('  DNA Voice Assistant Starting...')
    logger.info('=' * 50)

    # Confirm TTS is working with a startup greeting
    speak('DNA is online. Say hey Jarvis to wake me up.')
    init_db()
    discover_skills()
    start_proactive_monitors()
    start_tray()

    # ── Morning job check (silent if nothing new) ──
    try:
        from config import JOBS_ON_STARTUP
        if JOBS_ON_STARTUP:
            from skills.jobs_skill import morning_job_check
            job_update = morning_job_check()
            if job_update:
                speak(job_update)
    except Exception as e:
        logger.debug('Morning job check skipped: %s', e)

    while session_get('is_running', True):
        try:
            # Step 1: Wait for wake word
            session_update('is_listening', False)
            detected = wait_for_wake_word()

            if not session_get('is_running', True):
                break

            if not detected:
                continue

            # Step 2: Play acknowledgment and record command
            session_update('is_listening', True)
            speak(get_wake_greeting())

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
            session_update('last_command', text)

            # Step 4: Route to tool
            result = route(text)

            if not result or not result.strip():
                error_msg = 'I could not process that command. Please try again.'
                log_command(text, error_msg, 'error')
                speak(error_msg)
                continue

            # Step 5: Speak the result
            logger.info('Result: "%s"', result)
            status = 'error' if 'could not' in result.lower() else 'success'
            log_command(text, result, status)
            speak(result)

        except KeyboardInterrupt:
            logger.info('Shutting down DNA via KeyboardInterrupt...')
            session_update('is_running', False)
            speak('Goodbye.')
            break
        except Exception as e:
            logger.error('Main loop error: %s', e, exc_info=True)
            cmd_text = locals().get('text', 'unknown')
            log_command(cmd_text, str(e), 'error')
            speak('Something went wrong. I am still listening.')


if __name__ == '__main__':
    main()
