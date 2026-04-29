# 1. stdlib
import logging
import random
import re
import sys
import threading
import time
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


def _is_prefix_only_command(text: str) -> bool:
    """Return True when transcript is only an assistant call-prefix."""
    if not text:
        return False
    cleaned = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in text.lower())
    cleaned = ' '.join(cleaned.split())
    return cleaned in {'jarvis', 'hey jarvis', 'dna', 'hey dna', 'assistant'}


def _normalize_transcript(text: str) -> str:
    """Normalize noisy STT output into a cleaner command string."""
    if not text:
        return ''

    cleaned = text.lower().strip()
    
    # 1. Protect completely known phrases before word-splitting
    cleaned = cleaned.replace("whats app", "whatsapp")
    cleaned = cleaned.replace("what's app", "whatsapp")
    
    # 2. Apply word conversions
    cleaned = re.sub(r"\bwhat's\b", 'what is', cleaned)
    cleaned = re.sub(r"\bwhats\b", 'what is', cleaned)
    cleaned = re.sub(r"\bhow's\b", 'how is', cleaned)
    cleaned = re.sub(r"\bhows\b", 'how is', cleaned)
    cleaned = cleaned.replace('_', ' ')
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _looks_incomplete_command(text: str) -> bool:
    """Return True when a transcript looks truncated and needs continuation capture."""
    cleaned = _normalize_transcript(text)
    if not cleaned:
        return True

    tokens = cleaned.split()
    if not tokens:
        return True

    if cleaned in {
        'what', 'what is', 'what is the',
        'how', 'how is', 'how is the',
        'tell me', 'show me',
        'open', 'start', 'launch',
        'can you', 'could you', 'please'
    }:
        return True

    # Truncated app launches or questions
    if cleaned.startswith(('open ', 'start ', 'launch ')) and cleaned.endswith(' the'):
        return True

    if cleaned.startswith(('what is ', 'how is ')) and len(tokens) <= 2:
        return True

    # Commands ending with function words are often truncated chunks.
    if tokens[-1] in {
        'is', 'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on',
        'at', 'with', 'my', 'your', 'this', 'that', 'and'
    } and len(tokens) <= 6:
        return True

    # Very short generic questions frequently indicate partial capture.
    if len(tokens) <= 4 and tokens[-1] in {'guidance'}:
        return True

    return False


