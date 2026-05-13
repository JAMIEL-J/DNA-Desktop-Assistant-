import unittest
from datetime import datetime, timedelta
from skills.job_search_scorer import HybridScorer

class TestJobSearchScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = HybridScorer()
        self.today = datetime(2026, 5, 13).date()

    def test_tiering_logic(self):
        jobs = [
            {"title": "AI Engineer Fresher", "published": "2026-05-13"}, # High
            {"title": "Data Analyst", "published": "2026-05-13"},        # High
            {"title": "Business Analyst", "published": "2026-05-13"},    # Med
            {"title": "Random Role", "published": "2026-05-13"},         # Low
        ]
        results = self.scorer.tier_jobs(jobs)
        self.assertEqual(results[0]["tier"], "High")
        self.assertEqual(results[1]["tier"], "High")
        self.assertEqual(results[2]["tier"], "Medium")
        self.assertEqual(results[3]["tier"], "Low")

    def test_recency_filter(self):
        # Mocking current date inside the method might be needed,
        # but for this test we assume the current date is 2026-05-13 as per prompt.
        # We will pass the current date to the filter if the implementation allows,
        # or the implementation should use datetime.now().

        # Since we can't easily mock datetime.now() without monkeypatching,
        # we'll implement the scorer to accept a reference date for testing.

        jobs = [
            {"title": "Recent Job", "published": "2026-05-13"}, # New (<24h)
            {"title": "Old Job", "published": "2026-05-05"},    # > 7 days
            {"title": "Mid Job", "published": "2026-05-10"},    # 3 days ago
        ]

        # We'll use a helper to inject the date if we implement it that way
        results = self.scorer.filter_recency(jobs, reference_date=self.today)

        # "Old Job" should be removed
        self.assertEqual(len(results), 2)

        # "Recent Job" should be marked as is_new
        recent_job = next(j for j in results if j["title"] == "Recent Job")
        self.assertTrue(recent_job.get("is_new"))

        # "Mid Job" should not be is_new
        mid_job = next(j for j in results if j["title"] == "Mid Job")
        self.assertFalse(mid_job.get("is_new", False))

if __name__ == "__main__":
    unittest.main()
