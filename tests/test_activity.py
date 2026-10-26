import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SAMPLE = {
    "asOf": "2026-10-26", "periodStart": "2025-10-26", "periodEnd": "2026-10-26",
    "publicRepositories": 25, "totalContributions": 7, "commits": 5, "pullRequests": 2,
    "issues": 0, "reviews": 0, "repositoriesCreated": 0,
    "activeDays": [{"date": "2026-03-31", "count": 4, "level": 3},
                   {"date": "2026-04-01", "count": 1, "level": 1},
                   {"date": "2026-04-02", "count": 2, "level": 2}],
}


class ActivityTests(unittest.TestCase):
    def test_streak_survives_until_end_of_today(self):
        from render_stats import streaks
        days = [{"date": d, "count": 1} for d in ("2026-10-23", "2026-10-24", "2026-10-25")]
        self.assertEqual(streaks(days, "2026-10-26"), (3, 3))
        self.assertEqual(streaks(days, "2026-10-27"), (0, 3))

    def test_snapshot_has_three_day_best_streak(self):
        from render_stats import streaks
        sample = copy.deepcopy(SAMPLE)
        self.assertEqual(streaks(sample["activeDays"], sample["asOf"]), (0, 3))

    def test_code_mix_excludes_repository_creation(self):
        from render_stats import activity_mix
        self.assertEqual(activity_mix({"commits": 12, "pullRequests": 6, "issues": 0, "reviews": 0,
                                      "repositoriesCreated": 3}), [2 / 3, 0, 1 / 3, 0])
        self.assertEqual(activity_mix({}), [0, 0, 0, 0])

    def test_mismatched_daily_total_is_rejected(self):
        from render_stats import validate_snapshot
        sample = copy.deepcopy(SAMPLE)
        validate_snapshot(sample)
        invalid = copy.deepcopy(sample)
        invalid["totalContributions"] += 1
        with self.assertRaises(ValueError):
            validate_snapshot(invalid)

    def test_duplicate_calendar_day_is_rejected(self):
        from render_stats import validate_snapshot
        sample = copy.deepcopy(SAMPLE)
        sample["activeDays"].append(sample["activeDays"][0])
        with self.assertRaises(ValueError):
            validate_snapshot(sample)

    def test_failed_fetch_does_not_replace_good_files(self):
        from update_activity import refresh
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            (root / "assets").mkdir()
            data = root / "data/activity.json"
            art = root / "assets/activity-dark.svg"
            data.write_text("previous-good-data", encoding="utf-8")
            art.write_text("previous-good-art", encoding="utf-8")
            def fail(*_args, **_kwargs):
                raise RuntimeError("network unavailable")
            with self.assertRaises(RuntimeError):
                refresh(root, "not-a-real-token", "ThanhBinh-IwtR", fetcher=fail)
            self.assertEqual(data.read_text(encoding="utf-8"), "previous-good-data")
            self.assertEqual(art.read_text(encoding="utf-8"), "previous-good-art")


if __name__ == "__main__":
    unittest.main()
