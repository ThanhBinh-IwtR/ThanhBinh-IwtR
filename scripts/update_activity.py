"""Write public GitHub activity into README.md, assets/activity.svg and assets/fields.svg.

Standard library only. Only the block between the activity markers is generated; the rest of the
README is edited by hand. Needs a token (the Actions token is enough) to read GitHub's GraphQL API.
"""
from datetime import date, timedelta
from pathlib import Path
import json
import os
import tempfile
import urllib.request
from fields import field_shares, fields_svg

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- activity:start -->", "<!-- activity:end -->"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
ACTIVITY, FIELDS = "assets/activity.svg", "assets/fields.svg"
# Same mid-tone tokens and left gutter as assets/hero.svg, so the track reads in both themes.
TRACK_STYLE = """<style>
  svg { --violet: #8b74d0; --slate: #768390; }
  text { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 11px; fill: var(--slate); }
  .name { font-size: 12px; text-anchor: end; }
  .axis { fill: none; stroke: var(--slate); stroke-opacity: .5; }
  .day { fill: var(--violet); }
</style>"""
SNAKE = "assets/snake-light.svg"
SNAKE_PICTURE = """<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/snake-dark.svg">
  <img src="assets/snake-light.svg" width="100%" alt="A snake eating the cells of the public GitHub contribution calendar">
</picture>"""
ID_QUERY = "query($login:String!){user(login:$login){id}}"
QUERY = """query($login:String!,$id:ID!){
  user(login:$login){
    repositories(first:100,privacy:PUBLIC,ownerAffiliations:[OWNER],orderBy:{field:PUSHED_AT,direction:DESC}){
      totalCount
      nodes{
        name isFork description
        repositoryTopics(first:20){nodes{topic{name}}}
        languages(first:5,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}
        readme:object(expression:"HEAD:README.md"){...on Blob{text}}
        readmeLower:object(expression:"HEAD:readme.md"){...on Blob{text}}
        defaultBranchRef{target{...on Commit{history(first:100,author:{id:$id}){totalCount nodes{committedDate}}}}}
      }
    }
    contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{date contributionCount}}
    }}
  }
}"""


def graphql(token, query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request("https://api.github.com/graphql", data=payload,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "Tabi-Profile"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def fetch_profile(token, username):
    """Calendar, repositories and my commits in each; commits are matched to my account id."""
    user = (graphql(token, ID_QUERY, {"login": username}).get("data") or {}).get("user")
    if not user:
        raise RuntimeError("GitHub did not return the account id; README is unchanged.")
    return graphql(token, QUERY, {"login": username, "id": user["id"]})


def read_snapshot(body):
    """Check a GraphQL response and keep what the README shows: repos, total and daily counts."""
    user = (body.get("data") or {}).get("user")
    if body.get("errors") or not user:
        raise RuntimeError("GitHub did not return a complete contribution calendar; README is unchanged.")
    calendar = user["contributionsCollection"]["contributionCalendar"]
    days = sorted((date.fromisoformat(d["date"]), d["contributionCount"])
                  for week in calendar["weeks"] for d in week["contributionDays"])
    if not days:
        raise ValueError("Empty contribution calendar")
    for (previous, _), (stamp, _) in zip(days, days[1:]):
        if stamp - previous != timedelta(days=1):
            raise ValueError("Calendar days must be consecutive and unique")
    if any(type(count) is not int or count < 0 for _, count in days):
        raise ValueError("Invalid contribution count")
    if sum(count for _, count in days) != calendar["totalContributions"]:
        raise ValueError("Calendar total does not match contribution total")
    return {"publicRepositories": user["repositories"]["totalCount"], "repositories": user["repositories"]["nodes"],
            "totalContributions": calendar["totalContributions"], "days": days}


def streaks(days):
    """Current and longest run of active days; today still counts until it ends."""
    active = {stamp for stamp, count in days if count}
    today = days[-1][0]
    cursor = today if today in active else today - timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    previous = None
    for stamp in sorted(active):
        run = run + 1 if previous is not None and stamp - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = stamp
    return current, longest


def day_label(stamp):
    return f"{stamp.day} {MONTHS[stamp.month-1]} {stamp.year}"


def summary(snapshot):
    days = snapshot["days"]
    peak_day, peak = max(days, key=lambda d: (d[1], d[0]))
    text = (f'Contributions per day from {day_label(days[0][0])} to {day_label(days[-1][0])}: '
            f'{snapshot["totalContributions"]} in total')
    return text + (f", most on {day_label(peak_day)} ({peak})." if peak else ".")


def activity_svg(snapshot):
    """A coverage track with one bar per day, lined up under the rows of assets/hero.svg."""
    days = snapshot["days"]
    left, width, base = 132, 728, 76
    x = lambda i: left + (i + .5) * width / len(days)
    peak_day, peak = max(days, key=lambda d: (d[1], d[0]))
    bars = "".join(f"M{x(i) - 2:.1f} {base}v{-8 - 48 * count / peak:.1f}h4V{base}z"
                   for i, (_, count) in enumerate(days) if count)
    ticks, labels = f"M{left} {base}H{left + width}", []
    for i, (stamp, _) in enumerate(days):
        if stamp.day == 1:
            ticks += f"M{x(i):.1f} {base}v5"
            labels.append(f'<text x="{x(i):.1f}" y="{base + 19}">{MONTHS[stamp.month-1]}</text>')
            if stamp.month == 1 or len(labels) == 1:
                labels.append(f'<text x="{x(i):.1f}" y="{base + 33}">{stamp.year}</text>')
    if peak:
        at = min(max(x(days.index((peak_day, peak))), left + 40), left + width - 40)
        labels.append(f'<text x="{at:.1f}" y="11" text-anchor="middle">{peak} on {peak_day.day} {MONTHS[peak_day.month-1]}</text>')
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 116" width="880" height="116" role="img" aria-labelledby="title">',
        f'<title id="title">{summary(snapshot)}</title>', TRACK_STYLE,
        f'<text class="name" x="{left - 12}" y="{base}">contributions</text>',
        f'<path class="axis" d="{ticks}"/>', f'<path class="day" d="{bars}"/>', *labels, "</svg>", ""])


