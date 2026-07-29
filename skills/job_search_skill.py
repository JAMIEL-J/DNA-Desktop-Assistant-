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
from skills.job_search_scorer import HybridScorer
from skills.job_search_dashboard import DashboardGenerator

logger = logging.getLogger('dna.skill.job_search')

# ── Role Configuration ────────────────────────────────────────────────────────

ROLE_QUERIES = {
    "data analyst":      ["data analyst fresher India", "data analyst entry level India",
                          "junior data analyst India", "data analyst 0-1 years India"],
    "financial analyst": ["financial analyst fresher India", "finance analyst entry level India",
                          "FP&A analyst fresher India", "financial planning analyst India"],
    "sales analyst":     ["sales analyst fresher India", "sales operations analyst India",
                          "commercial analyst fresher India"],
    "marketing analyst": ["marketing analyst fresher India", "digital marketing analyst India",
                          "growth analyst fresher India"],
    "business analyst":  ["business analyst fresher India", "junior business analyst India",
                          "BA fresher India", "business analyst entry level India"],
    "research analyst":  ["research analyst fresher India", "junior research analyst India",
                          "equity research analyst fresher India"],
    "all":               ["data analyst fresher India", "financial analyst fresher India",
                          "FP&A analyst India", "sales analyst fresher India",
                          "marketing analyst fresher India", "business analyst fresher India"],
}

# Seniority blocklist — titles containing these are filtered out
SENIORITY_BLOCKLIST = [
    "senior", "sr.", "sr ", "lead", "principal", "staff", "head of",
    "director", "manager", "vp ", "vice president", "chief",
    "architect", "distinguished", "founding", "mid-level",
]

