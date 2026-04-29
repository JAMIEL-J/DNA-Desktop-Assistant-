# 1. stdlib
import io
import json
import logging
import time
import wave
from pathlib import Path
import urllib.request
import threading

# 2. third-party
import numpy as np
import sounddevice as sd

# 3. internal
from config import (
    PIPER_MODEL_DIR, PIPER_MODEL_PATH, PIPER_MODEL_JSON,
    PIPER_VOICE, SAMPLE_RATE, TTS_SUPPRESS_MS,
)
from core.session import update as session_update

logger = logging.getLogger('dna.tts')

# Piper voice model download URLs (HuggingFace)
_HF_BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/main'
_VOICE_PARTS = PIPER_VOICE.split('-')  # ['en_US', 'lessac', 'medium']
_LANG_CODE = _VOICE_PARTS[0]  # 'en_US'
_LANG_SHORT = _VOICE_PARTS[0][:2]  # 'en'
_SPEAKER = _VOICE_PARTS[1]  # 'lessac'
_QUALITY = _VOICE_PARTS[2]  # 'medium'
_MODEL_URL = f'{_HF_BASE}/{_LANG_SHORT}/{_LANG_CODE}/{_SPEAKER}/{_QUALITY}/{PIPER_VOICE}.onnx'
_JSON_URL = f'{_HF_BASE}/{_LANG_SHORT}/{_LANG_CODE}/{_SPEAKER}/{_QUALITY}/{PIPER_VOICE}.onnx.json'

# Lazy-loaded Piper synthesizer
_synthesizer = None
_synth_lock = threading.Lock()
_tts_lock = threading.Event()


def _clear_tts_lock_after_playback() -> None:
    """Clear speaking lock after async playback completes and suppress window passes."""
    try:
        sd.wait()
    except Exception:
        pass
    time.sleep(TTS_SUPPRESS_MS / 1000.0)
    _tts_lock.clear()
    session_update('is_speaking', False)


def _download_voice_model():
    """Download Piper voice model files if they don't exist."""
    PIPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not PIPER_MODEL_PATH.exists():
        logger.info('Downloading Piper voice model: %s', PIPER_VOICE)
        logger.info('URL: %s', _MODEL_URL)
        _robust_download(_MODEL_URL, PIPER_MODEL_PATH)
        logger.info('Downloaded: %s', PIPER_MODEL_PATH.name)

    if not PIPER_MODEL_JSON.exists():
        logger.info('Downloading Piper voice config: %s.json', PIPER_VOICE)
        _robust_download(_JSON_URL, PIPER_MODEL_JSON)
        logger.info('Downloaded: %s', PIPER_MODEL_JSON.name)


def _robust_download(url: str, dest_path: Path):
    import urllib.request
    import shutil
    temp_path = dest_path.with_suffix('.tmp')
    try:
        with urllib.request.urlopen(url, timeout=30.0) as response, open(temp_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        # atomic rename
        temp_path.replace(dest_path)
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        logger.error('Download failed for %s: %s', url, e)
        raise e


def _get_synthesizer():
    """Load the Piper synthesizer once and cache it."""
    global _synthesizer
    if _synthesizer is None:
        with _synth_lock:
            if _synthesizer is None:
                _download_voice_model()
        
                logger.info('Loading Piper TTS model: %s', PIPER_VOICE)
                start = time.time()
        
                from piper import PiperVoice
                _synthesizer = PiperVoice.load(str(PIPER_MODEL_PATH))
        
                logger.info('Piper TTS loaded in %.2fs', time.time() - start)
    return _synthesizer


def _synthesize_to_float32(voice, text: str):
    """Synthesize text to a float32 numpy array using Piper.

    Args:
        voice: Loaded PiperVoice instance.
        text: Text to synthesize.

    Returns:
        Tuple of (audio_float32_array, sample_rate).
    """
    tts_sample_rate = voice.config.sample_rate

    # synthesize() yields AudioChunk objects with raw int16 audio
    audio_bytes = b''
    for chunk in voice.synthesize(text):
        audio_bytes += chunk.audio_int16_bytes

    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
    audio_float = audio_int16.astype(np.float32) / 32768.0
    return audio_float, tts_sample_rate


def speak(text: str) -> str:
    """Convert text to speech and play it through the speakers using streaming.

    Args:
        text: The text to speak aloud.

    Returns:
        Confirmation message or error description.
    """
    try:
        if not text or not text.strip():
            return 'Nothing to say.'

        _tts_lock.set()
        session_update('is_speaking', True)
        voice = _get_synthesizer()
        tts_sample_rate = voice.config.sample_rate

        logger.info('Speaking (streaming): "%s"', text)
        
        # Stream chunks directly to audio output as they form
        with sd.OutputStream(samplerate=tts_sample_rate, channels=1, dtype='int16') as stream:
            for chunk in voice.synthesize(text):
                audio_int16 = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
                stream.write(audio_int16)

        return f'Said: {text}'

    except Exception as e:
        logger.error('TTS speak failed: %s', e)
        return f'Could not speak that: {str(e)}'
    finally:
        time.sleep(TTS_SUPPRESS_MS / 1000.0)
        _tts_lock.clear()
        session_update('is_speaking', False)


def speak_async(text: str) -> str:
    """Convert text to speech and play without blocking using a background thread."""
    if not text or not text.strip():
        return 'Nothing to say.'

    def _async_worker():
        speak(text)

    threading.Thread(target=_async_worker, daemon=True).start()
    return f'Speaking: {text}'


def is_speaking() -> bool:
    """Return True while TTS is speaking or in short suppression window."""
    return _tts_lock.is_set()


