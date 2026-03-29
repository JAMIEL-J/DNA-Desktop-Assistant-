"""Phase 1 End-to-End Test: Record audio → Transcribe → Speak back.

Run from project root:
    python test_phase1.py

This will:
1. Record 5 seconds of audio from your microphone
2. Transcribe it using faster-whisper (tiny model)
3. Speak the transcription back using Piper TTS
"""
# 1. stdlib
import logging
import sys
import time

# 2. third-party
import numpy as np
import sounddevice as sd

# 3. internal
from config import SAMPLE_RATE, CHANNELS, RECORD_SECONDS
from pipeline.stt import transcribe, is_silent
from pipeline.tts import speak

# Set up visible logging for the test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger('dna.test')


def record_audio(duration: int = RECORD_SECONDS) -> np.ndarray:
    """Record audio from the default microphone.

    Args:
        duration: Seconds to record.

    Returns:
        Float32 numpy array of audio samples.
    """
    try:
        logger.info('Recording for %d seconds... Speak now!', duration)
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
        )
        sd.wait()
        logger.info('Recording complete.')
        return audio.flatten()
    except Exception as e:
        logger.error('Recording failed: %s', e)
        return np.array([], dtype=np.float32)


def main():
    print('\n' + '=' * 50)
    print('  DNA Phase 1 Test: STT + TTS Pipeline')
    print('=' * 50)

    # Step 1: Record
    print('\n[Step 1] Recording audio...')
    audio = record_audio()

    if is_silent(audio):
        print('[!] Audio appears to be silent. Trying TTS only...')
        result = speak('Hello, I am DNA, your desktop natural assistant.')
        print(f'[TTS Result] {result}')
        return

    # Step 2: Transcribe
    print('\n[Step 2] Transcribing with Whisper...')
    start = time.time()
    text = transcribe(audio)
    elapsed = time.time() - start

    if not text:
        print('[!] No speech detected. Testing TTS with default message...')
        result = speak('I could not hear anything. Please try again.')
        print(f'[TTS Result] {result}')
        return

    print(f'[Transcription] "{text}" ({elapsed:.2f}s)')

    # Step 3: Speak back
    print('\n[Step 3] Speaking back via Piper TTS...')
    response = f'You said: {text}'
    result = speak(response)
    print(f'[TTS Result] {result}')

    print('\n' + '=' * 50)
    print('  Phase 1 Test Complete!')
    print('=' * 50 + '\n')


if __name__ == '__main__':
    main()
