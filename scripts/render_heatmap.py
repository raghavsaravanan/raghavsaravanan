#!/usr/bin/env python3
"""
Render data/stats.json as a 53-week contribution calendar inside a terminal
window. Cells ripple in once from the top-left, then the graph holds still.

    python scripts/render_heatmap.py
"""
import datetime
import json
import os

from theme import CYAN, FRAME, GOLD, GREEN, GREENS, INK, MUTED, TITLEBAR_H, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "stats.json")
OUT = os.path.join(ROOT, "assets", "heatmap.svg")

CELL, GAP = 12, 3
STEP = CELL + GAP
PAD = 24
DAY_LABEL_W = 32
MONTH_LABEL_H = 22
FOOTER_H = 92

COL_DELAY = 0.022
ROW_DELAY = 0.05

CSS = (
    "@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}"
    "100%{opacity:1;transform:scale(1)}}"
    ".c{opacity:0;transform-box:fill-box;transform-origin:center;"
    "animation:pop .5s cubic-bezier(.2,.8,.2,1) both}"
    "@keyframes fade{to{opacity:1}}"
    ".f{opacity:0;animation:fade .6s ease-out both}"
)


def pretty(iso):
    return datetime.date.fromisoformat(iso).strftime("%b %-d, %Y")


def weeks(days):
    """Group days into Sunday-first week columns, padding the first and last weeks."""
    first = datetime.date.fromisoformat(days[0]["date"])
    column = [None] * ((first.weekday() + 1) % 7)
    grid = []
    for day in days:
        column.append(day)
        if len(column) == 7:
            grid.append(column)
            column = []
    if column:
        grid.append(column + [None] * (7 - len(column)))
    return grid


def main():
    data = json.load(open(SRC))
    grid = weeks(data["days"])
    width = PAD * 2 + DAY_LABEL_W + len(grid) * STEP - GAP
    grid_top = TITLEBAR_H + MONTH_LABEL_H + 8
    grid_left = PAD + DAY_LABEL_W
    grid_bottom = grid_top + 7 * STEP - GAP
    height = grid_bottom + FOOTER_H + 24

    parts = window(width, height, "~$ ./contributions.sh --last-year", css=CSS)

    # Label each month at its first full week, skipping slivers too narrow to fit a label.
    labels = []
    for ci, column in enumerate(grid):
        first = column[0]
        if first and int(first["date"][8:]) <= 7 and ci < len(grid) - 2:
            labels.append((ci, datetime.date.fromisoformat(first["date"]).strftime("%b")))
    for i, (ci, label) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - ci < 3:
            continue
        parts.append(f'<text x="{grid_left + ci * STEP}" y="{TITLEBAR_H + 22}" fill="{MUTED}" '
                     f'font-size="11">{label}</text>')

    for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(f'<text x="{PAD}" y="{grid_top + row * STEP + 10}" fill="{MUTED}" font-size="10">{name}</text>')

    for ci, column in enumerate(grid):
        for ri, day in enumerate(column):
            if not day:
                continue
            plural = "" if day["count"] == 1 else "s"
            parts.append(
                f'<rect class="c" x="{grid_left + ci * STEP}" y="{grid_top + ri * STEP}" width="{CELL}" '
                f'height="{CELL}" rx="2.5" fill="{GREENS[min(day["level"], 4)]}" '
                f'style="animation-delay:{ci * COL_DELAY + ri * ROW_DELAY:.3f}s">'
                f'<title>{day["count"]} contribution{plural} on {pretty(day["date"])}</title></rect>'
            )

    reveal_end = len(grid) * COL_DELAY + 7 * ROW_DELAY

    legend_y = grid_bottom + 12
    legend_x = width - PAD - len(GREENS) * STEP - 34
    parts.append(f'<g class="f" style="animation-delay:{reveal_end:.2f}s">')
    parts.append(f'<text x="{legend_x - 8}" y="{legend_y + 10}" fill="{MUTED}" font-size="10" '
                 f'text-anchor="end">Less</text>')
    for i, color in enumerate(GREENS):
        parts.append(f'<rect x="{legend_x + i * STEP}" y="{legend_y}" width="{CELL}" height="{CELL}" '
                     f'rx="2.5" fill="{color}"/>')
    parts.append(f'<text x="{legend_x + len(GREENS) * STEP + 4}" y="{legend_y + 10}" fill="{MUTED}" '
                 f'font-size="10">More</text>')

    rule_y = legend_y + CELL + 14
    parts.append(f'<line x1="{PAD}" y1="{rule_y}" x2="{width - PAD}" y2="{rule_y}" stroke="{FRAME}"/>')

    current, longest, best = data["current_streak"], data["longest_streak"], data["best_day"]
    line1, line2 = rule_y + 26, rule_y + 50
    parts.append(
        f'<text x="{PAD}" y="{line1}" font-size="14" fill="{MUTED}"><tspan fill="{CYAN}">$</tspan> '
        f'<tspan fill="{GREEN}" font-weight="700">{data["total_contributions"]:,}</tspan> contributions '
        f'across <tspan fill="{INK}" font-weight="700">{data["active_days"]}</tspan> active days</text>'
    )
    parts.append(f'<text x="{width - PAD}" y="{line1}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'{esc(pretty(data["range"]["start"]))} &#8594; {esc(pretty(data["range"]["end"]))}</text>')
    parts.append(
        f'<text x="{PAD}" y="{line2}" font-size="14" fill="{MUTED}"><tspan fill="{CYAN}">$</tspan> '
        f'current streak <tspan fill="{CYAN}" font-weight="700">{current["length"]} days</tspan>'
        f'  &#183;  longest <tspan fill="{CYAN}" font-weight="700">{longest["length"]} days</tspan></text>'
    )
    parts.append(f'<text x="{width - PAD}" y="{line2}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'best day <tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> '
                 f'on {esc(pretty(best["date"]))}</text>')
    parts.append("</g></svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
