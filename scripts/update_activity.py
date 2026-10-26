"""Refresh publicly visible GitHub metrics without a personal access token."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import tempfile
import urllib.request
from render_stats import render_all, validate_snapshot

QUERY = """query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    repositories(privacy:PUBLIC,ownerAffiliations:[OWNER]){totalCount}
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions totalIssueContributions totalPullRequestContributions
      totalPullRequestReviewContributions totalRepositoryContributions
      contributionCalendar{totalContributions weeks{contributionDays{
        date contributionCount contributionLevel
      }}}
    }
  }
}"""


def fetch_snapshot(token, username):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(days=365)
    stamp = lambda d: d.isoformat().replace("+00:00", "Z")
    payload = json.dumps({"query": QUERY, "variables": {"login": username, "from": stamp(start), "to": stamp(now)}}).encode()
    request = urllib.request.Request("https://api.github.com/graphql", data=payload,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "Tabi-Profile"})
    with urllib.request.urlopen(request, timeout=45) as response:
        body = json.load(response)
    if body.get("errors") or not body.get("data", {}).get("user"):
        raise RuntimeError("GitHub did not return a complete public activity snapshot; previous files are unchanged.")
    user = body["data"]["user"]
    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    levels = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    days = [{"date": d["date"], "count": d["contributionCount"], "level": levels[d["contributionLevel"]]}
            for week in calendar["weeks"] for d in week["contributionDays"]
            if start.date().isoformat() <= d["date"] <= now.date().isoformat()]
    sample = {
        "asOf": now.date().isoformat(), "periodStart": min(d["date"] for d in days),
        "periodEnd": max(d["date"] for d in days), "publicRepositories": user["repositories"]["totalCount"],
        "totalContributions": calendar["totalContributions"], "commits": collection["totalCommitContributions"],
        "pullRequests": collection["totalPullRequestContributions"], "issues": collection["totalIssueContributions"],
        "reviews": collection["totalPullRequestReviewContributions"], "repositoriesCreated": collection["totalRepositoryContributions"],
        "source": "https://github.com/" + username, "activeDays": days,
    }
    validate_snapshot(sample)
    return sample


def refresh(root, token, username, fetcher=fetch_snapshot):
    root = Path(root)
    sample = fetcher(token, username)
    validate_snapshot(sample)
    # Generate and validate every new asset before replacing any existing file.
    with tempfile.TemporaryDirectory(dir=root) as temp:
        staged = Path(temp)
        render_all(sample, staged)
        (staged / "activity.json").write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")
        (root / "assets").mkdir(exist_ok=True)
        (root / "data").mkdir(exist_ok=True)
        for item in staged.glob("*.svg"):
            os.replace(item, root / "assets" / item.name)
        os.replace(staged / "activity.json", root / "data/activity.json")
    print("Updated publicly visible activity as of " + sample["asOf"])


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("No GITHUB_TOKEN. Run the Profile assets workflow on GitHub; no personal token is needed.")
    refresh(root, token, os.environ.get("PROFILE_USERNAME", "ThanhBinh-IwtR"))
