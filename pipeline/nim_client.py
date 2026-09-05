# pipeline/nim_client.py
# ──────────────────────────────────────────────────────────────────────
# NVIDIA NIM transport — OpenAI-shape chat calls with key rotation.
# Free tier throttles ~40 RPM *account-wide*: keys rotate, Retry-After
# is honored (capped), then NIMRateLimited lets the caller cascade to
# OpenRouter-free → Gemini → Ollama. No new deps (requests only).
# ──────────────────────────────────────────────────────────────────────

# 1. stdlib
import logging
import re
import threading
import time
from typing import Any

# 2. third-party
import requests

# 3. internal
from config import NIM_URL, NIM_TIMEOUT, NVIDIA_API_KEYS

logger = logging.getLogger('dna.llm.nim')


class NIMRateLimited(Exception):
    """All NIM keys throttled or unreachable — caller should cascade."""


class NIMError(Exception):
    """Non-retryable NIM failure (bad request, bad key on all keys)."""


_key_lock = threading.Lock()
_key_index = 0


def _ordered_keys() -> list[str]:
    """Round-robin key order starting after last used index."""
    global _key_index
    keys = [k for k in (NVIDIA_API_KEYS or []) if k]
    if not keys:
        raise NIMRateLimited("No NVIDIA_API_KEY_1/_2 configured.")
    with _key_lock:
        start = _key_index % len(keys)
        _key_index += 1
    return keys[start:] + keys[:start]


def _strip_think(text: str) -> str:
    """Remove reasoning traces: <think>..</think> pairs and stray </think>."""
    if not text:
        return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.replace('</think>', '').strip()


def call_nim(model: str, messages: list[dict], temperature: float = 0.2,
             max_tokens: int = 1024, timeout: float | None = None) -> str:
    """Chat completion via NIM. Returns assistant `content` (never thinking).

    Reasoning budget: callers MUST allow generous max_tokens — thinking
    consumes output budget first (Glimmer returned empty at 64 tokens).
    Raises NIMRateLimited (cascade) or NIMError (give up).
    """
    last_err: Exception | None = None
    for key in _ordered_keys():
        try:
            resp = requests.post(
                NIM_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                timeout=timeout or NIM_TIMEOUT,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning('NIM transport failed, trying next key: %s', e)
            last_err = e
            continue
        if resp.status_code == 200:
            try:
                content = resp.json()["choices"][0]["message"].get("content", "") or ""
            except Exception as e:
                raise NIMError(f"NIM response parse failed: {e}")
            return _strip_think(content)
        if resp.status_code == 429:
            wait = 0.0
            try:
                wait = min(float(resp.headers.get("Retry-After", "2")), 5.0)
            except (TypeError, ValueError):
                wait = 2.0
            logger.warning('NIM 429, waiting %.1fs then next key.', wait)
            time.sleep(wait)
            last_err = NIMRateLimited(f"NIM throttled (429) for {model}.")
            continue
        if resp.status_code in (401, 403):
            logger.warning('NIM key rejected (%s), trying next key.', resp.status_code)
            last_err = NIMError(f"NIM auth failed ({resp.status_code}).")
            continue
        raise NIMError(f"NIM HTTP {resp.status_code}: {resp.text[:200]}")
    if isinstance(last_err, NIMRateLimited):
        raise last_err
    raise NIMRateLimited(f"All NIM keys exhausted for {model}: {last_err}")
