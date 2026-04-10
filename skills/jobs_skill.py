"""
skills/jobs_skill.py
DNA Job Search Skill — Fresher Data Analyst/Science roles, South India
Sources: Indeed India RSS (real-time, no API key) + Internshala browser fallback
"""

import feedparser
import re
import webbrowser
from datetime import datetime, timezone
from config import JOBS_ROLES, JOBS_LOCATION, JOBS_MAX_AGE_DAYS

# ── Constants ─────────────────────────────────────────────────────────────────

INDEED_RSS_TEMPLATES = [
    "https://in.indeed.com/rss?q={query}&l={location}&sort=date&fromage={days}",
]

INTERNSHALA_URL = "https://internshala.com/fresher-jobs/data-science-data-analytics-jobs/"

SEARCH_QUERIES = [
    "data+analyst+fresher",
    "data+science+fresher",
    "data+analyst+entry+level",
    "business+analyst+fresher",
]

SOUTH_INDIA_CITIES = [
    "Chennai", "Bangalore", "Bengaluru", "Hyderabad",
    "Coimbatore", "Kochi", "Pune", "Madurai", "Mysore",
    "Tiruchirappalli", "Trichy", "Vizag", "Visakhapatnam",
    "Mangalore", "Hubli"
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_title(title: str) -> str:
    """Strip HTML and trailing company names from RSS titles."""
    title = re.sub(r'<[^>]+>', '', title)
    title = re.sub(r'\s*-\s*[^-]{1,40}$', '', title).strip()
    return title

def _is_south_india(location: str) -> bool:
    """Check if job location is in South India."""
    if not location:
        return True  # include if location unknown
    loc_lower = location.lower()
    return any(city.lower() in loc_lower for city in SOUTH_INDIA_CITIES)

def _is_fresh_job(published: str, max_days: int) -> bool:
    """Return True if job was posted within max_days."""
    try:
        import time
        parsed = feedparser._parse_date(published)
        if not parsed:
            return True  # include if date unknown
        pub_time = datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
        age = (datetime.now(tz=timezone.utc) - pub_time).days
        return age <= max_days
    except Exception:
        return True  # include if date parsing fails

def _fetch_indeed_jobs(query: str, location: str = "South+India",
                       days: int = 7) -> list[dict]:
    """Fetch jobs from Indeed RSS feed."""
    results = []
    url = INDEED_RSS_TEMPLATES[0].format(
        query=query, location=location, days=days
    )
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title    = _clean_title(entry.get("title", ""))
            company  = entry.get("author", "Unknown Company")
            link     = entry.get("link", "")
            location = entry.get("location", "South India")
            published = entry.get("published", "")

            if not title or not link:
                continue
            if not _is_south_india(location):
                continue
            if not _is_fresh_job(published, days):
                continue

            results.append({
                "title":    title,
                "company":  company,
                "location": location,
                "link":     link,
                "source":   "Indeed"
            })
    except Exception:
        pass
    return results

# ── Main Tools ────────────────────────────────────────────────────────────────

def check_jobs(open_browser: bool = True) -> str:
    """
    Fetch top 5 fresher Data Analyst/Science jobs in South India from Indeed.
    Opens Internshala in browser as fallback if fewer than 3 results found.
    """
    try:
        all_jobs = []

        for query in SEARCH_QUERIES:
            jobs = _fetch_indeed_jobs(
                query=query,
                location="South+India",
                days=JOBS_MAX_AGE_DAYS
            )
            for job in jobs:
                # Deduplicate by link
                if not any(j["link"] == job["link"] for j in all_jobs):
                    all_jobs.append(job)
            if len(all_jobs) >= 10:
                break

        if not all_jobs:
            # Fallback — open Internshala in browser
            if open_browser:
                webbrowser.open(INTERNSHALA_URL)
            return ("I couldn't fetch live job listings right now. "
                    "I've opened Internshala in your browser — "
                    "it has the freshest fresher openings for Data roles in India.")

        top5 = all_jobs[:5]

        # Build spoken response
        count = len(all_jobs)
        response = f"Found {count} fresher Data Analyst and Data Science openings in South India. Here are the top {len(top5)}. "

        for i, job in enumerate(top5, 1):
            loc = job["location"].split(",")[0].strip() if job["location"] else "South India"
            response += (f"Number {i}: {job['title']} at {job['company']}, "
                         f"{loc}. ")

        response += "I've opened the full list in your browser."

        # Open browser with first job link + Internshala
        if open_browser:
            webbrowser.open(top5[0]["link"])
            webbrowser.open(INTERNSHALA_URL)

        return response

    except Exception as e:
        return f"Job search failed: {str(e)}"


def morning_job_check() -> str:
    """
    Lightweight startup check — only speaks if new jobs found today.
    Called on startup, not on demand.
    """
    try:
        jobs = []
        for query in SEARCH_QUERIES[:2]:  # only 2 queries on startup
            jobs += _fetch_indeed_jobs(query=query, location="South+India", days=1)
        jobs = list({j["link"]: j for j in jobs}.values())  # deduplicate

        if not jobs:
            return ""  # silent — no new jobs today, don't bother user

        count = len(jobs)
        top = jobs[0]
        loc = top["location"].split(",")[0].strip() if top["location"] else "South India"
        return (f"By the way, {count} new Data Analyst and Data Science "
                f"fresher job openings posted today in South India. "
                f"Latest one is {top['title']} at {top['company']}, {loc}. "
                f"Say 'show me jobs' for the full list.")

    except Exception:
        return ""  # always silent on startup failure


def open_job_portals() -> str:
    """Open all major job portals for manual browsing."""
    try:
        webbrowser.open(INTERNSHALA_URL)
        webbrowser.open(
            "https://in.indeed.com/q-data-analyst-fresher-jobs.html"
            "?l=South+India&sort=date"
        )
        webbrowser.open(
            "https://www.naukri.com/data-analyst-fresher-jobs-in-south-india"
        )
        return ("Opened Internshala, Indeed, and Naukri in your browser — "
                "all filtered for fresher Data roles in South India.")
    except Exception as e:
        return f"Could not open job portals: {str(e)}"


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "check_jobs":         check_jobs,
    "morning_job_check":  morning_job_check,
    "open_job_portals":   open_job_portals,
}
