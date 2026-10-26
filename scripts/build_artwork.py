"""Rebuild the approved Tabi artwork; Python standard library only."""
from pathlib import Path
from html import escape
import base64
import json
import re
import textwrap
from render_stats import PALETTES, rect, text, svg, render_all

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def paragraph(x, y, content, width, size, color, leading=None):
    lines = textwrap.wrap(content, width, break_long_words=False, break_on_hyphens=False)
    leading = leading or size * 1.5
    return "".join(text(x, round(y+i*leading, 2), line, size, color) for i, line in enumerate(lines))


def molecular_art(c, x, y, w, h):
    source = (ROOT / "scripts/molecular-template.svg").read_text(encoding="utf-8")
    for token, color in [("accent", c["accent"]), ("mint", c["mint"]), ("sky", c["sky"]),
                         ("border", c["border"]), ("muted", c["muted"])]:
        source = source.replace("var(--tb-"+token+")", color)
    return source.replace("<svg ", f'<svg x="{x}" y="{y}" width="{w}" height="{h}" ', 1)


def banner(c, mobile):
    w, h = (400, 420) if mobile else (900, 280)
    b = rect(0, 0, w, h, c["wash"], radius=12)
    b += text(28 if mobile else 36, 36, "PERCEPTION · REASONING · DISCOVERY", 11 if mobile else 13, c["accent"], mono=True)
    b += text(28 if mobile else 36, 91 if mobile else 105, "Thanh Bình.", 40 if mobile else 53, c["text"], 600)
    b += text(28 if mobile else 36, 120 if mobile else 139, "Call me Tabi.", 16, c["mint"], mono=True)
    b += paragraph(28 if mobile else 36, 158 if mobile else 184,
                   "From visual signals to biological insight.", 42, 14 if mobile else 18, c["muted"], 22)
    x, y = (28, 188) if mobile else (36, 215)
    for label, width in [("AI / Agents", 103), ("Machine Learning", 143), ("Bioinformatics", 135)]:
        if x+width > w-20:
            x, y = 28, y+31
        b += rect(x, y, width, 25, c["bg"], c["border"], 5)
        b += text(x+9, y+17, label, 12, c["text"], mono=True)
        x += width+8
    b += molecular_art(c, 155 if mobile else 610, 215 if mobile else 12, 235 if mobile else 270, 202 if mobile else 245)
    return svg(w, h, b, "Thanh Bình. Call me Tabi. AI, computer vision and bioinformatics. Conceptual molecular artwork.")


def intro(c, mobile):
    w, h = (400, 620) if mobile else (900, 295)
    pw, ph, right_x, right_y = (400, 285, 0, 305) if mobile else (438, 294, 462, 0)
    b = rect(1, 1, pw-2, ph-2, c["code"], c["border"], 9)
    b += rect(right_x+1, right_y+1, pw-2, (314 if mobile else ph)-2, c["panel"], c["border"], 9)
    code = ['const binh = {', '  alias: "Tabi",', '  focus: [', '    "AI & Computer Vision",',
            '    "ML for Biology"', '  ],', '  exploring: "Agentic AI",', '  also: "Web applications"', '};']
    for i, line in enumerate(code):
        b += text(24, 43+i*25, line, 16, c["accent"] if i == 0 else c["mint"] if '"' in line else c["text"], mono=True)
    b += paragraph(right_x+23, right_y+34, "I build across computer vision, multimodal AI and machine learning for biological data.",
                   42 if mobile else 44, 16, c["text"], 23)
    rows = [("AI & computer vision", "Perception, speech and assistive AI systems."),
            ("Bioinformatics", "Protein language models and enzyme kinetics."),
            ("Web", "Client landing pages and AI applications.")]
    for i, (label, description) in enumerate(rows):
        y = right_y+125+i*60
        b += f'<circle cx="{right_x+28}" cy="{y-5}" r="3" fill="{c["accent"]}"/>'
        b += text(right_x+43, y, label, 16, c["text"], 500)
        b += paragraph(right_x+43, y+23, description, 36, 14, c["muted"], 19)
    return svg(w, h, b, "About Tabi: AI and computer vision, machine learning for biology, agentic AI and web applications.")


