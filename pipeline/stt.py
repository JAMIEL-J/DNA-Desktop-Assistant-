# 1. stdlib
import logging
import re
import time
from difflib import get_close_matches
import threading
from collections import deque

# 2. third-party
import numpy as np
from faster_whisper import WhisperModel

# 3. internal
import sounddevice as sd

from config import (
    WHISPER_MODEL,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    END_OF_SPEECH_SILENCE,
    MIN_SPEECH_SECONDS,
    MIC_CHUNK_SECONDS,
    MIC_PRE_ROLL_SECONDS,
    CONFIDENCE_THRESHOLD,
    STT_FAST_BEAM_SIZE,
    STT_ROBUST_BEAM_SIZE,
)
from core.session import update as session_update

logger = logging.getLogger('dna.stt')

# Lazy-loaded singleton — avoid loading the model until first use
_model = None
_model_lock = threading.Lock()

# Vocabulary prompt — primes Whisper to expect these words
WHISPER_PROMPT = (
    'Hey Jarvis, open notepad, open chrome, open calculator, '
    'volume, mute, unmute, screenshot, '
    'set volume to 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, '
    'play, pause, next track, previous track, '
    'what is the time, what is the date, '
    'what is the current system status, system status, computer status, cpu usage, '
    'shutdown, restart, lock screen, close, launch, '
    'notion, open file explorer, open terminal, open edge, open vscode'
)

# Known words DNA expects — used for fuzzy correction
_KNOWN_WORDS = {
    'notepad', 'chrome', 'calculator', 'explorer', 'terminal',
    'edge', 'vscode', 'paint', 'settings', 'task', 'notion', 'potion',
    'volume', 'mute', 'unmute', 'screenshot', 'shutdown',
    'restart', 'pause', 'play', 'next', 'previous', 'skip',
    'open', 'close', 'launch', 'start', 'set', 'turn',
    'lock', 'screen', 'time', 'date', 'system', 'status', 'current', 'cpu', 'usage',
}

# Common Whisper mishearings → correct word
_CORRECTIONS = {
    'north bad': 'Notepad',
    'northbad': 'Notepad',
    'notbad': 'Notepad',
    'not bad': 'Notepad',
    'note bad': 'Notepad',
    'note pad': 'Notepad',
    'nord pad': 'Notepad',
    'not pad': 'Notepad',
    'knot pad': 'Notepad',
    'calculus': 'calculator',
    'crew': 'chrome',
    'crome': 'chrome',
    'krome': 'chrome',
    'screen shut': 'screenshot',
    'screen shot': 'screenshot',
    'skull code': 'vscode',
    'vs coat': 'vscode',
    'jarvis': 'jarvis',
    'charlie': 'jarvis',
    'charlies': 'jarvis',
    # Number corrections — teens
    'ten': '10',
    'eleven': '11',
    'twelve': '12',
    'thirteen': '13',
    'fourteen': '14',
    'fifteen': '15',
    'sixteen': '16',
    'seventeen': '17',
    'eighteen': '18',
    'nineteen': '19',
    # Number corrections — tens
    'twenty': '20',
    'thirty': '30',
    'forty': '40',
    'fifty': '50',
    'sixty': '60',
    'seventy': '70',
    'eighty': '80',
    'ninety': '90',
    'hundred': '100',
}


def _deduplicate(text: str) -> str:
    """Remove repeated phrases caused by Whisper hallucination loops.

    Detects when Whisper outputs the same phrase over and over
    (e.g. 'open chrome, open chrome, open chrome') and collapses it.
    """
    # Strip punctuation clutter and split by commas or periods
    parts = re.split(r'[,\.]+', text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return text

    # Fuzzy de-duplication for two similar parts (e.g. "close notion, close potion")
    if len(parts) == 2:
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, parts[0], parts[1]).ratio()
        if ratio > 0.7:
            logger.info('Similar parallel repetition detected: "%s" & "%s" (ratio=%.2f) → collapsed', parts[0], parts[1], ratio)
            return parts[0]

    return text


def _correct_transcription(text: str) -> str:
    """Apply fuzzy correction to common Whisper mishearings."""
    if not text:
        return text

    corrected = text.lower()

    # De-duplicate hallucinated repetitions first
    corrected = _deduplicate(corrected)

    # Apply exact phrase corrections first (longest match first)
    for wrong, right in sorted(_CORRECTIONS.items(), key=lambda x: -len(x[0])):
        corrected = corrected.replace(wrong, right)

    # Fuzzy-match individual words against known vocabulary
    words = corrected.split()
    result = []
    for word in words:
        clean = re.sub(r'[^\w]', '', word)
        if clean and clean not in _KNOWN_WORDS and len(clean) > 3:
            matches = get_close_matches(clean, _KNOWN_WORDS, n=1, cutoff=0.7)
            if matches:
                logger.debug('Fuzzy corrected: "%s" → "%s"', clean, matches[0])
                result.append(word.replace(clean, matches[0]))
            else:
                result.append(word)
        else:
            result.append(word)

    return ' '.join(result)


