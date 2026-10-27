#!/usr/bin/env python3
"""
Turn source/avatar.jpg into a monochrome ASCII portrait SVG. A cyan scanline
sweeps down once, printing each row as it passes, then the portrait holds.

The background is removed with source/mask.png (from scripts/cutout.swift) and
local contrast is boosted so the eyes, brows, and smile survive at ASCII size.
This only needs rerunning when the photo changes, so it isn't in the workflow.

    swift scripts/cutout.swift source/avatar.jpg source/mask.png
    pip install -r scripts/requirements-portrait.txt
    python scripts/make_portrait.py
"""
import os

import cv2
import numpy as np

from theme import CYAN, FRAME, INK, MUTED, SOFT_INK, TITLEBAR_H, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PHOTO = os.path.join(ROOT, "source", "avatar.jpg")
MASK = os.path.join(ROOT, "source", "mask.png")
OUT = os.path.join(ROOT, "assets", "portrait.svg")

W, H = 840, 880  # matches assets/stats.svg
SCALE = 2
PAD = 20
STATUS_H = 64
ART_TOP = TITLEBAR_H * SCALE + 8
ART_W = W - PAD * 2
ART_H = H - ART_TOP - STATUS_H - 8

COLS = 150
CELL_W = ART_W / COLS
ROWS = int(ART_H / (CELL_W * 1.9))
CELL_H = ART_H / ROWS

# Bright areas print as dense characters, so the portrait reads like a lit face
# on a dark terminal. Dark hair and clothing keep the RAMP[1] floor, which
# preserves the silhouette; only pixels outside the person mask print blank.
RAMP = " .:-=+*#%@"
GAMMA = 1.0

SWEEP = 4.5              # seconds for the scanline to cover the portrait
NAME = "Raghav Saravanan"
ROLE = "AI Engineer Intern @ bondingAI"


def prepared_image():
    photo = cv2.cvtColor(cv2.imread(PHOTO), cv2.COLOR_BGR2GRAY)
    mask = cv2.imread(MASK, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
    mask = cv2.resize(mask, photo.shape[::-1])

    smooth = cv2.bilateralFilter(photo, 7, 30, 7)
    local = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(6, 6)).apply(smooth)
    lo, hi = np.percentile(local[mask > 0.5], [3, 96])
    tone = np.clip((local.astype(np.float32) - lo) / (hi - lo), 0, 1)

    # Darken thin features (eyelids, pupils, brows) that plain averaging washes out.
    fine = cv2.GaussianBlur(smooth, (0, 0), 1.4).astype(np.float32)
    coarse = cv2.GaussianBlur(smooth, (0, 0), 5).astype(np.float32)
    tone = np.clip(tone - 0.5 * np.clip((coarse - fine) / 35.0, 0, 1), 0, 1)

    # Pad the sides so the photo matches the art area's aspect ratio.
    h, w = tone.shape
    side = max(0, (int(h * ART_W / ART_H) - w) // 2)
    pad = lambda img: cv2.copyMakeBorder(img, 0, 0, side, side, cv2.BORDER_CONSTANT, value=0.0)
    return pad(tone), pad(mask)


def ascii_rows(tone, mask):
    shrink = lambda img: cv2.resize(img, (COLS, ROWS), interpolation=cv2.INTER_AREA)
    tone, mask = shrink(tone), shrink(mask)
    rows = []
    for tone_row, mask_row in zip(tone, mask):
        chars = [
            " " if inside < 0.5 else RAMP[max(1, min(len(RAMP) - 1, int(lum ** GAMMA * (len(RAMP) - 1) + 0.5)))]
            for lum, inside in zip(tone_row, mask_row)
        ]
        rows.append("".join(chars).rstrip())
    return rows


def main():
    rows = ascii_rows(*prepared_image())
    css = ("@keyframes print{from{opacity:0}to{opacity:1}}"
           ".r{opacity:0;animation:print .25s ease-out both}"
           "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
           ".k{animation:blink 1s step-end infinite}"
           "@keyframes scan{0%{opacity:.9;transform:translateY(0)}95%{opacity:.9}"
           f"100%{{opacity:0;transform:translateY({ART_H}px)}}}}"
           f".s{{opacity:0;animation:scan {SWEEP}s linear both}}")
    parts = window(W, H, "~$ ./portrait.sh", scale=SCALE, css=css)

    font = CELL_H * 0.9
    for i, line in enumerate(rows):
        if not line:
            continue
        y = ART_TOP + i * CELL_H + CELL_H * 0.78
        parts.append(
            f'<text class="r" xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{SOFT_INK}" '
            f'font-size="{font:.1f}" textLength="{len(line) * CELL_W:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'style="animation-delay:{SWEEP * i / ROWS:.3f}s">{esc(line)}</text>'
        )

    parts.append(f'<rect class="s tw" x="0" y="{ART_TOP}" width="{W}" height="3" fill="{CYAN}"/>')

    bar_y = H - STATUS_H
    text_y = bar_y + 40
    parts.append(f'<line x1="0" y1="{bar_y}" x2="{W}" y2="{bar_y}" stroke="{FRAME}"/>')
    status = f"$ whoami  {NAME}  ·  {ROLE}"
    parts.append(f'<text x="{PAD + 4}" y="{text_y}" font-size="20" fill="{MUTED}" xml:space="preserve" '
                 f'textLength="{len(status) * 12:.1f}" lengthAdjust="spacingAndGlyphs">'
                 f'<tspan fill="{CYAN}">$</tspan> whoami  <tspan fill="{INK}" font-weight="700">{esc(NAME)}</tspan>'
                 f'  ·  {esc(ROLE)}</text>')
    cursor_x = PAD + 4 + len(status) * 20 * 0.6 + 8
    parts.append(f'<rect class="k" x="{cursor_x:.0f}" y="{text_y - 17}" width="11" height="21" fill="{INK}"/>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