PROJECTS = {
    "navisight": dict(category="MULTIMODAL AI", name="NAVISIGHT",
        description="A vision assistant for visually impaired users, combining object detection, depth estimation, voice interaction and spoken guidance.",
        tech=["PyTorch · YOLO11", "Depth Anything v2 · Whisper"], foot=["Assistive AI", "Vision × Speech"]),
    "visl": dict(category="SIGN LANGUAGE AI", name="ViSL",
        description="Vietnamese sign-language recognition using hand, face and pose landmarks with a custom PyTorch Transformer and web interface.",
        tech=["PyTorch · MediaPipe", "Transformer · FastAPI"], foot=["Accessibility", "Sequence modeling"]),
}


def project_card(c, key, mobile):
    p = PROJECTS[key]
    w, h = (400, 370) if mobile else (440, 325)
    b = rect(1, 1, w-2, h-2, c["panel"], c["border"], 10)
    b += text(24, 32, p["category"], 12, c["muted"], mono=True)
    b += text(24, 75, p["name"]+" ↗", 28, c["accent"], 600)
    b += paragraph(24, 113, p["description"], 35 if mobile else 46,
                   18 if mobile else 16, c["muted"], 25 if mobile else 23)
    for i, line in enumerate(p["tech"]):
        b += text(24, h-97+i*23, line, 15 if mobile else 14, c["text"], mono=True)
    b += f'<path d="M24 {h-51}H{w-24}" stroke="{c["border"]}"/>'
    b += text(24, h-24, p["foot"][0], 14, c["muted"])
    b += text(w-24, h-24, p["foot"][1], 14, c["muted"], anchor="end")
    return svg(w, h, b, p["name"]+": "+p["description"])


def bio(c, mobile):
    w, h = (400, 620) if mobile else (900, 330)
    b = rect(1, 1, w-2, h-2, c["panel"], c["border"], 10)
    b += f'<path d="M2 12V{h-12}" stroke="{c["mint"]}" stroke-width="3"/>'
    b += text(24, 32, "BIOINFORMATICS · MOLECULAR ML", 12, c["mint"], mono=True)
    b += text(24, 78, "K-ICM ↗", 32, c["accent"], 600)
    b += paragraph(24, 116, "Predicting enzyme turnover from protein sequences and substrate SMILES with protein and molecular language models and cross-attention fusion.",
                   37 if mobile else 47, 18 if mobile else 16, c["muted"], 25 if mobile else 23)
    b += text(24, 240 if mobile else 223, "ESM-3 · LoRA · MoLFormer-XL", 15, c["text"], mono=True)
    b += text(24, 265 if mobile else 248, "Lightning · OOD evaluation", 15, c["text"], mono=True)
    b += text(24, 300 if mobile else 299, "Explore the research code ↗", 16, c["accent"])
    x, y, bw, gap = (20, 340, 170, 20) if mobile else (485, 71, 180, 24)
    for i, (title, example, model) in enumerate([( "Protein sequence", "M A G W K …", "ESM-3 + LoRA"),
                                               ("Substrate SMILES", "CCO", "MoLFormer-XL")]):
        xx = x+i*(bw+gap)
        b += rect(xx, y, bw, 103, c["code"], c["border"], 6)
        b += text(xx+bw/2, y+28, title, 14, c["mint"], 500, "middle")
        b += text(xx+bw/2, y+54, example, 13, c["muted"], anchor="middle", mono=True)
        b += text(xx+bw/2, y+82, model, 15, c["text"], anchor="middle")
    mid = x+bw+gap/2
    b += text(mid, y+129, "↘  residue × molecule  ↙", 13, c["accent"], anchor="middle", mono=True)
    b += rect(x, y+146, bw*2+gap, 44, c["wash"], c["border"], 6)
    b += text(mid, y+174, "Cross-attention fusion", 16, c["text"], anchor="middle")
    b += text(mid, y+228, "↓  predicted log₁₀ kcat", 17, c["mint"], anchor="middle", mono=True)
    return svg(w, h, b, "K-ICM: protein sequence via ESM-3 and LoRA; substrate SMILES via MoLFormer-XL; cross-attention predicts log10 kcat.")


