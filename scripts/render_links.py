#!/usr/bin/env python3
"""
Render one row per entry in data/links.json into assets/links/<id>.svg. The
README stacks them vertically, each wrapped in its own link, and they slide in
one after another.

Rows are drawn at 2x and shown at half size in the README.

    python scripts/render_links.py
"""
import base64
import json
import os

from theme import CYAN, FONT, FRAME, INK, MUTED, PANEL, REDUCED_MOTION, esc, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "links.json")
OUT_DIR = os.path.join(ROOT, "assets", "links")

W, H = 840, 100
ICON = 60
ICON_X = 20
LABEL_X = ICON_X + ICON + 24
STAGGER = 0.15

CSS = (
    "@keyframes slide{from{opacity:0;transform:translateX(-16px)}to{opacity:1;transform:none}}"
    ".r{opacity:0;animation:slide .5s cubic-bezier(.2,.8,.2,1) both}"
)


def bondingai_icon(x, y, size):
    with open(os.path.join(ROOT, "source", "bondingai.png"), "rb") as f:
        data = base64.b64encode(f.read()).decode()
    inset = size * 0.18
    return (f'<image x="{x + inset}" y="{y + inset}" width="{size - inset * 2}" height="{size - inset * 2}" '
            f'href="data:image/png;base64,{data}"/>')


def linkedin_icon(x, y, size):
    s = size * 0.5 / 24
    return (f'<g transform="translate({x + size * 0.25} {y + size * 0.25}) scale({s})"><path fill="#fff" '
            'd="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1s2.48 1.12 2.48 2.5zM.22 8h4.56v14H.22zM8.34 '
            '8h4.37v1.92h.06c.61-1.15 2.1-2.37 4.32-2.37 4.62 0 5.47 3.04 5.47 7V22h-4.56v-6.6c0-1.58-.03-3.6-2.2-3.6-2.2 '
            '0-2.53 1.72-2.53 3.49V22H8.34z"/></g>')


def devpost_icon(x, y, size):
    cx, cy, r = x + size / 2, y + size / 2, size * 0.32
    hexagon = " ".join(f"{cx + r * dx:.1f},{cy + r * dy:.1f}"
                       for dx, dy in [(-0.5, -0.866), (0.5, -0.866), (1, 0), (0.5, 0.866), (-0.5, 0.866), (-1, 0)])
    return (f'<polygon points="{hexagon}" fill="none" stroke="#fff" stroke-width="3.5" stroke-linejoin="round"/>'
            f'<text x="{cx}" y="{cy + size * 0.13}" fill="#fff" font-size="{size * 0.36:.0f}" font-weight="700" '
            f'text-anchor="middle" font-family="{FONT}">D</text>')


def email_icon(x, y, size):
    left, top, w, h = x + size * 0.2, y + size * 0.28, size * 0.6, size * 0.44
    return (f'<rect x="{left}" y="{top}" width="{w}" height="{h}" rx="4" fill="none" stroke="#fff" stroke-width="3.5"/>'
            f'<polyline points="{left + 2},{top + 3} {x + size / 2},{top + h * 0.58} {left + w - 2},{top + 3}" '
            f'fill="none" stroke="#fff" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>')


ICONS = {"bondingai": bondingai_icon, "linkedin": linkedin_icon, "devpost": devpost_icon, "email": email_icon}


def row(link, index):
    icon_y = (H - ICON) / 2
    delay = index * STAGGER
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
        f"<style>{CSS}{REDUCED_MOTION}</style>",
        f'<g class="r" style="animation-delay:{delay:.2f}s">',
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{PANEL}" stroke="{FRAME}" stroke-width="2"/>',
        f'<rect x="{ICON_X}" y="{icon_y}" width="{ICON}" height="{ICON}" rx="14" fill="{link["color"]}" '
        f'stroke="{FRAME}" stroke-width="2"/>',
        ICONS[link["icon"]](ICON_X, icon_y, ICON),
        f'<text x="{LABEL_X}" y="{H / 2 + 11}" fill="{INK}" font-size="32" font-weight="700">{esc(link["label"])}</text>',
        f'<text x="{W - 64}" y="{H / 2 + 9}" fill="{MUTED}" font-size="25" text-anchor="end">{esc(link["display"])}</text>',
        f'<path d="M{W - 48} {H / 2 + 8} l14 -14 M{W - 46} {H / 2 - 6} h12 v12" fill="none" stroke="{CYAN}" '
        f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
        "</g></svg>",
    ]
    write(os.path.join(OUT_DIR, f'{link["id"]}.svg'), parts)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for index, link in enumerate(json.load(open(SRC))):
        row(link, index)


if __name__ == "__main__":
    main()
