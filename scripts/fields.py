"""Estimate which fields my commits go to and draw assets/fields.svg. Standard library only.

Each public repository is sorted into fields by its GitHub topics; without matching topics, by the
words in its name, description and README; failing that, by its main language. Its commits are then
shared between those fields, and recent commits count more: a commit loses half its weight each year.
"""
from datetime import date
from html import escape
import math
import re

HALF_LIFE_DAYS = 365
# Keywords are matched as whole words, after lowercasing and turning punctuation into spaces.
FIELDS = {
    "Computer vision": ("computer vision", "vision", "sign language", "fingerspelling", "object detection", "yolo",
                        "opencv", "mediapipe", "pose estimation", "depth estimation", "segmentation", "ocr"),
    "Bioinformatics": ("bioinformatics", "protein", "enzyme", "enzyme kinetics", "kcat", "molecular", "cheminformatics",
                       "smiles", "drug discovery", "genomics", "computational biology"),
    "NLP and speech": ("nlp", "llm", "rag", "speech", "speech recognition", "chatbot", "language model", "whisper", "tts"),
    "Agentic AI": ("agentic", "agents", "ai agent", "ai agents", "mcp", "langchain", "langgraph"),
    "Web": ("web", "website", "landing page", "frontend", "react", "nextjs", "html", "css", "javascript", "typescript"),
    "Data science": ("data science", "machine learning", "data analysis", "data mining", "statistics", "pandas", "kaggle"),
}
LANGUAGES = {"HTML": "Web", "CSS": "Web", "SCSS": "Web", "JavaScript": "Web", "TypeScript": "Web", "Vue": "Web",
             "PHP": "Web", "Jupyter Notebook": "Data science", "Python": "Data science", "R": "Data science"}
STYLE = """<style>
  svg { --violet: #8b74d0; --mint: #3f9c8a; --slate: #768390; }
  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; }
  .grid { fill: none; stroke: var(--slate); stroke-opacity: .28; }
  .share { fill: var(--violet); fill-opacity: .2; stroke: var(--violet); stroke-width: 2; stroke-linejoin: round; }
  .point { fill: var(--mint); }
  .name { fill: var(--slate); font-size: 12px; }
  .value { fill: var(--violet); font-size: 13px; font-weight: 600; }
</style>"""


def words(text):
    return " " + re.sub(r"[^a-z0-9]+", " ", (text or "").lower()) + " "


def hits(text):
    return {field: sum(text.count(f" {keyword} ") for keyword in keywords) for field, keywords in FIELDS.items()}


def classify(repo):
    """Share of a repository that belongs to each field; empty when nothing tells."""
    topics = words(" , ".join(node["topic"]["name"] for node in repo["repositoryTopics"]["nodes"]))
    readme = repo.get("readme") or repo.get("readmeLower") or {}
    for text in (topics, words(" , ".join([repo["name"], repo.get("description") or "", readme.get("text") or ""]))):
        found = {field: n for field, n in hits(text).items() if n}
        if found:
            return {field: n / sum(found.values()) for field, n in found.items()}
    languages = sorted(repo["languages"]["edges"], key=lambda edge: -edge["size"])
    field = LANGUAGES.get(languages[0]["node"]["name"]) if languages else None
    return {field: 1.0} if field else {}


def commit_weight(repo, today):
    """Commits I authored on the default branch, each worth half as much per year of age."""
    history = ((repo.get("defaultBranchRef") or {}).get("target") or {}).get("history")
    if not history:
        return 0.0
    ages = [(today - date.fromisoformat(node["committedDate"][:10])).days for node in history["nodes"]]
    weight = sum(.5 ** (age / HALF_LIFE_DAYS) for age in ages)
    # Only the newest commits come back with dates; older ones count at the oldest date seen.
    return weight + (history["totalCount"] - len(ages)) * .5 ** (max(ages, default=0) / HALF_LIFE_DAYS)


def field_shares(repositories, today, owner):
    totals = dict.fromkeys(FIELDS, 0.0)
    for repo in repositories:
        if repo["isFork"] or repo["name"].lower() == owner.lower():
            continue
        weight = commit_weight(repo, today)
        for field, share in classify(repo).items():
            totals[field] += weight * share
    total = sum(totals.values())
    return {field: value / total if total else 0.0 for field, value in totals.items()}


def percent(share):
    return "<1%" if 0 < share < .005 else f"{share:.0%}"


def fields_svg(shares):
    """A radar with one axis per field; the radius grows with the square root of the share."""
    cx, cy, radius = 220, 184, 108
    peak = max(shares.values())
    axes = [(field, math.radians(-90 + 60 * i)) for i, field in enumerate(FIELDS)]
    at = lambda r, a: (cx + r * math.cos(a), cy + r * math.sin(a))
    ring = lambda r: "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in (at(r, a) for _, a in axes)) + "Z"
    grid = "".join(ring(radius * k / 4) for k in range(1, 5)) + "".join(
        f"M{cx} {cy}L{x:.1f} {y:.1f}" for x, y in (at(radius, a) for _, a in axes))
    points = [at(radius * math.sqrt(shares[field] / peak) if peak else 0, a) for field, a in axes]
    body = [f'<path class="grid" d="{grid}"/>',
            '<path class="share" d="M' + "L".join(f"{x:.1f} {y:.1f}" for x, y in points) + 'Z"/>',
            *(f'<circle class="point" cx="{x:.1f}" cy="{y:.1f}" r="3.5"/>' for x, y in points)]
    for field, a in axes:
        x, y = at(radius + 18, a)
        anchor = "start" if math.cos(a) > .3 else "end" if math.cos(a) < -.3 else "middle"
        name_y, value_y = (y - 16, y) if math.sin(a) < -.9 else (y + 10, y + 26) if math.sin(a) > .9 else (y - 3, y + 13)
        body.append(f'<text class="name" x="{x:.1f}" y="{name_y:.1f}" text-anchor="{anchor}">{escape(field)}</text>')
        body.append(f'<text class="value" x="{x:.1f}" y="{value_y:.1f}" text-anchor="{anchor}">{escape(percent(shares[field]))}</text>')
    title = "Share of my recent commits by field: " + ", ".join(f"{field} {percent(share)}" for field, share in shares.items()) + "."
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 360" width="440" height="360" role="img" aria-labelledby="title">',
        f'<title id="title">{escape(title)}</title>', STYLE, *body, "</svg>", ""])
