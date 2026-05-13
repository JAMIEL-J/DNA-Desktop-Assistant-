"""
skills/job_search_skill.py
DNA Job Search Mode — Full Implementation

Features:
- Multi-role search (DA, DS, ML, BA, DE)
- Indeed RSS + Internshala scraping
- Deduplication + date ranking
- Save results to CSV
- Job search session state (next/open/save/exit)
- Fresher-focused, South India filtered
"""

import csv
import feedparser
import logging
import os
import re
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from config import (
    JOB_ROLES, JOB_LOCATION, JOB_MAX_AGE_DAYS,
    JOB_RESULTS_DIR, JOB_EXPERIENCE_LEVEL,
)

logger = logging.getLogger('dna.skill.job_search')

# ── Role Configuration ────────────────────────────────────────────────────────

ROLE_QUERIES = {
    "data analyst":     ["data analyst fresher", "data analyst entry level",
                         "junior data analyst"],
    "data scientist":   ["data scientist fresher", "data science fresher",
                         "junior data scientist", "ml engineer fresher"],
    "business analyst": ["business analyst fresher", "junior business analyst",
                         "BA fresher"],
    "data engineer":    ["data engineer fresher", "junior data engineer",
                         "ETL developer fresher"],
    "ml engineer":      ["machine learning engineer fresher", "ml engineer fresher",
                         "AI engineer fresher"],
    "all":              ["data analyst fresher", "data scientist fresher",
                         "business analyst fresher", "data engineer fresher"],
}

SOUTH_INDIA_CITIES = [
    "chennai", "bangalore", "bengaluru", "hyderabad", "coimbatore",
    "kochi", "cochin", "madurai", "mysore", "mysuru", "trichy",
    "tiruchirappalli", "vizag", "visakhapatnam", "mangalore",
    "hubli", "salem", "vellore", "pondicherry", "puducherry",
    "tirunelveli", "erode", "tiruppur", "south india", "tamil nadu",
    "karnataka", "kerala", "andhra", "telangana"
]

# ── Session State ─────────────────────────────────────────────────────────────