def _assistant_loop() -> None:
    """Assistant engine loop with session mode and voice I/O."""
    from pipeline.wake_word import wait_for_wake_word
    from pipeline.stt import record_audio, transcribe
    from pipeline.tts import speak, is_speaking
    from pipeline.intent_router import route, is_dismiss_command
    from pipeline.memory import log_command, get_scored_startup_suggestion
    from core.session import update as session_update, get as session_get
    from pipeline.session_manager import DNAState, get_state, set_state
    from core.personality import get_wake_greeting
    from config import (
        AUTO_SLEEP_TIMEOUT,
        ACTIVE_LISTEN_SECONDS,
        ACTIVE_RETRY_SECONDS,
        SHORT_TRANSCRIPT_MIN,
        WAKE_RESPONSES,
        TIMEOUT_RESPONSES,
        DISMISS_RESPONSES,
        SUGGESTIONS_ENABLED,
        STARTUP_SUGGESTIONS_ENABLED,
        STARTUP_SUGGESTION_MIN_COUNT,
        STARTUP_SUGGESTION_MIN_CONFIDENCE,
        STARTUP_SUGGESTION_COOLDOWN_MINUTES,
    )

    # Start active immediately so the window does not require manual wake.
    set_state(DNAState.ACTIVE)
    session_update('assistant_state', 'active')
    session_update('is_listening', True)

    # Startup should keep the loyal aide tone from the first line.
    speak(f'DNA is online. {get_wake_greeting()}')

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

    # ── Behavioral hint (non-intrusive) ──
    try:
        if SUGGESTIONS_ENABLED and STARTUP_SUGGESTIONS_ENABLED:
            top_app = get_scored_startup_suggestion(
                min_count=STARTUP_SUGGESTION_MIN_COUNT,
                min_confidence=STARTUP_SUGGESTION_MIN_CONFIDENCE,
                cooldown_minutes=STARTUP_SUGGESTION_COOLDOWN_MINUTES,
            )
        else:
            top_app = None

        if top_app:
            speak(f'You usually open {top_app} around this time. Say open {top_app} if you want me to launch it.')
    except Exception as e:
        logger.debug('Hourly suggestion check skipped: %s', e)

    last_input_time = time.time()

    while session_get('is_running', True):
        try:
            state = get_state()

            # SLEEPING: listen only for wake word.
            if state == DNAState.SLEEPING:
                session_update('is_listening', False)
                session_update('assistant_state', 'sleeping')
                detected = wait_for_wake_word()

                if not session_get('is_running', True):
                    break

                if not detected:
                    continue

                set_state(DNAState.ACTIVE)
                session_update('assistant_state', 'active')
                last_input_time = time.time()
                speak(random.choice(WAKE_RESPONSES))
                continue

            # ACTIVE: listen for direct commands without wake word.
            if state == DNAState.ACTIVE:
                session_update('is_listening', True)
                session_update('assistant_state', 'active')

                if time.time() - last_input_time > AUTO_SLEEP_TIMEOUT:
                    set_state(DNAState.SLEEPING)
                    session_update('is_listening', False)
                    session_update('assistant_state', 'sleeping')
                    speak(random.choice(TIMEOUT_RESPONSES))
                    continue

                if is_speaking():
                    time.sleep(0.05)
                    continue

                audio = record_audio(duration=ACTIVE_LISTEN_SECONDS)
                if audio is None:
                    continue

                # Any non-silent audio means user is actively trying to speak.
                # This prevents auto-sleep while valid speech is being attempted.
                last_input_time = time.time()

                # First pass: fast decode for low-latency simple commands.
                text = transcribe(audio, fast=True)
                if not text:
                    # Retry once with a slightly longer capture and robust decode.
                    retry_audio = record_audio(duration=ACTIVE_RETRY_SECONDS)
                    if retry_audio is not None:
                        last_input_time = time.time()
                        text = transcribe(retry_audio, fast=False, confidence_offset=-0.2)

                if not text:
                    continue

                # If STT catches only the wake prefix (e.g., "jarvis"),
                # capture a short continuation chunk and merge it.
                if _is_prefix_only_command(text):
                    follow_audio = record_audio(duration=ACTIVE_RETRY_SECONDS)
                    if follow_audio is not None:
                        last_input_time = time.time()
                        follow_text = transcribe(follow_audio, fast=False, confidence_offset=-0.25)
                        if follow_text:
                            text = f'{text} {follow_text}'.strip()

                if _is_prefix_only_command(text):
                    # Treat bare prefix as "waiting for your next phrase".
                    speak(random.choice(WAKE_RESPONSES))
                    continue

                text = _normalize_transcript(text)

                # Dynamically capture continuation when STT returns a partial question.
                if _looks_incomplete_command(text):
                    follow_audio = record_audio(duration=ACTIVE_RETRY_SECONDS + 0.8)
                    if follow_audio is not None:
                        last_input_time = time.time()
                        follow_text = transcribe(follow_audio, fast=False, confidence_offset=-0.3)
                        if follow_text:
                            text = _normalize_transcript(f'{text} {follow_text}')

                if _looks_incomplete_command(text):
                    speak('Please continue, sir.')
                    continue

                logger.info('Command: "%s"', text)

                # Ignore likely noise before touching session timer.
                if len(text.split()) < SHORT_TRANSCRIPT_MIN:
                    continue

                # Explicit dismiss commands are handled before routing.
                if is_dismiss_command(text):
                    set_state(DNAState.SLEEPING)
                    session_update('is_listening', False)
                    session_update('assistant_state', 'sleeping')
                    speak(random.choice(DISMISS_RESPONSES))
                    continue

                last_input_time = time.time()
                session_update('last_command', text)
                set_state(DNAState.PROCESSING)
                session_update('assistant_state', 'processing')

                result = route(text)

                if not result or not result.strip():
                    error_msg = 'I could not process that command. Please try again.'
                    log_command(text, error_msg, 'error')
                    session_update('last_result', error_msg)
                    speak(error_msg)
                    set_state(DNAState.ACTIVE)
                    session_update('assistant_state', 'active')
                    continue

                logger.info('Result: "%s"', result)
                status = 'error' if 'could not' in result.lower() else 'success'
                log_command(text, result, status)
                session_update('last_result', result)
                suppress_next_tts = bool(session_get('suppress_next_tts', False))
                if suppress_next_tts:
                    session_update('suppress_next_tts', False)
                else:
                    speak(result)
                set_state(DNAState.ACTIVE)
                session_update('assistant_state', 'active')
                continue

            # PROCESSING: hold briefly and let execution path transition state.
            if state == DNAState.PROCESSING:
                session_update('assistant_state', 'processing')
                time.sleep(0.05)
                continue

        except KeyboardInterrupt:
            logger.info('Shutting down DNA via KeyboardInterrupt...')
            session_update('is_running', False)
            set_state(DNAState.SLEEPING)
            speak('Goodbye.')
            break
        except Exception as e:
            logger.error('Main loop error: %s', e, exc_info=True)
            cmd_text = locals().get('text', 'unknown')
            log_command(cmd_text, str(e), 'error')
            session_update('last_result', 'Something went wrong. I am still listening.')
            speak('Something went wrong. I am still listening.')
            set_state(DNAState.ACTIVE)
            session_update('assistant_state', 'active')


def main():
    """Boot DNA services and run UI + assistant engine."""
    import importlib
    from core.session import update as session_update, snapshot as session_snapshot
    from core.skill_registry import discover_skills
    from core.proactive import start_proactive_monitors
    from pipeline.memory import init_db, load_session_state, save_session_state
    from pipeline.session_manager import DNAState, set_state
    from ui.tray import start_tray
    run_assistant_window = importlib.import_module('ui.window').run_assistant_window

    logger.info('=' * 50)
    logger.info('  DNA Voice Assistant Starting...')
    logger.info('=' * 50)

    init_db()

    # Restore key session context across restarts (if available).
    restored = load_session_state()
    for key, value in restored.items():
        session_update(key, value)

    discover_skills()
    start_proactive_monitors()
    start_tray()

    # Reflect active startup state in UI immediately.
    set_state(DNAState.ACTIVE)
    session_update('assistant_state', 'active')
    session_update('is_listening', True)

    engine_thread = threading.Thread(
        target=_assistant_loop,
        name='DNAEngineThread',
        daemon=False,
    )
    engine_thread.start()

    try:
        ui_started = run_assistant_window()
        if ui_started:
            logger.info('Assistant window closed. Stopping DNA...')
            session_update('is_running', False)
        else:
            logger.info('Running without desktop window (PySide6 unavailable).')
        engine_thread.join()
    except KeyboardInterrupt:
        logger.info('Shutting down DNA via KeyboardInterrupt...')
        session_update('is_running', False)
        engine_thread.join(timeout=3.0)
    finally:
        # Persist minimal context for next launch continuity.
        save_session_state(session_snapshot())


if __name__ == '__main__':
    main()
