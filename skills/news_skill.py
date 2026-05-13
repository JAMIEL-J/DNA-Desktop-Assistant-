"""
skills/news_skill.py
DNA News Aggregator — LIVE news with headline briefs (no API key needed)

Strategy for freshness + quality:
  1. TechCrunch / Ars Technica → direct feeds with rich summaries (always fresh)
  2. Google News `when:1d` → last-24h headlines, brief fetched from page
  3. Every headline includes a 1-line brief so the user gets context

Capabilities:
  1. get_news(topic)       - headlines + briefs for any topic
  2. get_ai_news()         - AI/ML specific (live, last 24h)
  3. get_tech_news()       - technology (live, last 24h)
  4. get_india_news()      - India top stories (last 24h)
  5. get_cricket_score()   - cricket updates (last 24h)
  6. get_headlines()       - general top stories (last 24h)
  7. morning_news_brief()  - compact startup briefing (2-3 headlines with briefs)
"""

import feedparser
import html
import logging
import re
import time
from datetime import datetime, timezone

logger = logging.getLogger('dna.skill.news')

# ── RSS Feed Sources (LIVE — last 24h or direct publisher) ────────────────────

FEEDS = {
    "ai": [
        # TechCrunch AI — always has rich summaries
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        # Google News last 24h — AI focused (wider net)
        "https://news.google.com/rss/search?q=OpenAI+OR+ChatGPT+OR+Gemini+AI+OR+Claude+AI+OR+Google+AI+when:1d&hl=en&gl=US&ceid=US:en",
    ],
    "tech": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://news.google.com/rss/search?q=technology+startup+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "india": [
        "https://news.google.com/rss/search?q=India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "cricket": [
        "https://news.google.com/rss/search?q=cricket+score+India+OR+IPL+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "world": [
        "https://news.google.com/rss/search?q=world+news+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    ],
    "business": [
        "https://news.google.com/rss/search?q=stock+market+business+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Strip HTML tags and entities, normalize whitespace."""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _clean_title(title: str) -> str:
    """Strip source suffix from Google News titles."""
    title = _clean_text(title)
    # Remove " - Source Name" suffix common in Google News
    title = re.sub(r'\s*-\s*[^-]{1,40}$', '', title).strip()
    return title


def _extract_brief(summary_raw: str) -> str:
    """Extract a 1-sentence brief from RSS summary/description."""
    if not summary_raw:
        return ""
    text = _clean_text(summary_raw)
    if len(text) < 15:
        return ""  # too short, probably just repeats title

    # Take first sentence (up to period, question mark, or 150 chars)
    match = re.match(r'^(.{30,200}?[.!?])\s', text)
    if match:
        return match.group(1).strip()
    # No clean sentence break — just truncate at 150 chars
    return text[:150].rsplit(' ', 1)[0] + '...' if len(text) > 150 else text


def _fetch_page_brief(url: str) -> str:
    """Fetch a web page and extract first meaningful paragraph as brief."""
    import requests
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try meta description first (fastest, most reliable)
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            desc = _clean_text(meta["content"])
            if len(desc) > 30:
                return _extract_brief(desc)

        # Try og:description
        og = soup.find("meta", attrs={"property": "og:description"})
        if og and og.get("content"):
            desc = _clean_text(og["content"])
            if len(desc) > 30:
                return _extract_brief(desc)

        # Fallback: first <p> tag with meaningful text
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 50:
                return _extract_brief(text)

    except Exception as e:
        logger.debug("Page brief fetch failed for %s: %s", url, e)
    return ""


def _parse_pub_date(published: str):
    """Try to parse a published date string into a datetime."""
    if not published:
        return None
    try:
        parsed = feedparser._parse_date(published)
        if parsed:
            return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    except Exception:
        pass
    try:
        clean = re.sub(r'[+-]\d{2}:\d{2}$', '', published).strip()
        return datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None


def _time_ago(pub_date) -> str:
    """Return a human-friendly 'X hours ago' string."""
    if not pub_date:
        return ""
    try:
        now = datetime.now(tz=timezone.utc)
        delta = now - pub_date
        hours = delta.total_seconds() / 3600
        if hours < 1:
            mins = int(delta.total_seconds() / 60)
            return f"{mins} minutes ago" if mins > 1 else "just now"
        elif hours < 24:
            h = int(hours)
            return f"{h} hour{'s' if h != 1 else ''} ago"
        else:
            d = int(hours / 24)
            return f"{d} day{'s' if d != 1 else ''} ago"
    except Exception:
        return ""


def _fetch_feed(urls: list, max_items: int = 5, fetch_briefs: bool = True) -> list[dict]:
    """
    Fetch and parse RSS feed(s), return top N items sorted by freshness.
    For items without a summary, fetches the page meta description.
    """
    all_items = []
    seen_titles = set()

    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items * 3]:  # fetch extra, we'll sort+dedup
                raw_title = entry.get("title", "")
                title = _clean_title(raw_title)
                if not title or len(title) < 10:
                    continue

                # Deduplicate by normalized key (first 40 chars lowercase)
                dedup_key = re.sub(r'[^a-z0-9]', '', title.lower())[:40]
                if dedup_key in seen_titles:
                    continue
                seen_titles.add(dedup_key)

                pub_str = entry.get("published", "")
                pub_date = _parse_pub_date(pub_str)

                # Extract brief from RSS summary field
                summary_raw = entry.get("summary", "") or entry.get("description", "")
                brief = _extract_brief(summary_raw)

                # Check if brief is just the title repeated (Google News does this)
                if brief and _is_same_as_title(brief, title):
                    brief = ""

                source = entry.get("source", {}).get("title", "")
                if not source and hasattr(feed, 'feed'):
                    source = feed.feed.get("title", "")
                # Clean source name
                source = _clean_text(source).replace(" | ", " ").strip()

                link = entry.get("link", "")

                all_items.append({
                    "title":     title,
                    "brief":     brief,
                    "source":    source,
                    "link":      link,
                    "published": pub_str,
                    "pub_date":  pub_date,
                    "ago":       _time_ago(pub_date),
                })

        except Exception as e:
            logger.debug("Feed fetch failed for %s: %s", url, e)
            continue

    # Sort by publish date (newest first)
    all_items.sort(
        key=lambda x: x["pub_date"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )

    items = all_items[:max_items]

    # For items missing a brief, try fetching from the page (limit to 2 fetches)
    if fetch_briefs:
        fetched = 0
        for item in items:
            if not item["brief"] and item["link"] and fetched < 2:
                item["brief"] = _fetch_page_brief(item["link"])
                fetched += 1

    return items


def _is_same_as_title(brief: str, title: str) -> bool:
    """Check if the brief is basically the same as the title."""
    norm_brief = re.sub(r'[^a-z0-9]', '', brief.lower())[:40]
    norm_title = re.sub(r'[^a-z0-9]', '', title.lower())[:40]
    return norm_brief == norm_title or norm_brief.startswith(norm_title[:25])


def _speak_headlines(items: list, topic: str, count: int = 5) -> str:
    """Build a spoken summary with headline + brief for each item."""
    if not items:
        return f"I couldn't find any {topic} news right now."

    count = min(count, len(items))
    response = f"Here are the top {count} {topic} headlines. "

    for i, item in enumerate(items[:count], 1):
        ago = f", {item['ago']}" if item.get('ago') else ""
        brief = f" {item['brief']}" if item.get('brief') else ""
        response += f"Number {i}: {item['title']}{ago}.{brief} "

    return response.strip()


# ── Main Tools ────────────────────────────────────────────────────────────────

def get_news(topic: str = "technology") -> str:
    """Get news headlines for any topic using Google News RSS."""
    topic = topic.strip().lower() if topic else "technology"

    topic_map = {
        "ai": "ai", "artificial intelligence": "ai", "machine learning": "ai",
        "ml": "ai", "openai": "ai", "chatgpt": "ai", "gemini": "ai",
        "tech": "tech", "technology": "tech", "gadgets": "tech",
        "india": "india", "indian": "india", "domestic": "india",
        "cricket": "cricket", "ipl": "cricket", "match": "cricket",
        "world": "world", "global": "world", "international": "world",
        "business": "business", "stock": "business", "market": "business",
        "finance": "business",
    }

    feed_key = topic_map.get(topic)

    if feed_key and feed_key in FEEDS:
        items = _fetch_feed(FEEDS[feed_key], max_items=5)
        return _speak_headlines(items, topic)
    else:
        custom_url = (
            f"https://news.google.com/rss/search?"
            f"q={topic.replace(' ', '+')}+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
        )
        items = _fetch_feed([custom_url], max_items=5)
        return _speak_headlines(items, topic)


def get_ai_news() -> str:
    """Get the latest AI and tech news (live, last 24h, with briefs)."""
    items = _fetch_feed(FEEDS["ai"], max_items=5)
    return _speak_headlines(items, "AI and tech")


def get_tech_news() -> str:
    """Get the latest technology news (live, last 24h, with briefs)."""
    items = _fetch_feed(FEEDS["tech"], max_items=5)
    return _speak_headlines(items, "technology")


def get_india_news() -> str:
    """Get top India news stories (last 24h)."""
    items = _fetch_feed(FEEDS["india"], max_items=5)
    return _speak_headlines(items, "India")


def get_cricket_score() -> str:
    """Get latest cricket updates and scores."""
    items = _fetch_feed(FEEDS["cricket"], max_items=5)
    return _speak_headlines(items, "cricket")


def get_headlines() -> str:
    """Get general top news headlines."""
    items = _fetch_feed(FEEDS["world"], max_items=5)
    return _speak_headlines(items, "world")


def morning_news_brief() -> str:
    """
    Compact startup briefing — 2 AI/tech headlines with briefs.
    Called at startup. Focused on what the user cares about.
    """
    try:
        import random
        # Fetch a pool of top 10 items so we can randomly pick 2 for variety
        pool = _fetch_feed(FEEDS["ai"], max_items=10, fetch_briefs=False)

        if not pool:
            return ""

        # Randomly select 2 items to ensure we don't repeat the exact same news every startup
        items = random.sample(pool, min(2, len(pool)))
        
        # Sort the selected 2 items by publish date so the newest is spoken first
        items.sort(key=lambda x: x["pub_date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        # Now fetch briefs ONLY for the 2 items we selected to save time
        fetched = 0
        for item in items:
            if not item["brief"] and item["link"] and fetched < 2:
                item["brief"] = _fetch_page_brief(item["link"])
                fetched += 1

        parts = []
        for item in items:
            ago = f", {item['ago']}" if item.get('ago') else ""
            brief = f" {item['brief']}" if item.get('brief') else ""
            parts.append(f"{item['title']}{ago}.{brief}")

        return "Here's what's happening in AI and tech. " + " ".join(parts)

    except Exception as e:
        logger.debug("Morning news brief failed: %s", e)
        return ""  # Silent on failure


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "get_news":           get_news,
    "get_ai_news":        get_ai_news,
    "get_tech_news":      get_tech_news,
    "get_india_news":     get_india_news,
    "get_cricket_score":  get_cricket_score,
    "get_headlines":      get_headlines,
    "morning_news_brief": morning_news_brief,
}