_search_session = {
    "active":        False,
    "results":       [],      # all fetched jobs
    "current_index": 0,       # pointer for next/previous
    "current_role":  "all",
    "saved_jobs":    [],      # bookmarked this session
    "last_search":   None,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_south_india(location: str) -> bool:
    if not location:
        return True
    loc = location.lower()
    return any(city in loc for city in SOUTH_INDIA_CITIES)

def _is_recent(published: str, max_days: int = 14) -> bool:
    try:
        import time as t
        parsed = feedparser._parse_date(published)
        if not parsed:
            return True
        pub = datetime.fromtimestamp(t.mktime(parsed), tz=timezone.utc)
        return (datetime.now(tz=timezone.utc) - pub).days <= max_days
    except Exception:
        return True

def _clean_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _deduplicate(jobs: list) -> list:
    seen_titles = set()
    unique = []
    for job in jobs:
        key = f"{job['title'].lower()[:40]}_{job['company'].lower()[:20]}"
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(job)
    return unique


# ── Fetchers ──────────────────────────────────────────────────────────────────

def _fetch_indeed(query: str, days: int = 14) -> list:
    """Fetch from Indeed India RSS."""
    results = []
    url = (f"https://in.indeed.com/rss?"
           f"q={query.replace(' ', '+')}"
           f"&l=South+India&sort=date&fromage={days}")
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title    = _clean_text(entry.get("title", ""))
            company  = entry.get("author", "Unknown")
            link     = entry.get("link", "")
            location = entry.get("location", "South India")
            published = entry.get("published", "")

            if not title or not link:
                continue
            if not _is_south_india(location):
                continue
            if not _is_recent(published, days):
                continue

            # Strip company from title if present
            title = re.sub(r'\s*-\s*' + re.escape(company) + r'$', '',
                           title, flags=re.IGNORECASE).strip()

            results.append({
                "title":     title,
                "company":   _clean_text(company),
                "location":  location.split(",")[0].strip(),
                "link":      link,
                "source":    "Indeed",
                "published": published,
            })
    except Exception as e:
        logger.debug('Indeed fetch failed: %s', e)
    return results


def _fetch_internshala(role: str) -> list:
    """Scrape Internshala fresher jobs."""
    results = []
    
    # Use proper Internshala category slugs
    if role == "data" or role == "all":
        role_slug = "data-science,data-analytics"
    else:
        role_slug = role.lower().replace(" ", "-")
        
    # Internshala doesn't support 'south-india' region, so we must query the major cities explicitly.
    cities = ["bangalore", "chennai", "hyderabad"]
    
    for city in cities:
        url = f"https://internshala.com/fresher-jobs/{role_slug}-jobs-in-{city}/"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            import requests
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            # Fetch up to 20 cards per city to keep request times reasonable
            cards = soup.select(".individual_internship")[:20]

            for card in cards:
                try:
                    title_el   = card.select_one(".job-title-href, .profile")
                    company_el = card.select_one(".company_name, .company-name")
                    loc_el     = card.select_one(".locations, .location_names")
                    link_el    = card.select_one("a.job-title-href, a[href*='/job/']")

                    title   = _clean_text(title_el.text) if title_el else ""
                    company = _clean_text(company_el.text) if company_el else "Unknown"
                    loc     = _clean_text(loc_el.text) if loc_el else city.title()
                    href    = link_el.get("href", "") if link_el else ""
                    link    = f"https://internshala.com{href}" if href.startswith("/") else href

                    if title and link:
                        results.append({
                            "title":     title,
                            "company":   company,
                            "location":  loc.split(",")[0].strip(),
                            "link":      link,
                            "source":    "Internshala",
                            "published": datetime.now().isoformat(),
                        })
                except Exception:
                    continue
        except ImportError:
            logger.warning('beautifulsoup4 not installed. Internshala scraping disabled.')
            break
        except Exception as e:
            logger.debug('Internshala fetch failed for %s: %s', city, e)

    return results


# ── Core Search ───────────────────────────────────────────────────────────────

def _run_search(role: str = "all") -> list:
    """Run full search for a role. Returns deduplicated sorted list."""
    queries = ROLE_QUERIES.get(role.lower(), ROLE_QUERIES["all"])
    all_jobs = []

    for query in queries[:3]:  # limit to 3 queries to avoid rate limiting
        all_jobs += _fetch_indeed(query, days=JOB_MAX_AGE_DAYS)
        time.sleep(0.3)  # polite delay

    # Internshala scrape
    internshala_role = role if role != "all" else "data"
    all_jobs += _fetch_internshala(internshala_role)

    # ── Strict Filtering ──
    # Internshala often ignores URL parameters and returns generic jobs from all over India.
    # We must explicitly filter out non-South India locations and irrelevant job titles.
    filtered_jobs = []
    
    # Define keywords based on the requested role
    role_lower = role.lower()
    valid_keywords = []
    if role_lower in ["data analyst", "data scientist", "data engineer", "ml engineer", "all"]:
        valid_keywords.extend(["data", "analyst", "analy", "science", "scientist", "machine learning", "ml", "engineer", "artificial intelligence", "ai"])
    if role_lower in ["business analyst", "all"]:
        valid_keywords.extend(["business", "ba"])
        
    for job in all_jobs:
        # 1. Strict Location Filter
        if not _is_south_india(job["location"]):
            continue
            
        # 2. Strict Title Filter (must match at least one relevant keyword)
        title_lower = job["title"].lower()
        
        # Exclude obvious junk that sneaks into data searches
        if any(junk in title_lower for junk in ["sales", "counsellor", "counselor", "business development", "bde", "bda", "marketing", "hr", "human resource"]):
            continue
            
        if valid_keywords:
            import re
            # Create a regex pattern with word boundaries for short acronyms like "ai", "ml", "ba"
            # For longer words, regular matching is fine, but regex handles both safely.
            pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in valid_keywords) + r')\b'
            # Also allow partial matches for longer keywords just in case (like 'analy' in 'analytics')
            long_kws = [kw for kw in valid_keywords if len(kw) > 3]
            
            has_match = bool(re.search(pattern, title_lower)) or any(kw in title_lower for kw in long_kws)
            if not has_match:
                continue
                
        filtered_jobs.append(job)

    # Deduplicate and sort by recency (Internshala first since fresher-focused)
    unique = _deduplicate(filtered_jobs)
    internshala = [j for j in unique if j["source"] == "Internshala"]
    indeed      = [j for j in unique if j["source"] == "Indeed"]

    logger.info('Job search for "%s": %d Indeed + %d Internshala = %d unique',
                role, len(indeed), len(internshala), len(unique))

    return internshala + indeed   # Internshala first


