"""
skills/web_skill.py
DNA Web Search Skill — Real-time web search + page summarization
Uses DuckDuckGo (no API key needed) with Gemini/Ollama summarization.

Capabilities:
  1. web_search(query) - search the web, summarize top results
  2. fetch_and_summarize(url) - read a page and summarize it
"""

import logging
import re
import time

from config import (
    GOOGLE_API_KEY,
    CLOUD_LLM_MODEL,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)

logger = logging.getLogger('dna.skill.web')


# ── Search Engine ─────────────────────────────────────────────────────────────

def _duckduckgo_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo and return top results.
    Returns: [{"title": ..., "url": ..., "snippet": ...}, ...]
    """
    import requests
    results = []

    try:
        # DuckDuckGo HTML search (no API key needed)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result")[:max_results]:
            title_el = result.select_one(".result__title a, .result__a")
            snippet_el = result.select_one(".result__snippet")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # DuckDuckGo wraps URLs in redirects
            if "uddg=" in url:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                url = parsed.get("uddg", [url])[0]

            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                })

    except Exception as e:
        logger.error("DuckDuckGo search failed: %s", e)

    return results


def _fetch_page_text(url: str, max_chars: int = 3000) -> str:
    """Fetch a web page and extract readable text."""
    import requests

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "form", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        return text[:max_chars]

    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
        return ""


# ── LLM Summarization ────────────────────────────────────────────────────────

def _summarize_with_gemini(context: str, question: str) -> str:
    """Use Gemini to summarize search results for voice."""
    import importlib
    genai = importlib.import_module('google.genai')
    client = genai.Client(api_key=GOOGLE_API_KEY)

    prompt = (
        "You are DNA, a voice assistant. The user asked a question and you "
        "searched the web. Summarize the search results below into a spoken "
        "answer. Rules:\n"
        "- Maximum 3-4 sentences\n"
        "- Plain text only, no markdown, no bullet points\n"
        "- Be specific with facts, numbers, names\n"
        "- If the results don't answer the question, say so honestly\n"
        "- Address the user as 'sir'\n\n"
        f"User question: {question}\n\n"
        f"Search results:\n{context}"
    )

    response = client.models.generate_content(
        model=CLOUD_LLM_MODEL,
        contents=prompt,
    )

    text = (getattr(response, 'text', '') or '').strip()
    # Clean LLM artifacts
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.replace('**', '').replace('*', '').replace('`', '').replace('#', '')
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return ' '.join(lines) if lines else "I found some results but couldn't summarize them clearly."


def _summarize_with_ollama(context: str, question: str) -> str:
    """Use local Ollama to summarize search results."""
    import requests

    prompt = (
        f"Summarize these web search results to answer: {question}\n"
        f"Keep it under 3 sentences. Plain text only.\n\n{context}"
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            'model': OLLAMA_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,
            'options': {'temperature': 0.3},
        },
        timeout=OLLAMA_TIMEOUT * 2,
    )
    response.raise_for_status()
    return str(response.json().get('message', {}).get('content', '')).strip()


# ── Main Tools ────────────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    """
    Search the web and return a voice-friendly summary.
    Works for: "KFC offers today", "latest AI news", "cricket score", etc.
    """
    if not query or not query.strip():
        return "What would you like me to search for?"

    try:
        logger.info("Web searching: %s", query)
        results = _duckduckgo_search(query, max_results=5)

        if not results:
            return f"I searched for {query} but didn't find any relevant results."

        # Build context from snippets + one page fetch
        context_parts = []
        for i, r in enumerate(results[:5], 1):
            context_parts.append(f"{i}. {r['title']}: {r['snippet']}")

        # Try to fetch the first result's full page for richer answers
        if results:
            page_text = _fetch_page_text(results[0]['url'])
            if page_text:
                context_parts.append(f"\nDetailed content from top result:\n{page_text[:1500]}")

        context = "\n".join(context_parts)

        # Summarize with LLM
        if GOOGLE_API_KEY:
            try:
                return _summarize_with_gemini(context, query)
            except Exception as e:
                logger.error("Gemini summarization failed: %s", e)

        # Ollama fallback
        try:
            return _summarize_with_ollama(context, query)
        except Exception as e:
            logger.error("Ollama summarization failed: %s", e)

        # Raw fallback — just read snippets
        top3 = results[:3]
        response = f"Here's what I found for {query}. "
        for r in top3:
            response += f"{r['title']}: {r['snippet']}. "
        return response

    except Exception as e:
        logger.error("web_search failed: %s", e)
        return f"Sorry boss, the web search failed: {str(e)}"


def fetch_and_summarize(url: str) -> str:
    """Fetch a specific URL and summarize its content."""
    if not url or not url.strip():
        return "Please provide a URL to read."

    try:
        text = _fetch_page_text(url, max_chars=4000)
        if not text:
            return "I couldn't read that page."

        question = f"Summarize this web page content"

        if GOOGLE_API_KEY:
            try:
                return _summarize_with_gemini(text, question)
            except Exception:
                pass

        try:
            return _summarize_with_ollama(text, question)
        except Exception:
            pass

        # Raw truncated text
        return text[:500] + "..."

    except Exception as e:
        return f"Could not read that page: {str(e)}"


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "web_search":          web_search,
    "fetch_and_summarize": fetch_and_summarize,
}