WEB = {
    "chichi": ("Chi Chi Chành Chành", "A cultural event landing page bringing the programme, activities and partners together.", "Events", "chichi-logo.png"),
    "ftalent": ("F-Talent 2022", "A talent competition website with judges, event schedules, galleries and registration links.", "Events", "ftalent-logo.png"),
    "kiera": ("Kiera Nguyen Beauty Care", "A beauty business website presenting services, pricing, imagery and booking contact points.", "Business", "kiera-logo.png"),
}


def web_card(c, key, mobile):
    title, description, kind, logo = WEB[key]
    w, h = (400, 410) if mobile else (280, 355)
    b = rect(1, 1, w-2, h-2, c["panel"], c["border"], 10)
    b += rect(2, 2, w-4, 120 if mobile else 110, c["code"], radius=9)
    path = ASSETS / logo
    if path.exists():
        encoded = base64.b64encode(path.read_bytes()).decode()
        b += f'<image x="24" y="14" width="{w-48}" height="88" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/png;base64,{encoded}"/>'
    else:
        b += paragraph(22, 58, title, 22, 20, c["accent"])
    b += paragraph(22, 155 if mobile else 146, title, 25 if mobile else 21, 26 if mobile else 22, c["text"], 31 if mobile else 28)
    b += paragraph(22, 230 if mobile else 214, description, 33 if mobile else 30, 19 if mobile else 14, c["muted"], 26 if mobile else 20)
    b += text(22, h-49, kind+" · HTML / CSS / JS", 14 if mobile else 11, c["muted"], mono=True)
    b += text(22, h-20, "View repository ↗", 16 if mobile else 14, c["accent"])
    return svg(w, h, b, title+": "+description)


def snake_fallback(sample, c):
    # A truthful static calendar remains usable before the first scheduled animation.
    w, h = 900, 160
    b = rect(1, 1, w-2, h-2, c["panel"], c["border"], 9)
    counts = {d["date"]: d["level"] for d in sample["activeDays"]}
    from datetime import date, timedelta
    start = date.fromisoformat(sample["periodStart"])
    start -= timedelta(days=(start.weekday()+1)%7)
    end = date.fromisoformat(sample["periodEnd"])
    cols = (end-start).days//7+1
    step = 856/cols
    colors = [c["code"], "#44405d" if c["bg"] == "#0d1117" else "#e6ddfb", c["sky"], c["mint"], c["accent"]]
    for i in range((end-start).days+1):
        stamp = (start+timedelta(days=i)).isoformat()
        b += rect(round(22+(i//7)*step,2), round(22+(i%7)*step,2), round(step-3,2), round(step-3,2), colors[counts.get(stamp,0)], radius=2)
    return svg(w, h, b, "Contribution calendar. The scheduled workflow generates the animated snake.")


def main():
    ASSETS.mkdir(exist_ok=True)
    for theme, c in PALETTES.items():
        for mobile in (False, True):
            suffix = "-mobile" if mobile else ""
            items = {"banner": banner(c,mobile), "intro":intro(c,mobile), "bio":bio(c,mobile)}
            items.update({name:project_card(c,name,mobile) for name in PROJECTS})
            items.update({name:web_card(c,name,mobile) for name in WEB})
            for name, content in items.items():
                (ASSETS/f"{name}{suffix}-{theme}.svg").write_text(content,encoding="utf-8")
    sample = json.loads((ROOT/"data/activity.json").read_text(encoding="utf-8"))
    render_all(sample, ASSETS)
    for theme,c in PALETTES.items():
        path = ASSETS/f"snake-{theme}.svg"
        if not path.exists():
            path.write_text(snake_fallback(sample,c),encoding="utf-8")
    print("Built responsive light/dark profile artwork.")


if __name__ == "__main__":
    main()