def _save_to_csv(jobs: list, role: str) -> str:
    """Save job results to CSV. Returns file path."""
    os.makedirs(JOB_RESULTS_DIR, exist_ok=True)
    date_str  = datetime.now().strftime("%Y-%m-%d")
    role_slug = role.replace(" ", "_")
    path      = os.path.join(JOB_RESULTS_DIR,
                              f"jobs_{role_slug}_{date_str}.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f,
            fieldnames=["title", "company", "location", "link", "source", "published"])
        writer.writeheader()
        writer.writerows(jobs)

    logger.info('Saved %d jobs to %s', len(jobs), path)
    return path


def _speak_jobs(jobs: list, start: int = 0, count: int = 5) -> str:
    """Build spoken summary for a slice of job results."""
    batch = jobs[start:start + count]
    if not batch:
        return "No more jobs to show."

    total   = len(jobs)
    showing = f"Showing jobs {start + 1} to {min(start + count, total)} of {total}. "
    lines   = []

    for i, job in enumerate(batch, start + 1):
        lines.append(
            f"Number {i}: {job['title']} at {job['company']}, {job['location']}."
        )

    result = showing + " ".join(lines)
    result += " Say next for more, open number to open a job, save to bookmark, or exit job search to stop."
    return result


# ── Session Tools ─────────────────────────────────────────────────────────────

def enter_job_search_mode(role: str = "all") -> str:
    """
    Enter job search mode. Fetch results and speak first 5.
    Sets session state for follow-up commands.
    """
    _search_session["active"]        = True
    _search_session["current_role"]  = role
    _search_session["current_index"] = 0
    _search_session["saved_jobs"]    = []

    role_label = role.title() if role != "all" else "Data Analyst and Data Science"

    jobs = _run_search(role)
    _search_session["results"]    = jobs
    _search_session["last_search"] = datetime.now()

    if not jobs:
        _search_session["active"] = False
        return (f"Could not find any {role_label} openings right now. "
                "Try again later or say open job portals to browse manually.")

    # Save to CSV silently
    csv_path = _save_to_csv(jobs, role)

    result  = f"Entering job search mode. Searching for {role_label} fresher roles in South India. "
    result += f"Found {len(jobs)} fresher openings. "
    result += _speak_jobs(jobs, 0, 5)
    result += f" Full list saved to {Path(csv_path).name}."

    # Open first job in browser
    try:
        webbrowser.open(jobs[0]["link"])
    except Exception:
        pass

    return result


def next_jobs() -> str:
    """Show next 5 jobs."""
    if not _search_session["active"] or not _search_session["results"]:
        return "No active job search. Say job search mode to start."

    _search_session["current_index"] += 5
    idx = _search_session["current_index"]

    if idx >= len(_search_session["results"]):
        _search_session["current_index"] = 0
        return "That is all the jobs I found. Starting from the beginning. " + \
               _speak_jobs(_search_session["results"], 0, 5)

    return _speak_jobs(_search_session["results"], idx, 5)


def previous_jobs() -> str:
    """Show previous 5 jobs."""
    if not _search_session["active"]:
        return "No active job search."

    _search_session["current_index"] = max(
        0, _search_session["current_index"] - 5)
    return _speak_jobs(
        _search_session["results"],
        _search_session["current_index"], 5
    )