def _get_model():
    """Load the Whisper model once and cache it."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info('Loading Whisper model: %s (compute=%s, device=%s)',
                             WHISPER_MODEL, WHISPER_COMPUTE_TYPE, WHISPER_DEVICE)
                start = time.time()
                _model = WhisperModel(
                    WHISPER_MODEL,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )
                logger.info('Whisper model loaded in %.2fs', time.time() - start)
    return _model


def transcribe(audio_data: np.ndarray, fast: bool = True, confidence_offset: float = 0.0) -> str:
    """Transcribe a numpy audio array to text.

    Args:
        audio_data: Float32 numpy array of audio samples at SAMPLE_RATE Hz.

    Returns:
        Transcribed text string, or empty string on failure.
    """
    try:
        if audio_data is None or len(audio_data) == 0:
            return ''

        # Ensure float32 and mono
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        model = _get_model()
        logger.info('Starting transcription (audio_len=%.1fs)...', len(audio_data) / SAMPLE_RATE)
        
        beam_size = STT_FAST_BEAM_SIZE if fast else STT_ROBUST_BEAM_SIZE
        min_silence_ms = 550 if fast else 800

        segments, info = model.transcribe(
            audio_data,
            beam_size=beam_size,
            language='en',
            vad_filter=True,
            vad_parameters={'min_silence_duration_ms': min_silence_ms},
            initial_prompt=WHISPER_PROMPT,
            condition_on_previous_text=False,
            repetition_penalty=1.5,
            no_repeat_ngram_size=3,
        )

        segment_list = list(segments)
        if not segment_list:
            return ''

        # Discard low-confidence results that are likely background noise.
        avg_logprob = sum(seg.avg_logprob for seg in segment_list) / len(segment_list)
        confidence_cutoff = CONFIDENCE_THRESHOLD + confidence_offset
        if avg_logprob < confidence_cutoff:
            logger.info('Discarded low-confidence transcript (avg_logprob=%.2f)', avg_logprob)
            return ''

        segment_texts = []
        seg_count = 0
        for segment in segment_list:
            seg_count += 1
            logger.debug('Segment %d: "%s" [%.2fs -> %.2fs]', 
                         seg_count, segment.text, segment.start, segment.end)
            segment_texts.append(segment.text.strip())
            
        raw_text = ' '.join(segment_texts).strip()
        text = _correct_transcription(raw_text)

        if text != raw_text.lower():
            logger.info('Corrected: "%s" → "%s"', raw_text, text)
        logger.info('Transcribed (%s, %d segments, %.2fs): "%s"',
                     info.language, seg_count, info.duration, text)
        return text

    except Exception as e:
        logger.error('STT transcription failed: %s', e)
        return ''


def is_silent(audio_data: np.ndarray, threshold: float = 0.01) -> bool:
    """Check if audio data is mostly silence."""
    try:
        if audio_data is None or len(audio_data) == 0:
            return True
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        return rms < threshold
    except Exception as e:
        logger.error('Silence check failed: %s', e)
        return True


def record_audio(duration: float = 6.0) -> np.ndarray | None:
    """Record until speaker finishes, tolerating short pauses.

    `duration` is treated as maximum capture time. Recording ends earlier
    when speech is detected and trailing silence exceeds END_OF_SPEECH_SILENCE.
    """
    try:
        max_duration = max(float(duration or 0.0), 1.0)
        chunk_s = max(0.05, float(MIC_CHUNK_SECONDS))
        chunk_size = max(1, int(SAMPLE_RATE * chunk_s))

        pre_roll_chunks = max(1, int(max(0.0, float(MIC_PRE_ROLL_SECONDS)) / chunk_s))
        pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_chunks)

        frames: list[np.ndarray] = []
        speaking = False
        silence_tail = 0.0
        captured_speech = 0.0
        start = time.time()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocksize=chunk_size,
        ) as stream:
            while (time.time() - start) < max_duration:
                chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    logger.debug('InputStream overflow during capture')

                flat = chunk.flatten().astype(np.float32)
                if flat.size == 0:
                    continue

                rms = float(np.sqrt(np.mean(flat ** 2)))
                session_update('mic_level', min(1.0, rms * 20.0))

                if not speaking:
                    pre_roll.append(flat)
                    if rms >= SILENCE_THRESHOLD:
                        speaking = True
                        frames.extend(pre_roll)
                        pre_roll.clear()
                        silence_tail = 0.0
                    continue

                frames.append(flat)
                captured_speech += chunk_s

                if rms < SILENCE_THRESHOLD:
                    silence_tail += chunk_s
                else:
                    silence_tail = 0.0

                if captured_speech >= MIN_SPEECH_SECONDS and silence_tail >= END_OF_SPEECH_SILENCE:
                    break

        session_update('mic_level', 0.0)

        if not speaking or not frames:
            return None

        audio = np.concatenate(frames)
        if is_silent(audio, threshold=SILENCE_THRESHOLD):
            return None
        return audio
    except Exception as e:
        logger.error('Short audio recording failed: %s', e)
        session_update('mic_level', 0.0)
        return None


def listen_once(timeout: float = 10.0) -> str:
    """Record and transcribe user input once.
    
    Combines record_audio and transcribe into a single step for
    gathering user context or followup information.
    """
    try:
        audio = record_audio(duration=timeout)
        if audio is None or audio.size == 0:
            return ''
        
        text = transcribe(audio, fast=False, confidence_offset=0.0)
        return text.strip()
    except Exception as e:
        logger.error('listen_once failed: %s', e)
        return ''

