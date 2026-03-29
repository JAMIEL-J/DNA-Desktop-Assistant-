# 1. stdlib
import io
import json
import logging
import time
import wave
from pathlib import Path
from urllib.request import urlretrieve

# 2. third-party
import numpy as np
import sounddevice as sd

# 3. internal
from config import (
    PIPER_MODEL_DIR, PIPER_MODEL_PATH, PIPER_MODEL_JSON,
    PIPER_VOICE, SAMPLE_RATE,
)

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


def _download_voice_model():
    """Download Piper voice model files if they don't exist."""
    PIPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not PIPER_MODEL_PATH.exists():
        logger.info('Downloading Piper voice model: %s', PIPER_VOICE)
        logger.info('URL: %s', _MODEL_URL)
        urlretrieve(_MODEL_URL, str(PIPER_MODEL_PATH))
        logger.info('Downloaded: %s', PIPER_MODEL_PATH.name)

    if not PIPER_MODEL_JSON.exists():
        logger.info('Downloading Piper voice config: %s.json', PIPER_VOICE)
        urlretrieve(_JSON_URL, str(PIPER_MODEL_JSON))
        logger.info('Downloaded: %s', PIPER_MODEL_JSON.name)


def _get_synthesizer():
    """Load the Piper synthesizer once and cache it."""
    global _synthesizer
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
    """Convert text to speech and play it through the speakers.

    Args:
        text: The text to speak aloud.

    Returns:
        Confirmation message or error description.
    """
    try:
        if not text or not text.strip():
            return 'Nothing to say.'

        voice = _get_synthesizer()
        audio_float, tts_sample_rate = _synthesize_to_float32(voice, text)

        sd.play(audio_float, samplerate=tts_sample_rate)
        sd.wait()

        logger.info('Spoke: "%s" (%.1fs audio)', text,
                     len(audio_float) / tts_sample_rate)
        return f'Said: {text}'

    except Exception as e:
        logger.error('TTS speak failed: %s', e)
        return f'Could not speak that: {str(e)}'


def speak_async(text: str) -> str:
    """Convert text to speech and play without blocking.

    Args:
        text: The text to speak aloud.

    Returns:
        Confirmation message or error description.
    """
    try:
        if not text or not text.strip():
            return 'Nothing to say.'

        voice = _get_synthesizer()
        audio_float, tts_sample_rate = _synthesize_to_float32(voice, text)

        sd.play(audio_float, samplerate=tts_sample_rate)

        logger.info('Speaking (async): "%s"', text)
        return f'Speaking: {text}'

    except Exception as e:
        logger.error('TTS async speak failed: %s', e)
        return f'Could not speak that: {str(e)}'