def render(snapshot, username, snake=False):
    """The generated block; the snake is shown once the workflow has drawn it."""
    current, longest = streaks(snapshot["days"])
    active = sum(1 for _, count in snapshot["days"] if count)
    days = lambda n: f"{n} day" + ("" if n == 1 else "s")
    return "\n".join([
        "<!-- Generated by scripts/update_activity.py; edits inside this block are overwritten. -->",
        "",
        "| Contributions | Active days | Current streak | Longest streak | Public repos |",
        "| :---: | :---: | :---: | :---: | :---: |",
        f'| **{snapshot["totalContributions"]}** | {active} | {days(current)} | {days(longest)} | {snapshot["publicRepositories"]} |',
        "",
        f'<img src="{ACTIVITY}" width="100%" alt="{summary(snapshot)}">',
        "",
        f'<sub>The last 12 months on the public contribution calendar of <a href="https://github.com/{username}">{username}</a>, '
        "checked daily by GitHub Actions.</sub>",
        *(["", SNAKE_PICTURE] if snake else []),
    ])


def splice(readme, block):
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) > readme.index(END):
        raise ValueError(f"README.md needs exactly one {START} ... {END} block")
    head, rest = readme.split(START)
    return head + START + "\n" + block + "\n" + END + rest.split(END, 1)[1]


def write_if_changed(path, text):
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    # Write beside the target and swap it in, so a crash never leaves half a file.
    path.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as temp:
        temp.write(text)
    os.replace(temp.name, path)
    return True


def refresh(readme_path, token, username, fetcher=fetch_profile):
    readme_path = Path(readme_path)
    root = readme_path.parent
    snapshot = read_snapshot(fetcher(token, username))
    readme = splice(readme_path.read_text(encoding="utf-8"), render(snapshot, username, (root / SNAKE).is_file()))
    shares = field_shares(snapshot["repositories"], snapshot["days"][-1][0], username)
    changed = write_if_changed(root / ACTIVITY, activity_svg(snapshot))
    changed = write_if_changed(root / FIELDS, fields_svg(shares)) or changed
    changed = write_if_changed(readme_path, readme) or changed
    if not changed:
        print("README activity is already current.")
        return
    print(f'Updated README activity: {snapshot["totalContributions"]} contributions in the last year.')


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("No GITHUB_TOKEN. Run the Profile activity workflow, or export a token to run locally.")
    refresh(ROOT / "README.md", token, os.environ.get("PROFILE_USERNAME", "ThanhBinh-IwtR"))
