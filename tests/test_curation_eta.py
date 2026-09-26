import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from resource_research_agent.curation_eta import estimate_curation
from resource_research_agent.scout_progress import build_scout_progress


class CurationEtaTests(unittest.TestCase):
    def setUp(self):
        self.job = {"id": 1, "status": "in-progress", "progress": {"completed": 0, "total": 1},
                    "categories": [{"categoryId": "housing", "candidateCount": 120, "status": "assigned"}]}
        self.events = []
        self.now = datetime(2026, 9, 26, tzinfo=timezone.utc)
        self.batch(1, 30, 600)
        self.batch(2, 10, 300)

    def batch(self, number, count, seconds):
        self.events.append({"phase": "codex-curation-batch-started", "categoryId": "housing",
                            "createdAt": self.now.isoformat(), "details": {"batch": number, "candidateCount": count}})
        self.now += timedelta(seconds=seconds)
        self.events.append({"phase": "codex-curation-batch-completed", "categoryId": "housing",
                            "createdAt": self.now.isoformat(), "details": {"batch": number}})

    def test_weighted_pace_remaining_candidates_and_units(self):
        eta = estimate_curation(self.job, self.events)
        self.assertEqual(80, eta["remainingCandidates"])
        self.assertEqual("Done in 24 - 39 minutes", eta["label"])
        self.job["categories"].append({"categoryId": "food", "candidateCount": 280, "status": "pending"})
        self.assertEqual("Done in 1 - 3 hours", estimate_curation(self.job, self.events)["label"])

    def test_replayed_checkpoints_and_heartbeats_do_not_change_estimate(self):
        before = estimate_curation(self.job, self.events)
        replay = deepcopy(self.events)
        for event in replay:
            event["createdAt"] = (self.now + timedelta(hours=3)).isoformat()
        replay += [{"phase": "codex-curation-active", "categoryId": "housing", "details": {"batch": 3, "elapsedSeconds": 1200}}]
        self.assertEqual(before, estimate_curation(self.job, self.events + replay))
        self.batch(3, 30, 1200)
        after = estimate_curation(self.job, self.events)
        self.assertEqual(50, after["remainingCandidates"])
        self.assertNotEqual(before["updatedAt"], after["updatedAt"])

    def test_no_estimate_for_insufficient_timing_or_finished_work(self):
        self.assertIsNone(estimate_curation(self.job, self.events[:2]))
        invalid = deepcopy(self.events)
        invalid[0]["createdAt"] = "not a date"
        self.assertIsNone(estimate_curation(self.job, invalid))
        self.job["categories"][0]["status"] = "completed"
        self.assertIsNone(estimate_curation(self.job, self.events))
        self.job["status"] = "completed"
        self.assertIsNone(estimate_curation(self.job, self.events))

    def test_recent_slowdown_widens_range(self):
        self.job["categories"][0]["candidateCount"] = 1800
        for number in range(3, 16):
            self.batch(number, 30, 300)
        before = estimate_curation(self.job, self.events)
        for number in range(16, 28):
            self.batch(number, 30, 1200)
        after = estimate_curation(self.job, self.events)
        # Less work remains, but the recent pace is four times slower.
        self.assertGreater(after["upperSeconds"], before["upperSeconds"])

    def test_progress_appends_eta_but_hides_it_when_stopped(self):
        store = Mock()
        store.import_summary.return_value = {"officeName": "Mesa", "categories": [{"id": "housing", "label": "Housing"}]}
        store.list_runs.return_value = []
        store.list_scout_curation_jobs.return_value = [self.job]
        store.list_scout_curation_progress.return_value = self.events
        store.list_scout_workflow_progress.return_value = []
        store.list_focused_research_jobs.return_value = []
        store.latest_chatgpt_assignment_schedule.return_value = None
        self.events[-1]["message"] = "Completed Housing batch 2/4"
        progress = build_scout_progress(store, 1)
        self.assertEqual("Completed Housing batch 2/4, Done in 24 - 39 minutes.", progress["message"])
        self.events.append({"phase": "codex-curation-stopped", "message": "Needs correction", "createdAt": self.now.isoformat()})
        progress = build_scout_progress(store, 1)
        self.assertEqual("Needs correction", progress["message"])
        self.assertIsNone(progress["curation"]["estimate"])
