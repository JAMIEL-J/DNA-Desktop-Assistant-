# 1. stdlib
import logging
import time
import threading

# 2. third-party
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

# 3. internal
from config import (
    WAKE_WORD_MODEL, WAKE_WORD_THRESHOLD, WAKE_WORD_FRAMEWORK,
    SAMPLE_RATE, WAKE_CHUNK_SIZE,
)

logger = logging.getLogger('dna.wake')

_oww_model = None


def _get_model():
    """Load the OpenWakeWord model once and cache it."""
    global _oww_model
    if _oww_model is None:
        logger.info('Loading wake word model: %s (framework=%s)',
                     WAKE_WORD_MODEL, WAKE_WORD_FRAMEWORK)
        start = time.time()
        _oww_model = Model(
            wakeword_models=[WAKE_WORD_MODEL],
            inference_framework=WAKE_WORD_FRAMEWORK,
        )
        logger.info('Wake word model loaded in %.2fs', time.time() - start)
    return _oww_model


def wait_for_wake_word(timeout: float = None) -> bool:
    """Block until the wake word is detected on the microphone.

    Args:
        timeout: Maximum seconds to wait. None = wait forever.

    Returns:
        True if wake word detected, False if timed out.
    """
    try:
        model = _get_model()
        event = threading.Event()
        start_time = time.time()

        logger.info('Listening for wake word "%s"... (threshold=%.2f)',
                     WAKE_WORD_MODEL, WAKE_WORD_THRESHOLD)

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning('Audio status: %s', status)
            if event.is_set():
                return

            audio_chunk = indata[:, 0]  # mono
            prediction = model.predict(audio_chunk)

            for model_name, score in prediction.items():
                if score > WAKE_WORD_THRESHOLD:
                    logger.info('Wake word detected! model=%s score=%.3f',
                                 model_name, score)
                    event.set()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16',
            blocksize=WAKE_CHUNK_SIZE,
            callback=audio_callback,
        ):
            while not event.is_set():
                if timeout is not None and (time.time() - start_time) >= timeout:
                    logger.info('Wake word timeout after %.1fs', timeout)
                    model.reset()
                    return False
                event.wait(0.05)

        # Reset the model predictions to avoid false triggers next time
        model.reset()
        return True

    except Exception as e:
        logger.error('Wake word detection failed: %s', e)
        return False


def listen_and_record(duration: float = None) -> np.ndarray:
    """Record audio for a fixed duration.

    Args:
        duration: Fixed recording duration in seconds. If None, uses RECORD_SECONDS.

    Returns:
        Float32 numpy array of recorded audio.
    """
    try:
        from config import RECORD_SECONDS

        record_time = duration or RECORD_SECONDS
        logger.info('Recording command for up to %.1fs...', record_time)

        audio = sd.rec(
            int(record_time * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
        )
        sd.wait()

        audio = audio.flatten()
        logger.info('Recorded %.2fs of audio', len(audio) / SAMPLE_RATE)
        return audio

    except Exception as e:
        logger.error('Recording failed: %s', e)
        return np.array([], dtype=np.float32)
