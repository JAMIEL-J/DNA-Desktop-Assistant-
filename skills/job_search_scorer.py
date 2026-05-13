import datetime

class HybridScorer:
    def __init__(self):
        self.high_tier_keywords = ["ai engineer", "research analyst", "data analyst"]
        self.medium_tier_keywords = ["data", "fresher", "analyst"]

    def tier_jobs(self, jobs):
        """
        Ranks jobs into High, Medium, and Low tiers based on title keywords.
        """
        results = []
        for job in jobs:
            title = job.get("title", "").lower()

            # High Tier Check
            if any(kw in title for kw in self.high_tier_keywords):
                tier = "High"
            # Medium Tier Check
            elif any(kw in title for kw in self.medium_tier_keywords):
                tier = "Medium"
            else:
                tier = "Low"

            # Create a copy to avoid modifying original data
            job_copy = job.copy()
            job_copy["tier"] = tier
            results.append(job_copy)

        return results

    def filter_recency(self, jobs, reference_date=None):
        """
        Removes jobs older than 7 days and marks jobs within 24 hours as 'is_new'.
        """
        if reference_date is None:
            reference_date = datetime.date.today()

        filtered_jobs = []
        for job in jobs:
            published_str = job.get("published", "")
            try:
                published_date = datetime.datetime.strptime(published_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                # If date is missing or invalid, we skip the job
                continue

            delta = reference_date - published_date

            # Hard limit: Remove jobs > 7 days old
            if delta.days > 7:
                continue

            # Negative delta (future date) is kept but not marked as new
            if delta.days < 0:
                # Handle future dates as current for simplicity, or just keep them
                is_new = False
            else:
                # "is_new" flag: posted within last 24 hours (delta.days == 0)
                is_new = (delta.days == 0)

            job_copy = job.copy()
            job_copy["is_new"] = is_new
            filtered_jobs.append(job_copy)

        return filtered_jobs
