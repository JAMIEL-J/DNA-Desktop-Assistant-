import unittest
from datetime import datetime, timedelta
from skills.job_search_scorer import HybridScorer

class TestJobSearchScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = HybridScorer()
        self.today = datetime(2026, 5, 13)

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

    def test_tiering_edge_cases(self):
        # Empty list
        self.assertEqual(self.scorer.tier_jobs([]), [])

        # Missing title
        jobs = [{"published": "2026-05-13"}]
        results = self.scorer.tier_jobs(jobs)
        self.assertEqual(results[0]["tier"], "Low")

        # Empty title
        jobs = [{"title": "", "published": "2026-05-13"}]
        results = self.scorer.tier_jobs(jobs)
        self.assertEqual(results[0]["tier"], "Low")

    def test_recency_filter(self):
        jobs = [
            {"title": "Recent Job", "published": "2026-05-13"}, # New (<24h)
            {"title": "Old Job", "published": "2026-05-05"},    # > 7 days
            {"title": "Mid Job", "published": "2026-05-10"},    # 3 days ago
        ]

        results = self.scorer.filter_recency(jobs, reference_date=self.today)

        # "Old Job" should be removed
        self.assertEqual(len(results), 2)

        # "Recent Job" should be marked as is_new
        recent_job = next(j for j in results if j["title"] == "Recent Job")
        self.assertTrue(recent_job.get("is_new"))

        # "Mid Job" should not be is_new
        mid_job = next(j for j in results if j["title"] == "Mid Job")
        self.assertFalse(mid_job.get("is_new", False))

    def test_recency_edge_cases(self):
        # Empty list
        self.assertEqual(self.scorer.filter_recency([], reference_date=self.today), [])

        # Missing published date
        jobs = [{"title": "Missing Date"}]
        self.assertEqual(self.scorer.filter_recency(jobs, reference_date=self.today), [])

        # Invalid date format
        jobs = [{"title": "Invalid Date", "published": "not-a-date"}]
        self.assertEqual(self.scorer.filter_recency(jobs, reference_date=self.today), [])

        # Future date
        jobs = [{"title": "Future Job", "published": "2026-05-20"}]
        self.assertEqual(self.scorer.filter_recency(jobs, reference_date=self.today), [])

    def test_select_for_deep_dive(self):
        # Create 25 High tier jobs, 5 Medium, 5 Low
        jobs = []
        for i in range(25):
            jobs.append({"title": "AI Engineer", "tier": "High", "id": i})
        for i in range(25, 30):
            jobs.append({"title": "Business Analyst", "tier": "Medium", "id": i})
        for i in range(30, 35):
            jobs.append({"title": "Random", "tier": "Low", "id": i})

        selected = self.scorer.select_for_deep_dive(jobs)
        self.assertEqual(len(selected), 20)
        self.assertTrue(all(j["tier"] == "High" for j in selected))

    def test_run_deep_dive(self):
        from unittest.mock import patch

        # Mock career_ops_evaluate to return a controlled string
        # The expected format from career_ops_skill.py is:
        # "Evaluation complete. Score: 4.2/5. Archetype: High Growth. Legitimacy: Verified.\n\nFull Report:\n..."
        mock_output = "Evaluation complete. Score: 4.5/5. Archetype: Strategic AI. Legitimacy: High.\n\nFull Report:\nDetailed insight here."

        with patch('skills.job_search_scorer.career_ops_evaluate', return_value=mock_output) as mock_eval:
            jobs = [
                {"title": "AI Engineer", "tier": "High", "link": "http://job1.com"},
                {"title": "ML Engineer", "tier": "High", "link": "http://job2.com"},
            ]

            results = self.scorer.run_deep_dive(jobs)

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["llm_score"], "4.5")
            self.assertEqual(results[0]["llm_archetype"], "Strategic AI")
            self.assertEqual(results[0]["llm_insight"], "Detailed insight here.")
            self.assertEqual(mock_eval.call_count, 2)

if __name__ == "__main__":
    unittest.main()
