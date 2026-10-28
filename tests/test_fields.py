import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
TODAY = date(2026, 10, 29)


def repo(name, topics=(), description=None, readme=None, language=None, commit_days=(), fork=False, total=None):
    """A repository node shaped like the GraphQL response; commit_days are ages in days."""
    dates = [{"committedDate": (TODAY - timedelta(days=age)).isoformat() + "T00:00:00Z"} for age in commit_days]
    return {"name": name, "isFork": fork, "description": description,
            "repositoryTopics": {"nodes": [{"topic": {"name": t}} for t in topics]},
            "languages": {"edges": [{"size": 100, "node": {"name": language}}] if language else []},
            "readme": {"text": readme} if readme is not None else None, "readmeLower": None,
            "defaultBranchRef": {"target": {"history": {"totalCount": len(dates) if total is None else total, "nodes": dates}}}}


class FieldTests(unittest.TestCase):
    def test_topics_win_over_readme_words(self):
        from fields import classify
        self.assertEqual(classify(repo("demo", topics=["computer-vision"], readme="A website in HTML and CSS")),
                         {"Computer vision": 1.0})

    def test_readme_words_classify_a_repository_without_topics(self):
        from fields import classify
        self.assertEqual(classify(repo("K-ICM", readme="Predict enzyme kcat from protein sequence and SMILES.", language="Python")),
                         {"Bioinformatics": 1.0})

    def test_sign_language_is_vision_not_nlp(self):
        from fields import classify
        self.assertEqual(classify(repo("SIGN_LANGUAGE", language="Jupyter Notebook")), {"Computer vision": 1.0})

    def test_main_language_is_the_last_resort(self):
        from fields import classify
        self.assertEqual(classify(repo("kierabeauty", language="CSS")), {"Web": 1.0})
        self.assertEqual(classify(repo("TalkShow")), {})

    def test_commits_lose_half_their_weight_each_year(self):
        from fields import commit_weight
        self.assertAlmostEqual(commit_weight(repo("a", commit_days=(0, 0, 365)), TODAY), 2.5)
        # Commits beyond the dated ones count at the oldest date seen.
        self.assertAlmostEqual(commit_weight(repo("a", commit_days=(365,), total=3), TODAY), 1.5)

    def test_shares_skip_forks_and_the_profile_repository(self):
        from fields import field_shares
        shares = field_shares([repo("ViSL", topics=["sign-language"], commit_days=(0, 0, 0)),
                               repo("site", language="HTML", commit_days=(0,)),
                               repo("someone-else", topics=["bioinformatics"], commit_days=(0,) * 9, fork=True),
                               repo("ThanhBinh-IwtR", language="HTML", commit_days=(0,) * 9)], TODAY, "ThanhBinh-IwtR")
        self.assertAlmostEqual(shares["Computer vision"], .75)
        self.assertAlmostEqual(shares["Web"], .25)
        self.assertEqual(shares["Bioinformatics"], 0)

    def test_radar_names_every_field_with_its_share(self):
        from fields import FIELDS, fields_svg
        shares = dict.fromkeys(FIELDS, 0.0) | {"Computer vision": .5, "Web": .496, "Agentic AI": .004}
        root = ET.fromstring(fields_svg(shares))
        labels = [node.text for node in root.iter() if node.tag.endswith("text")]
        self.assertTrue(set(FIELDS) <= set(labels))
        self.assertIn("50%", labels)
        self.assertIn("<1%", labels)

    def test_radar_without_any_commits_is_still_valid(self):
        from fields import FIELDS, fields_svg
        ET.fromstring(fields_svg(dict.fromkeys(FIELDS, 0.0)))


if __name__ == "__main__":
    unittest.main()
