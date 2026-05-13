import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('dna.skill.job_search_scorer')

class HybridScorer:
    def __init__(self):
        # Keyword matrices with word boundaries to prevent false positives
        self.keyword_map = {
            "High": [
                r"\bdata analyst\b", r"\bresearch analyst\b", r"\bai engineer\b",
                r"\bartificial intelligence engineer\b", r"\bml engineer\b"
            ],
            "Medium": [
                r"\bdata\b", r"\banalyst\b", r"\bfresher\b", r"\bentry level\b",
                r"\bjunior\b", r"\bscience\b", r"\bscientist\b"
            ],
            "Low": [] # Default tier
        }
        # Compile regex for efficiency
        self.patterns = {
            tier: re.compile("|".join(pats), re.IGNORECASE)
            for tier, pats in self.keyword_map.items()
        }

    def tier_jobs(self, jobs: list) -> list:
        """Ranks jobs into High, Medium, or Low tiers based on title keywords."""
        if not jobs:
            return []

        enriched_jobs = []
        for job in jobs:
            title = job.get("title", "").lower()
            if not title:
                tier = "Low"
            elif self.patterns["High"].search(title):
                tier = "High"
            elif self.patterns["Medium"].search(title):
                tier = "Medium"
            else:
                tier = "Low"

            # Create a copy to avoid mutating original data
            enriched_job = job.copy()
            enriched_job["tier"] = tier
            enriched_jobs.append(enriched_job)

        return enriched_jobs

    def filter_recency(self, jobs: list, reference_date: datetime = None) -> list:
        """
        Filters jobs based on recency.
        - Hard limit: Remove jobs > 7 days old.
        - is_new: True if posted within last 24 hours.
        """
        if not jobs:
            return []

        if reference_date is None:
            reference_date = datetime.now()

        filtered_jobs = []
        for job in jobs:
            published_str = job.get("published")
            if not published_str:
                continue

            try:
                # Support a few common formats
                date_val = None
                for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        date_val = datetime.strptime(published_str, fmt)
                        break
                    except ValueError:
                        continue

                if date_val is None:
                    logger.warning(f"Invalid date format for job: {published_str}")
                    continue

                # Future date check
                if date_val > reference_date + timedelta(days=1):
                    logger.warning(f"Future date detected for job: {published_str}")
                    continue

                # 7-day hard limit
                delta = reference_date - date_val
                if delta.days > 7:
                    continue

                # is_new flag (< 24 hours)
                job_copy = job.copy()
                job_copy["is_new"] = delta.total_seconds() < 86400
                filtered_jobs.append(job_copy)

            except Exception as e:
                logger.error(f"Error processing date {published_str}: {e}")
                continue

        return filtered_jobs
