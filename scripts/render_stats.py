"""Render self-contained, light/dark profile statistics. Standard library only."""
from datetime import date, timedelta
from html import escape
from pathlib import Path
import json
import xml.etree.ElementTree as ET

PALETTES = {
    "dark": dict(bg="#0d1117", panel="#151b25", code="#111721", text="#e5eaf2",
                 muted="#a5b1c5", border="#2c3545", accent="#c4b5fd", mint="#a9dfcf", sky="#b6d8f2", wash="#211f32"),
    "light": dict(bg="#ffffff", panel="#f6f8fa", code="#f1f4f8", text="#202938",
                  muted="#59677b", border="#d8dee8", accent="#6e58ab", mint="#2b776a", sky="#467ba4", wash="#f5f0ff"),
}


def text(x, y, value, size=16, color="#e5eaf2", weight=400, anchor="start", mono=False):
    family = "Consolas,monospace" if mono else "Segoe UI,Arial,sans-serif"
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{escape(str(value))}</text>')


def rect(x, y, w, h, fill, stroke="none", radius=8):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def svg(width, height, body, title):
    result = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
              f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
              f'aria-labelledby="title"><title id="title">{escape(title)}</title>{body}</svg>')
    ET.fromstring(result)
    return result


def validate_snapshot(sample):
    start, end = date.fromisoformat(sample["periodStart"]), date.fromisoformat(sample["periodEnd"])
    date.fromisoformat(sample["asOf"])
    if end < start or (end - start).days > 366:
        raise ValueError("Invalid contribution period")
    seen, total = set(), 0
    for day in sample["activeDays"]:
        stamp = date.fromisoformat(day["date"])
        count, level = day["count"], day["level"]
        if stamp in seen or not start <= stamp <= end:
            raise ValueError("Duplicate or out-of-range contribution day")
        if type(count) is not int or count < 0 or type(level) is not int or not 0 <= level <= 4:
            raise ValueError("Invalid contribution value")
        seen.add(stamp)
        total += count
    if total != sample["totalContributions"]:
        raise ValueError("Calendar total does not match contribution total")
    for field in ("publicRepositories", "commits", "pullRequests", "issues", "reviews", "repositoriesCreated"):
        if type(sample[field]) is not int or sample[field] < 0:
            raise ValueError("Invalid metric: " + field)


def streaks(days, as_of):
    today = date.fromisoformat(as_of)
    active = {date.fromisoformat(d["date"]) for d in days if d["count"] > 0 and d["date"] <= as_of}
    current, cursor = 0, today if today in active else today - timedelta(days=1)
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


def activity_mix(sample):
    counts = [sample.get(k, 0) for k in ("commits", "reviews", "pullRequests", "issues")]
    total = sum(counts)
    return [n / total for n in counts] if total else [0, 0, 0, 0]


def activity_svg(sample, theme="dark", mobile=False):
    validate_snapshot(sample)
    c = PALETTES[theme]
    w, h = (400, 660) if mobile else (900, 515)
    body = rect(1, 1, w-2, h-2, c["panel"], c["border"], 12)
    current, longest = streaks(sample["activeDays"], sample["asOf"])
    labels = ["Public repos", "Current streak", "Best in period"]
    values = [sample["publicRepositories"], current, longest]
    for i, (label, value) in enumerate(zip(labels, values)):
        x = 22 + i * (w-44) / 3
        body += text(x, 33, label, 13 if mobile else 15, c["muted"])
        body += text(x, 70, value, 30 if mobile else 36, c["accent"], 600)
    body += text(22, 103, f'{sample["totalContributions"]} contributions in the last year', 14 if mobile else 17, c["text"], 500)
    start, end = date.fromisoformat(sample["periodStart"]), date.fromisoformat(sample["periodEnd"])
    start -= timedelta(days=(start.weekday()+1) % 7)
    cols = ((end - start).days // 7) + 1
    step = (w-44) / cols
    size = max(2, step - (2 if mobile else 3))
    active = {d["date"]: d for d in sample["activeDays"]}
    colors = [c["code"], "#44405d" if theme == "dark" else "#e6ddfb",
              "#71638f" if theme == "dark" else "#c9b9ed", c["mint"], c["accent"]]
    month = None
    for i in range((end-start).days+1):
        stamp = start + timedelta(days=i)
        col, row = i//7, i%7
        x, y = 22 + col*step, 139 + row*step
        day = active.get(stamp.isoformat(), {"level": 0, "count": 0})
        body += rect(round(x, 2), round(y, 2), round(size, 2), round(size, 2), colors[day["level"]], radius=1.5)
        if row == 0 and stamp.month != month:
            month = stamp.month
            if not mobile or col % 8 < 4:
                body += text(round(x, 2), 128, stamp.strftime("%b"), 10 if mobile else 12, c["muted"])
    chart_top = 215 if mobile else 280
    body += text(22, chart_top, "Activity overview", 18, c["text"], 500)
    fractions = activity_mix(sample)
    code_total = sum(sample[k] for k in ("commits", "reviews", "pullRequests", "issues"))
    body += text(22, chart_top+28, f'{sample["commits"]} commits · {sample["pullRequests"]} pull requests', 14, c["muted"])
    body += text(22, chart_top+50, f'{sample["issues"]} issues · {sample["reviews"]} code reviews', 14, c["muted"])
    note = f'{sample["repositoriesCreated"]} repositories created, excluded from this mix.'
    if mobile:
        body += text(22, chart_top+77, f'{sample["repositoriesCreated"]} repositories created separately.', 12, c["muted"])
    else:
        body += text(22, chart_top+81, note, 13, c["muted"])
    cx, cy, radius = (200, 470, 78) if mobile else (695, 365, 83)
    body += f'<path d="M{cx-radius} {cy}H{cx+radius}M{cx} {cy-radius}V{cy+radius}" fill="none" stroke="{c["border"]}"/>'
    points = [(cx-radius*fractions[0], cy), (cx, cy-radius*fractions[1]),
              (cx+radius*fractions[3], cy), (cx, cy+radius*fractions[2])]
    body += f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x,y in points)}" fill="{c["mint"]}" fill-opacity=".2" stroke="{c["mint"]}" stroke-width="1.6"/>'
    for x,y in points:
        body += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{c["mint"]}"/>'
    for label, fraction, x, y, anchor in [
        ("Commits", fractions[0], cx-radius-14, cy-12, "end"),
        ("Code review", fractions[1], cx, cy-radius-29, "middle"),
        ("Issues", fractions[3], cx+radius+14, cy-12, "start"),
        ("Pull requests", fractions[2], cx, cy+radius+27, "middle")]:
        body += text(x, y, f'{fraction:.0%}', 14, c["text"], 500, anchor)
        body += text(x, y+17, label, 12, c["muted"], anchor=anchor)
    foot = h-42
    body += text(22, foot, "Publicly visible GitHub activity", 12, c["muted"])
    body += text(22, foot+20, f'Snapshot: {sample["asOf"]} · {code_total} code contributions', 12, c["muted"])
    return svg(w, h, body, f'GitHub activity: {sample["totalContributions"]} contributions. Snapshot {sample["asOf"]}.')


def render_all(sample, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for theme in PALETTES:
        for mobile in (False, True):
            suffix = "-mobile" if mobile else ""
            (destination / f"activity{suffix}-{theme}.svg").write_text(activity_svg(sample, theme, mobile), encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    render_all(json.loads((root / "data/activity.json").read_text(encoding="utf-8")), root / "assets")
