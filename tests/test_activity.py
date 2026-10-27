import copy
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def calendar_body(first, counts, repos=26):
    """A GraphQL-shaped response with one calendar day per count, starting at `first`."""
    start = date.fromisoformat(first)
    days = [{"date": (start + timedelta(days=i)).isoformat(), "contributionCount": n} for i, n in enumerate(counts)]
    weeks = [{"contributionDays": days[i:i+7]} for i in range(0, len(days), 7)]
    return {"data": {"user": {"repositories": {"totalCount": repos}, "contributionsCollection": {
        "contributionCalendar": {"totalContributions": sum(counts), "weeks": weeks}}}}}


BODY = calendar_body("2026-09-28", [0, 1, 2, 0, 0, 0, 0] + [0] * 7 + [3, 4, 0, 0, 0, 0, 0] + [0] * 7 + [0, 0, 5, 0, 0])
README = "# Hello\n\n## Learning in public\n\n<!-- activity:start -->\nold\n<!-- activity:end -->\n\nHand-written footer.\n"


class ActivityTests(unittest.TestCase):
    def test_streak_survives_until_end_of_today(self):
        from update_activity import streaks
        days = [(date(2026, 10, 23), 1), (date(2026, 10, 24), 1), (date(2026, 10, 25), 1)]
        self.assertEqual(streaks(days + [(date(2026, 10, 26), 0)]), (3, 3))
        self.assertEqual(streaks(days + [(date(2026, 10, 26), 0), (date(2026, 10, 27), 0)]), (0, 3))

    def test_longest_streak_is_the_best_run_in_the_calendar(self):
        from update_activity import read_snapshot, streaks
        self.assertEqual(streaks(read_snapshot(BODY)["days"]), (0, 2))

    def test_monthly_totals_keep_partial_months_and_their_year(self):
        from update_activity import monthly, read_snapshot
        self.assertEqual(monthly(read_snapshot(BODY)["days"]), [("Sep 2026", 3), ("Oct 2026", 12)])

    def test_bars_scale_to_the_busiest_month(self):
        from update_activity import bar
        self.assertEqual(bar(0, 7), "·")
        self.assertEqual(bar(7, 7, width=4), "████")
        self.assertEqual(bar(1, 8, width=4), "▌")

    def test_render_is_plain_markdown_with_real_numbers(self):
        from update_activity import read_snapshot, render
        block = render(read_snapshot(BODY), "ThanhBinh-IwtR")
        self.assertIn("| **15** | 5 | 0 days | 2 days | 26 |", block)
        self.assertIn("Oct 2026   12  ████████████████████████", block)
        self.assertNotIn("<img", block)

    def test_splice_rewrites_only_the_generated_block(self):
        from update_activity import splice
        result = splice(README, "new")
        self.assertIn("<!-- activity:start -->\nnew\n<!-- activity:end -->", result)
        self.assertTrue(result.startswith("# Hello\n") and result.endswith("Hand-written footer.\n"))
        with self.assertRaises(ValueError):
            splice("# No markers\n", "new")

    def test_mismatched_daily_total_is_rejected(self):
        from update_activity import read_snapshot
        invalid = copy.deepcopy(BODY)
        invalid["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"] += 1
        with self.assertRaises(ValueError):
            read_snapshot(invalid)

    def test_duplicate_or_missing_calendar_day_is_rejected(self):
        from update_activity import read_snapshot
        for change in (lambda days: days.append(dict(days[0])), lambda days: days.pop(3)):
            invalid = copy.deepcopy(BODY)
            calendar = invalid["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            change(calendar["weeks"][0]["contributionDays"])
            calendar["totalContributions"] = sum(d["contributionCount"] for w in calendar["weeks"] for d in w["contributionDays"])
            with self.assertRaises(ValueError):
                read_snapshot(invalid)

    def test_graphql_error_is_reported(self):
        from update_activity import read_snapshot
        with self.assertRaises(RuntimeError):
            read_snapshot({"errors": [{"message": "rate limited"}], "data": None})

    def test_refresh_writes_block_and_failed_fetch_keeps_readme(self):
        from update_activity import refresh
        with tempfile.TemporaryDirectory() as temp:
            readme = Path(temp) / "README.md"
            readme.write_text(README, encoding="utf-8")

            def fail(*_args):
                raise RuntimeError("network unavailable")
            with self.assertRaises(RuntimeError):
                refresh(readme, "not-a-real-token", "ThanhBinh-IwtR", fetcher=fail)
            self.assertEqual(readme.read_text(encoding="utf-8"), README)

            refresh(readme, "not-a-real-token", "ThanhBinh-IwtR", fetcher=lambda *_args: BODY)
            updated = readme.read_text(encoding="utf-8")
            self.assertIn("| **15** |", updated)
            self.assertTrue(updated.endswith("Hand-written footer.\n"))

    def test_snake_appears_only_after_the_workflow_draws_it(self):
        from update_activity import refresh
        with tempfile.TemporaryDirectory() as temp:
            readme = Path(temp) / "README.md"
            readme.write_text(README, encoding="utf-8")
            refresh(readme, "not-a-real-token", "ThanhBinh-IwtR", fetcher=lambda *_args: BODY)
            self.assertNotIn("snake-light.svg", readme.read_text(encoding="utf-8"))
            (Path(temp) / "assets").mkdir()
            (Path(temp) / "assets/snake-light.svg").write_text("<svg/>", encoding="utf-8")
            refresh(readme, "not-a-real-token", "ThanhBinh-IwtR", fetcher=lambda *_args: BODY)
            self.assertIn('srcset="assets/snake-dark.svg"', readme.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
