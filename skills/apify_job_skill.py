# skills/apify_job_skill.py
"""
DNA Apify Job Search Skill — Direct SDK Calls via apify-client

OBSERVED CU MATH: misceres/indeed-scraper consumed ~0.003 CU per run (2 items in ~9.5 sec).
- 50 calls/day ≈ 0.15 CU/day ≈ 4.5 CU/month (~$0.90 compute credit).
- APIFY_DAILY_LIMIT=50 safely keeps usage well within Apify's $5.00/month free tier credit.
DO NOT add browser/Puppeteer actors without auditing observed CU consumption.
"""

import logging
import time
from config import APIFY_API_KEY, APIFY_DAILY_LIMIT
from core.usage_tracker import check_daily_limit, log_usage

logger = logging.getLogger('dna.skill.apify_job')

# Top-level safe import for static analyzers & runtime
try:
    from apify_client import ApifyClient
    HAS_APIFY = True
except ImportError:
    ApifyClient = None
    HAS_APIFY = False


def scrape_jobs(query: str, location: str = "India", max_items: int = 20, dry_run: bool = False) -> list[dict]:
    """
    Direct SDK call via apify-client.
    Caps max_items explicitly, checks daily usage limit, logs to SQLite.
    Fails loud on breach or error without crashing the voice session.
    """
    # 1. Enforce hard max_items cap
    max_items = min(max_items, 20)

    # 2. Check daily limit
    allowed, current_count = check_daily_limit("apify", APIFY_DAILY_LIMIT)
    if not allowed:
        error_msg = f"Apify daily limit reached ({current_count}/{APIFY_DAILY_LIMIT} runs today). Scrape aborted to protect API credits."
        logger.error(error_msg)
        print(f"[VOICE SPOKEN ERROR]: {error_msg}")
        return []

    # 3. Dry Run return path (for zero-credit isolated testing)
    if dry_run:
        logger.info("[DRY RUN] Simulating Apify scrape for query='%s' location='%s'", query, location)
        log_usage("apify", f"dry_run_scrape:{query}", 2)
        return [
            {
                "title": f"Junior {query.title()}",
                "company": "TechCorp India",
                "location": f"Bangalore, {location}",
                "link": "https://example.com/job/101",
                "published": "2026-07-27T10:00:00"
            },
            {
                "title": f"Entry Level {query.title()}",
                "company": "DataSys Solutions",
                "location": f"Chennai, {location}",
                "link": "https://example.com/job/102",
                "published": "2026-07-27T09:30:00"
            }
        ]

    # 4. Direct SDK execution checks
    if not APIFY_API_KEY:
        error_msg = "APIFY_API_KEY not configured in environment. Skipping Apify scrape."
        logger.error(error_msg)
        print(f"[VOICE SPOKEN ERROR]: {error_msg}")
        return []

    if not HAS_APIFY or ApifyClient is None:
        error_msg = "apify-client package is not installed. Install with: pip install apify-client"
        logger.error(error_msg)
        print(f"[VOICE SPOKEN ERROR]: {error_msg}")
        return []

    try:
        client = ApifyClient(APIFY_API_KEY)

        logger.info("Executing memo23/naukri-scraper actor query='%s' max_items=%d", query, max_items)
        run_input = {
            "searchKeyword": query,
            "location": location,
            "maxItems": max_items
        }

        try:
            run = client.actor("memo23/naukri-scraper").call(run_input=run_input)
        except Exception as actor_err:
            logger.warning("memo23/naukri-scraper failed (%s), falling back to apify/rag-web-browser", actor_err)
            rag_input = {"query": f"{query} jobs in {location} site:naukri.com", "maxResults": max_items}
            run = client.actor("apify/rag-web-browser").call(run_input=rag_input)

        dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.get("defaultDatasetId") if hasattr(run, "get") else getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))
        if not dataset_id and hasattr(run, "__dict__"):
            dataset_id = run.__dict__.get("default_dataset_id") or run.__dict__.get("defaultDatasetId")

        dataset_items = list(client.dataset(dataset_id).iterate_items())

        results = []
        for item in dataset_items:
            title = item.get("title", item.get("positionName", item.get("jobTitle", "")))
            company = item.get("companyName", item.get("company", "Unknown"))
            loc = item.get("location", item.get("place", location))
            pub = item.get("postedAt", item.get("postDate", ""))

            # Construct canonical desktop Naukri URL
            basic = item.get("basicInfo", {})
            jd_url = item.get("jdURL") or basic.get("jdURL", "")
            job_id = item.get("jobId") or basic.get("jobId", "")
            raw_url = item.get("url", basic.get("url", ""))

            if jd_url:
                if jd_url.startswith("http"):
                    link = jd_url
                elif jd_url.startswith("/"):
                    link = f"https://www.naukri.com{jd_url}"
                else:
                    link = f"https://www.naukri.com/{jd_url}"
            elif job_id:
                link = f"https://www.naukri.com/job-listings-{job_id}"
            elif raw_url and "naukri.com" in raw_url:
                link = raw_url
            else:
                link = raw_url or item.get("externalApplyLink", "")

            if title and link:
                results.append({
                    "title": str(title).strip(),
                    "company": str(company).strip(),
                    "location": str(loc).strip(),
                    "link": str(link).strip(),
                    "published": str(pub).strip()
                })

        log_usage("apify", f"naukri_scraper:{query}", len(results))
        return results

    except Exception as e:
        logger.error("Apify actor execution failed: %s", e, exc_info=True)
        print(f"[VOICE SPOKEN ERROR]: Apify job scrape encountered an error: {str(e)}")
        return []
