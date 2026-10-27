#!/usr/bin/env python3
"""
Render one terminal-window card per entry in data/projects.json into
assets/projects/<repo>.svg. The project name types itself in behind a block
cursor, then the description and tags fade up.

Cards are drawn at 2x and shown at half size in the README.

    python scripts/render_projects.py
"""
import json
import os
import textwrap

from theme import CYAN, FRAME, GOLD, INK, MUTED, PANEL, SOFT_INK, TITLEBAR_H, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "projects.json")
OUT_DIR = os.path.join(ROOT, "assets", "projects")

W, H = 840, 430
SCALE = 2
PAD = 36
NAME_SIZE = 46
DESC_SIZE = 24
DESC_LINE = 36
TAG_SIZE = 19
CHAR = 0.6  # monospace advance width, in em

TYPE_TIME = 0.6

CSS = (
    "@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    ".f{opacity:0;animation:rise .5s ease-out both}"
    "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
    ".k{animation:blink 1s step-end infinite}"
)


def card(project):
    slug = project.get("slug", project["repo"].lower())
    parts = window(W, H, f"~/projects/{slug}", scale=SCALE, css=CSS)

    prompt_y = TITLEBAR_H * SCALE + 46
    parts.append(f'<text x="{PAD}" y="{prompt_y}" fill="{MUTED}" font-size="20">'
                 f'<tspan fill="{CYAN}">$</tspan> cat README.md | head -1</text>')

    name_y = prompt_y + 66
    chars = len(project["name"])
    name_w = chars * NAME_SIZE * CHAR
    # Discrete steps reveal one whole character at a time, like typing.
    steps = ";".join(str(round(name_w * i / chars) + (4 if i == chars else 0)) for i in range(chars + 1))
    parts.append(
        f'<clipPath id="n"><rect x="{PAD}" y="{name_y - NAME_SIZE}" width="0" height="{NAME_SIZE + 14}">'
        f'<animate attributeName="width" values="{steps}" calcMode="discrete" begin="0.2s" '
        f'dur="{TYPE_TIME}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<text clip-path="url(#n)" x="{PAD}" y="{name_y}" fill="{INK}" font-size="{NAME_SIZE}" '
                 f'font-weight="700">{esc(project["name"])}</text>')
    parts.append(
        f'<rect class="k" x="{PAD + name_w + 8:.0f}" y="{name_y - NAME_SIZE + 8}" width="{NAME_SIZE * 0.5:.0f}" '
        f'height="{NAME_SIZE}" fill="{CYAN}" opacity="0.8"/>'
    )

    badge = project["badge"]
    color = GOLD if project.get("highlight") else CYAN
    badge_w = len(badge) * 20 * CHAR + 32
    badge_x = W - PAD - badge_w
    parts.append(f'<g class="f" style="animation-delay:{TYPE_TIME:.2f}s">'
                 f'<rect x="{badge_x:.0f}" y="{name_y - 34}" width="{badge_w:.0f}" height="40" rx="20" '
                 f'fill="{color}" fill-opacity="0.12" stroke="{color}" stroke-opacity="0.7"/>'
                 f'<text x="{badge_x + badge_w / 2:.0f}" y="{name_y - 7}" fill="{color}" font-size="20" '
                 f'font-weight="700" text-anchor="middle">{esc(badge)}</text></g>')

    width_chars = int((W - PAD * 2) / (DESC_SIZE * CHAR))
    lines = textwrap.wrap(project["description"], width_chars)[:3]
    desc_y = name_y + 56
    parts.append(f'<g class="f" style="animation-delay:{TYPE_TIME + 0.15:.2f}s">')
    for i, line in enumerate(lines):
        parts.append(f'<text x="{PAD}" y="{desc_y + i * DESC_LINE}" fill="{SOFT_INK}" '
                     f'font-size="{DESC_SIZE}">{esc(line)}</text>')
    parts.append("</g>")

    tag_y = H - PAD - 38
    x = PAD
    parts.append(f'<g class="f" style="animation-delay:{TYPE_TIME + 0.35:.2f}s">')
    for tag in project["tags"]:
        tag_w = len(tag) * TAG_SIZE * CHAR + 28
        parts.append(f'<rect x="{x:.0f}" y="{tag_y}" width="{tag_w:.0f}" height="38" rx="8" fill="{PANEL}" '
                     f'stroke="{FRAME}"/><text x="{x + tag_w / 2:.0f}" y="{tag_y + 26}" fill="{INK}" '
                     f'font-size="{TAG_SIZE}" text-anchor="middle">{esc(tag)}</text>')
        x += tag_w + 12
    parts.append("</g></svg>")
    write(os.path.join(OUT_DIR, f"{slug}.svg"), parts)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for project in json.load(open(SRC)):
        card(project)


if __name__ == "__main__":
    main()
