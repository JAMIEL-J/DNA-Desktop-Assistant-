# pipeline/openrouter_client.py
# ──────────────────────────────────────────────────────────────────────
# OpenRouter Fallback Client — Single model fallback (google/gemma-4-26b-a4b-it:free)
# Triggered when primary NVIDIA NIM API endpoints rate-limit (HTTP 429)
# ──────────────────────────────────────────────────────────────────────

import json
import logging
import requests
from typing import Any, Optional
from config import OPENROUTER_API_KEY, OPENROUTER_FALLBACK_MODEL

logger = logging.getLogger('dna.pipeline.openrouter')

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter_fallback(
    prompt: str,
    system_instruction: str = "",
    context: Optional[dict[str, Any]] = None
) -> str:
    """Call OpenRouter fallback API using strictly google/gemma-4-26b-a4b-it:free.
    
    Injects Blackboard session state and history for stateless continuity.
    """
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY is not set. OpenRouter fallback cannot execute.")
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    # Enhance system instruction with Blackboard context if available
    augmented_system = system_instruction or "You are a helpful AI assistant."
    if context:
        augmented_system += f"\n\nBLACKBOARD SESSION CONTEXT:\n{json.dumps(context, indent=2)}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/JAMIEL-J/DNA-Desktop-Assistant-",
        "X-Title": "DNA Desktop Assistant"
    }

    payload = {
        "model": OPENROUTER_FALLBACK_MODEL,  # google/gemma-4-26b-a4b-it:free
        "messages": [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    logger.info("Executing OpenRouter fallback request with model: %s", OPENROUTER_FALLBACK_MODEL)

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            content = choices[0]["message"].get("content", "").strip()
            return content
        
        logger.error("Unexpected OpenRouter response structure: %s", data)
        raise ValueError("Invalid response structure from OpenRouter")
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        error_text = e.response.text if e.response is not None else str(e)
        logger.error("OpenRouter HTTP Error %s: %s", status_code, error_text)
        raise RuntimeError(f"OpenRouter HTTP Error {status_code}: {error_text}")
    except Exception as e:
        logger.error("OpenRouter execution failed: %s", e)
        raise
