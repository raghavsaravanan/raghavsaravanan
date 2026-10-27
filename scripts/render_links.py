#!/usr/bin/env python3
"""
Render one terminal command line per entry in data/links.json into
assets/links/<id>.svg. The README stacks them, each wrapped in its own link,
and the commands type themselves in one after another like a running script.

Rows are drawn at 2x and shown at half size in the README.

    python scripts/render_links.py
"""
import json
import os

from theme import CYAN, FONT, FRAME, INK, MUTED, REDUCED_MOTION, BG_BOTTOM, BG_TOP, esc, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "links.json")
OUT_DIR = os.path.join(ROOT, "assets", "links")

W, H = 840, 84
PAD = 28
SIZE = 24
CHAR = SIZE * 0.6
CHAR_TIME = 0.025
ROW_GAP = 0.15

CSS = (
    "@keyframes fade{to{opacity:1}}"
    ".f{opacity:0;animation:fade .4s ease-out both}"
    "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
    ".k{animation:blink 1s step-end infinite}"
)


def row(link, start, is_last):
    command = f"$ {link['command']} {link['target']}"
    typed_w = len(command) * CHAR
    steps = ";".join(f"{typed_w * i / len(command):.1f}" for i in range(len(command) + 1))
    dur = len(command) * CHAR_TIME
    y = H / 2 + 8

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
        f"<style>{CSS}{REDUCED_MOTION}</style>",
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient></defs>',
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="url(#bg)" stroke="{FRAME}" stroke-width="2"/>',
        # Discrete steps reveal one whole character at a time, like typing.
        f'<clipPath id="t"><rect x="{PAD}" y="0" width="0" height="{H}">'
        f'<animate attributeName="width" values="{steps}" calcMode="discrete" begin="{start:.2f}s" '
        f'dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>',
        f'<text clip-path="url(#t)" x="{PAD}" y="{y}" font-size="{SIZE}" fill="{MUTED}" xml:space="preserve">'
        f'<tspan fill="{CYAN}">$</tspan> {esc(link["command"])} '
        f'<tspan fill="{INK}">{esc(link["target"])}</tspan></text>',
    ]

    cursor = (f'<rect x="{PAD}" y="{y - SIZE + 4}" width="{CHAR:.1f}" height="{SIZE}" fill="{INK}" opacity="0">'
              f'<animate attributeName="x" values="{";".join(f"{PAD + float(s):.1f}" for s in steps.split(";"))}" '
              f'calcMode="discrete" begin="{start:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
              f'<set attributeName="opacity" to="0.85" begin="{start:.2f}s"/>')
    if not is_last:
        cursor += f'<set attributeName="opacity" to="0" begin="{start + dur + 0.1:.2f}s"/>'
    cursor += "</rect>"
    parts.append(f'<g class="k">{cursor}</g>' if is_last else cursor)

    parts.append(f'<text class="f" x="{W - PAD}" y="{y}" font-size="{SIZE}" fill="{MUTED}" text-anchor="end" '
                 f'style="animation-delay:{start + dur:.2f}s"># <tspan fill="{INK}" font-weight="700">'
                 f'{esc(link["label"])}</tspan></text>')
    parts.append("</svg>")
    write(os.path.join(OUT_DIR, f'{link["id"]}.svg'), parts)
    return start + dur + ROW_GAP


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    links = json.load(open(SRC))
    start = 0.3
    for i, link in enumerate(links):
        start = row(link, start, i == len(links) - 1)


if __name__ == "__main__":
    main()
