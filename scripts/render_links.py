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

from theme import CYAN, FONT, FRAME, INK, MUTED, REDUCED_MOTION, esc, gradient, type_in, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "links.json")
OUT_DIR = os.path.join(ROOT, "assets", "links")

W, H = 840, 84
PAD = 28
SIZE = 24
CHAR = SIZE * 0.6
ROW_GAP = 0.15

CSS = "@keyframes fade{to{opacity:1}}.f{opacity:0;animation:fade .4s ease-out both}"


def row(link, start, is_last):
    command = f"$ {link['command']} {link['target']}"
    y = H / 2 + 8
    type_css, cover, done = type_in("t", PAD, y, SIZE, len(command), CHAR, start, keep_cursor=is_last)
    label = f"# {link['label']}"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
        f"<style>{CSS}{type_css}{REDUCED_MOTION}</style>",
        gradient(H),
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="url(#bg)" stroke="{FRAME}" stroke-width="2"/>',
        # textLength pins every glyph to the typing grid, whatever monospace font the viewer has.
        f'<text x="{PAD}" y="{y}" font-size="{SIZE}" fill="{MUTED}" xml:space="preserve" '
        f'textLength="{len(command) * CHAR:.1f}" lengthAdjust="spacingAndGlyphs">'
        f'<tspan fill="{CYAN}">$</tspan> {esc(link["command"])} <tspan fill="{INK}">{esc(link["target"])}</tspan></text>',
        cover,
        f'<text class="f" x="{W - PAD}" y="{y}" font-size="{SIZE}" fill="{MUTED}" text-anchor="end" '
        f'textLength="{len(label) * CHAR:.1f}" lengthAdjust="spacingAndGlyphs" '
        f'style="animation-delay:{done:.2f}s"># <tspan fill="{INK}" font-weight="700">{esc(link["label"])}</tspan></text>',
        "</svg>",
    ]
    write(os.path.join(OUT_DIR, f'{link["id"]}.svg'), parts)
    return done + ROW_GAP


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    links = json.load(open(SRC))
    start = 0.3
    for i, link in enumerate(links):
        start = row(link, start, i == len(links) - 1)


if __name__ == "__main__":
    main()