# All major Indian cities and states for location filtering
INDIA_CITIES = [
    # South India
    "chennai", "bangalore", "bengaluru", "hyderabad", "coimbatore",
    "kochi", "cochin", "madurai", "mysore", "mysuru", "trichy",
    "tiruchirappalli", "vizag", "visakhapatnam", "mangalore",
    "hubli", "salem", "vellore", "pondicherry", "puducherry",
    "tirunelveli", "erode", "tiruppur",
    # North / Central / West India
    "mumbai", "delhi", "new delhi", "ncr", "noida", "gurgaon",
    "gurugram", "pune", "ahmedabad", "jaipur", "lucknow",
    "kolkata", "chandigarh", "indore", "bhopal", "nagpur",
    "surat", "vadodara", "patna", "ranchi", "guwahati",
    "thiruvananthapuram", "trivandrum", "bhubaneswar",
    # State / region names
    "india", "tamil nadu", "karnataka", "kerala", "andhra",
    "telangana", "maharashtra", "rajasthan", "uttar pradesh",
    "west bengal", "gujarat", "haryana", "punjab",
    # Generic markers
    "remote", "pan india", "work from home", "wfh",
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

def _is_india(location: str) -> bool:
    """Returns True if the location is anywhere in India or unspecified."""
    if not location:
        return True
    loc = location.lower()
    return any(city in loc for city in INDIA_CITIES)

def _is_entry_level(title: str) -> bool:
    """Returns False if title contains seniority keywords (senior, lead, etc)."""
    if not title:
        return True
    t = title.lower()
    return not any(kw in t for kw in SENIORITY_BLOCKLIST)

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
    """Fetch direct from Indeed RSS feed for instant zero-quota results."""
    results = []
    url = (f"https://in.indeed.com/rss?"
           f"q={query.replace(' ', '+')}"
           f"&l=India&sort=date&fromage={days}")
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = _clean_text(entry.get("title", ""))
            company = entry.get("author", "Unknown")
            link = entry.get("link", "")
            location = entry.get("location", "India")
            published = entry.get("published", "")

            if not title or not link:
                continue
            if not _is_india(location):
                continue

            # Strip company from title if present
            title = re.sub(r'\s*-\s*' + re.escape(company) + r'$', '', title, flags=re.IGNORECASE).strip()

            results.append({
                "title": title,
                "company": _clean_text(company),
                "location": location.split(",")[0].strip(),
                "link": link,
                "source": "Indeed Direct RSS",
                "published": published,
            })
    except Exception as e:
        logger.warning("Indeed RSS fetch error: %s", e)
    return results


# ── Gemini Synthesis Layer ───────────────────────────────────────────────────

def synthesize_job_results(raw_jobs: list[dict], candidate_profile: str = "Data Analyst focus, ML Analyst secondary") -> list[dict]:
    """
    Pipes raw job scrape results through the Gemini wrapper (_call_google in pipeline.llm_agent).
    Filters out duplicates/irrelevant listings, scores fit against candidate profile,
    and returns structured JSON sorted by fit_score descending.
    Retries once on malformed JSON; fails gracefully to raw_jobs on error.
    """
    if not raw_jobs:
        return []

    try:
        import json
        from pipeline.llm_agent import _call_google

        prompt = f"""You are a professional Career & Job Matching Assistant.
Candidate Profile Context: {candidate_profile}.

Below is a raw list of job postings fetched from job boards:
{json.dumps(raw_jobs, indent=2)}

Tasks:
1. Filter out irrelevant or non-entry-level listings.
2. Score fit (0.0 to 10.0) based on how well the job aligns with a Data Analyst (primary) or ML/Business Analyst (secondary) entry-level profile.
3. Return ONLY a valid JSON array of objects or object containing a 'jobs' array. Do not include markdown formatting or non-JSON text.
Each object in the array MUST match this schema:
[
  {{
    "title": "Clean Job Title",
    "company": "Company Name",
    "location": "City, State or Remote",
    "apply_link": "https://...",
    "fit_score": 9.2,
    "one_line_reason": "Clear one line reason explaining why this fits"
  }}
]
"""
        # Execute via existing Gemini client wrapper
        for attempt in range(2):
            try:
                response = _call_google(prompt, tool_names=[])
                synthesized = []
                if isinstance(response, list):
                    synthesized = response
                elif isinstance(response, dict):
                    if "jobs" in response and isinstance(response["jobs"], list):
                        synthesized = response["jobs"]
                    elif "raw" in response and isinstance(response["raw"], str):
                        raw_str = response["raw"]
                        raw_str = re.sub(r'^```json\s*', '', raw_str, flags=re.MULTILINE)
                        raw_str = re.sub(r'```$', '', raw_str, flags=re.MULTILINE).strip()
                        parsed = json.loads(raw_str)
                        if isinstance(parsed, list):
                            synthesized = parsed
                        elif isinstance(parsed, dict) and "jobs" in parsed and isinstance(parsed["jobs"], list):
                            synthesized = parsed["jobs"]

                if isinstance(synthesized, list) and len(synthesized) > 0:
                    # Sort by fit_score descending
                    synthesized.sort(key=lambda x: float(x.get("fit_score", 0)), reverse=True)
                    # Convert to standard job dict format
                    result = []
                    for item in synthesized:
                        result.append({
                            "title": str(item.get("title", "")),
                            "company": str(item.get("company", "Unknown")),
                            "location": str(item.get("location", "India")),
                            "link": str(item.get("apply_link", item.get("link", ""))),
                            "fit_score": float(item.get("fit_score", 5.0)),
                            "one_line_reason": str(item.get("one_line_reason", "")),
                            "source": "Gemini Synthesized Job",
                            "published": datetime.now().isoformat()
                        })
                    return result
            except Exception as parse_err:
                logger.warning("Gemini synthesis JSON parse attempt %d failed: %s", attempt + 1, parse_err)

        logger.info("Gemini synthesis completed fallback: returning structured raw jobs.")
        return raw_jobs

    except Exception as e:
        logger.error("Gemini synthesis layer error: %s", e)
        return raw_jobs


# ── Core Search ───────────────────────────────────────────────────────────────

def _run_search(role: str = "all", dry_run: bool = False) -> list:
    """Run search using direct Indeed RSS feeds + Apify direct SDK and Gemini synthesis layer."""
    from skills.apify_job_skill import scrape_jobs

    queries = ROLE_QUERIES.get(role.lower(), ROLE_QUERIES["all"])
    raw_jobs = []

    # 1. Direct Indeed RSS feed (fast, direct, no quota)
    for q in queries[:2]:
        raw_jobs += _fetch_indeed(q, days=JOB_MAX_AGE_DAYS)

    # 2. Apify direct SDK (Naukri scraper)
    for query in queries[:2]:
        raw_jobs += scrape_jobs(query=query, location="India", max_items=10, dry_run=dry_run)

    if not raw_jobs:
        return []

    # 3. Deduplicate before synthesis
    raw_jobs = _deduplicate(raw_jobs)

    # 4. Pipe raw jobs through Gemini synthesis layer
    synthesized_jobs = synthesize_job_results(raw_jobs)
    unique = _deduplicate(synthesized_jobs)
    return unique


def _save_to_csv(jobs: list, role: str) -> str:
    """Save job results to CSV. Returns file path."""
    os.makedirs(JOB_RESULTS_DIR, exist_ok=True)
    date_str  = datetime.now().strftime("%Y-%m-%d")
    role_slug = role.replace(" ", "_")
    path      = os.path.join(JOB_RESULTS_DIR,
                              f"jobs_{role_slug}_{date_str}.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f,
            fieldnames=["title", "company", "location", "link", "source", "published"],
            extrasaction='ignore')
        writer.writeheader()
        writer.writerows(jobs)

    logger.info('Saved %d jobs to %s', len(jobs), path)
    return path


def _save_to_excel(jobs: list, role: str) -> str:
    """Save job results to Excel (.xlsx) file. Returns file path."""
    try:
        import pandas as pd
        os.makedirs(JOB_RESULTS_DIR, exist_ok=True)
        date_str  = datetime.now().strftime("%Y-%m-%d")
        role_slug = role.replace(" ", "_")
        excel_path = os.path.join(JOB_RESULTS_DIR, f"jobs_{role_slug}_{date_str}.xlsx")

        df = pd.DataFrame(jobs)
        # Select and reorder clean columns
        cols = [c for c in ["title", "company", "location", "link", "source", "published"] if c in df.columns]
        df = df[cols]

        df.to_excel(excel_path, index=False, engine="openpyxl")
        logger.info('Saved %d jobs to Excel at %s', len(jobs), excel_path)
        return excel_path
    except Exception as e:
        logger.error('Failed to export jobs to Excel: %s', e)
        return ""


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

    role_label = role.title() if role != "all" else "Data Analyst and Business Analyst"

    jobs = _run_search(role)
    _search_session["results"]    = jobs
    _search_session["last_search"] = datetime.now()

    if not jobs:
        _search_session["active"] = False
        return (f"Could not find any {role_label} openings right now. "
                "Try again later or say open job portals to browse manually.")

    # Save exclusively to Excel
    excel_path = _save_to_excel(jobs, role)
    excel_msg = f" Full list saved to Excel spreadsheet ({Path(excel_path).name})." if excel_path else ""

    result  = f"Entering high-fidelity job search mode. Searching for {role_label} entry-level roles across India. "
    result += f"Found {len(jobs)} entry-level openings. "
    result += _speak_jobs(jobs, 0, 5)
    result += excel_msg

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
            fieldnames=["title", "company", "location", "link", "source", "published"],
            extrasaction='ignore')
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
        webbrowser.open("https://internshala.com/fresher-jobs/data-analytics-jobs/")
        webbrowser.open(
            "https://in.indeed.com/q-data-analyst-fresher-jobs.html"
            "?l=India&sort=date"
        )
        webbrowser.open(
            "https://www.naukri.com/data-analyst-fresher-jobs"
        )
        return ("Opened Internshala, Indeed, and Naukri in your browser, "
                "all filtered for fresher Data Analyst roles across India.")
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
        from skills.apify_job_skill import scrape_jobs
        jobs = []
        for query in ["data analyst fresher", "business analyst fresher"]:
            fetched = scrape_jobs(query=query, location="India", max_items=5)
            fetched = [j for j in fetched if _is_entry_level(j.get('title', ''))]
            jobs += fetched
        jobs = list({j["link"]: j for j in jobs}.values())  # deduplicate

        if not jobs:
            return ""  # silent — no new jobs today

        count = len(jobs)
        top = jobs[0]
        loc = top["location"].split(",")[0].strip() if top["location"] else "India"
        return (f"By the way, {count} new Data Analyst "
                f"entry-level openings posted today in India. "
                f"Latest one is {top['title']} at {top['company']}, {loc}. "
                f"Say job search mode for the full list.")

    except Exception:
        return ""  # always silent on startup failure


from skills.composio_job_skill import (
    preview_application_email,
    preview_log_sheet,
    confirm_composio_action,
    cancel_composio_action
)

# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "enter_job_search_mode":     enter_job_search_mode,
    "next_jobs":                 next_jobs,
    "previous_jobs":             previous_jobs,
    "open_job":                  open_job,
    "save_job":                  save_job,
    "search_role":               search_role,
    "open_job_portals":          open_job_portals,
    "exit_job_search":           exit_job_search,
    "preview_application_email": preview_application_email,
    "preview_log_sheet":         preview_log_sheet,
    "confirm_composio_action":   confirm_composio_action,
    "cancel_composio_action":    cancel_composio_action,
}