def open_job(number: int = 1) -> str:
    """Open a specific job by number in browser."""
    if not _search_session["active"]:
        return "No active job search."

    jobs = _search_session["results"]
    idx  = number - 1

    if idx < 0 or idx >= len(jobs):
        return f"No job number {number} in current list."

    job = jobs[idx]
    webbrowser.open(job["link"])
    return f"Opening {job['title']} at {job['company']} in your browser."


def save_job(number: int = 1) -> str:
    """Bookmark a job to saved list."""
    if not _search_session["active"]:
        return "No active job search."

    jobs = _search_session["results"]
    idx  = number - 1

    if idx < 0 or idx >= len(jobs):
        return f"No job number {number} to save."

    job = jobs[idx]
    _search_session["saved_jobs"].append(job)

    # Append to saved jobs CSV
    os.makedirs(JOB_RESULTS_DIR, exist_ok=True)
    saved_path = os.path.join(JOB_RESULTS_DIR, "saved_jobs.csv")
    file_exists = os.path.exists(saved_path)

    with open(saved_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f,
            fieldnames=["title", "company", "location", "link", "source", "published"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(job)

    return f"Saved {job['title']} at {job['company']}. You have {len(_search_session['saved_jobs'])} saved jobs."


def search_role(role: str = "all") -> str:
    """Switch to a different role within job search mode."""
    return enter_job_search_mode(role)


def open_job_portals() -> str:
    """Open all major job portals for manual browsing."""
    try:
        webbrowser.open("https://internshala.com/fresher-jobs/data-science-data-analytics-jobs/")
        webbrowser.open(
            "https://in.indeed.com/q-data-analyst-fresher-jobs.html"
            "?l=South+India&sort=date"
        )
        webbrowser.open(
            "https://www.naukri.com/data-analyst-fresher-jobs-in-south-india"
        )
        return ("Opened Internshala, Indeed, and Naukri in your browser, "
                "all filtered for fresher Data roles in South India.")
    except Exception as e:
        return f"Could not open job portals: {str(e)}"


def exit_job_search() -> str:
    """Exit job search mode and return to normal ACTIVE state."""
    saved = len(_search_session["saved_jobs"])
    total = len(_search_session["results"])

    _search_session["active"]        = False
    _search_session["results"]       = []
    _search_session["current_index"] = 0

    if saved:
        return (f"Exiting job search mode. You saved {saved} jobs out of {total} found. "
                f"Check saved_jobs.csv in your job results folder.")
    return f"Exiting job search mode. Found {total} jobs total. Results saved to CSV."


def is_job_search_active() -> bool:
    """Check if job search session is currently active."""
    return _search_session["active"]


def morning_job_check() -> str:
    """
    Lightweight startup check — only speaks if new jobs found today.
    Called on startup, not on demand.
    """
    try:
        jobs = []
        for query in ["data analyst fresher", "data scientist fresher"]:
            jobs += _fetch_indeed(query=query, days=1)
        jobs = list({j["link"]: j for j in jobs}.values())  # deduplicate

        if not jobs:
            return ""  # silent — no new jobs today

        count = len(jobs)
        top = jobs[0]
        loc = top["location"].split(",")[0].strip() if top["location"] else "South India"
        return (f"By the way, {count} new Data Analyst and Data Science "
                f"fresher job openings posted today in South India. "
                f"Latest one is {top['title']} at {top['company']}, {loc}. "
                f"Say job search mode for the full list.")

    except Exception:
        return ""  # always silent on startup failure


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "enter_job_search_mode": enter_job_search_mode,
    "next_jobs":             next_jobs,
    "previous_jobs":         previous_jobs,
    "open_job":              open_job,
    "save_job":              save_job,
    "search_role":           search_role,
    "open_job_portals":      open_job_portals,
    "exit_job_search":       exit_job_search,
}
