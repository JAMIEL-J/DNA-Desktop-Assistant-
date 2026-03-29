# 1. stdlib
import logging
import re
import time
from difflib import get_close_matches

# 2. third-party
import numpy as np
from faster_whisper import WhisperModel

# 3. internal
from config import WHISPER_MODEL, WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, SAMPLE_RATE

logger = logging.getLogger('dna.stt')

# Lazy-loaded singleton — avoid loading the model until first use
_model = None

# Vocabulary prompt — primes Whisper to expect these words
WHISPER_PROMPT = (
    'Hey Jarvis, open notepad, open chrome, open calculator, '
    'volume, mute, unmute, screenshot, '
    'set volume to 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, '
    'play, pause, next track, previous track, '
    'what is the time, what is the date, '
    'shutdown, restart, lock screen, close, launch, '
    'open file explorer, open terminal, open edge, open vscode'
)

# Known words DNA expects — used for fuzzy correction
_KNOWN_WORDS = {
    'notepad', 'chrome', 'calculator', 'explorer', 'terminal',
    'edge', 'vscode', 'paint', 'settings', 'task',
    'volume', 'mute', 'unmute', 'screenshot', 'shutdown',
    'restart', 'pause', 'play', 'next', 'previous', 'skip',
    'open', 'close', 'launch', 'start', 'set', 'turn',
    'lock', 'screen', 'time', 'date',
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

    # If >50% of parts are identical, collapse to a single instance
    from collections import Counter
    counts = Counter(parts)
    most_common, freq = counts.most_common(1)[0]
    if freq > 1 and freq / len(parts) > 0.5:
        logger.info('Hallucination detected: "%s" repeated %dx → collapsed', most_common, freq)
        return most_common

    # Also catch consecutive duplicates: "open chrome open chrome" (no comma)
    words = text.split()
    # Try ngram sizes from large to small
    for n in range(min(5, len(words) // 2), 0, -1):
        ngram = ' '.join(words[:n])
        repetitions = 0
        i = 0
        while i + n <= len(words):
            chunk = ' '.join(words[i:i + n])
            if chunk == ngram:
                repetitions += 1
                i += n
            else:
                break
        if repetitions > 2 and repetitions * n >= len(words) * 0.5:
            logger.info('Hallucination detected (ngram=%d): "%s" repeated %dx → collapsed', n, ngram, repetitions)
            return ngram

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
                result.append(matches[0])
            else:
                result.append(word)
        else:
            result.append(word)

    return ' '.join(result)


def _get_model():
    """Load the Whisper model once and cache it."""
    global _model
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


def transcribe(audio_data: np.ndarray) -> str:
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
        segments, info = model.transcribe(
            audio_data,
            beam_size=3,
            language='en',
            vad_filter=True,
            initial_prompt=WHISPER_PROMPT,
            condition_on_previous_text=False,
            repetition_penalty=1.5,
            no_repeat_ngram_size=3,
        )

        raw_text = ' '.join(segment.text.strip() for segment in segments).strip()
        text = _correct_transcription(raw_text)

        if text != raw_text.lower():
            logger.info('Corrected: "%s" → "%s"', raw_text, text)
        logger.info('Transcribed (%s, %.2fs): "%s"',
                     info.language, info.duration, text)
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

