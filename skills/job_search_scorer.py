import re
import logging
from datetime import datetime, timedelta
from skills.career_ops_skill import career_ops_evaluate

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

    def select_for_deep_dive(self, jobs: list) -> list:
        """Returns up to 20 jobs from the High tier for LLM evaluation."""
        high_tier = [j for j in jobs if j.get("tier") == "High"]
        return high_tier[:20]

    def run_deep_dive(self, jobs: list) -> list:
        """
        Performs LLM evaluation on selected jobs using career_ops_evaluate.
        Extracts Score, Archetype, and Insight from the report.
        """
        if not jobs:
            return []

        results = []
        for job in jobs:
            link = job.get("link")
            if not link:
                logger.warning(f"Job missing link for deep dive: {job.get('title', 'Unknown')}")
                results.append(job)
                continue

            try:
                # Pass link as JD text (career_ops_evaluate expects text, but may handle URLs if the node script does)
                # Note: Requirements said 'career_ops_evaluate(link)', so we follow that.
                report = career_ops_evaluate(link)

                # Parse Score (e.g., "Score: 4.5/5")
                score_match = re.search(r'Score: ([\d\.]+)/5', report)
                # Parse Archetype (e.g., "Archetype: Strategic AI")
                archetype_match = re.search(r'Archetype: ([^|]*)', report)
                if archetype_match:
                    archetype = archetype_match.group(1).strip()
                    # Split by period or comma to remove legitimacy if it's in the same line
                    archetype = re.split(r'\. | ,', archetype)[0].strip()
                else:
                    archetype = "N/A"

                # Parse Insight (the "Full Report" part)
                insight_match = re.search(r'Full Report:\n([\s\S]*)', report)

                job_copy = job.copy()
                job_copy["llm_score"] = score_match.group(1) if score_match else "N/A"
                job_copy["llm_archetype"] = archetype
                job_copy["llm_insight"] = insight_match.group(1).strip() if insight_match else "N/A"

                results.append(job_copy)
            except Exception as e:
                logger.error(f"Error during deep dive for {link}: {e}")
                results.append(job)

        return results
