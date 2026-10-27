#!/usr/bin/env python3
"""
Render the last year of contributions as an ASCII farm in the portrait's style.

The landscape (mountains, sun, pines, barn, silo) comes from
data/farm_scene.json, painted and converted to ASCII by make_farm_scene.py.
The scenery prints in under a scanline, then the tractor starts doing laps of the
field. On its first pass each week's column turns from grass to crops, and every
day's crop grows denser with that day's contribution level. After that it keeps
circling, wheels spinning, while the chickens peck in the yard.

Drawn at 2x and shown at half size in the README.

    python scripts/render_farm.py
"""
import datetime
import json
import os

from theme import CYAN, FRAME, GOLD, INK, MUTED, SOFT_INK, TITLEBAR_H, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "stats.json")
SCENE = os.path.join(ROOT, "data", "farm_scene.json")
OUT = os.path.join(ROOT, "assets", "farm.svg")

SCALE = 2
CW, CH = 8, 15
FONT_SIZE = CH * 0.9
X0 = 40
ART_TOP = TITLEBAR_H * SCALE + 18

SCENE_ROWS = 30
MONTHS = SCENE_ROWS + 1
FIELD_TOP = MONTHS + 1               # 7 days x 2 rows per plot
YARD_TOP = FIELD_TOP + 14 + 1
GRASS = YARD_TOP + 5
ROWS = GRASS + 1
FIELD_C0 = 23
PLOT_W = 3

UNTILLED = "#2b4a33"
# GitHub's own contribution greens, so the field reads like the graph every visitor
# already knows. Days with no contributions are bare soil.
BEDS = ["#3a2f23", "#0e4429", "#006d32", "#26a641", "#39d353"]
CROPS = ["", ",", "v", "Y", "\u00a5"]   # a crop on each bed that grows with the level
BED = 22
RED = "#ff7b72"

SCENE_COLORS = {
    "sun": GOLD, "far": "#8b949e", "snow": INK, "hill": "#6e7681", "meadow": "#3d5a45",
    "tree": "#2ea043", "barn": "#e5534b", "roof": "#f47067", "window": GOLD, "door": "#a0413b",
    "silo": "#adbac7",
}

CHICKEN = ["  \\\\", "  (o>", "\\\\_//)", " \\_/_)", "  _|_"]
TRACTOR = [
    "      ___       |   ",
    "     |   |______|_  ",
    "     |___|        \\ ",
    "  ___|___|_________|",
    " /  _  \\  |__| / _ \\",
    "|  (o)  |-------(o) |",
    " \\_____/       \\___/",
]
CHICK = ["(.>", " ^ "]

PRINT_TIME = 1.2
DRIVE_START = PRINT_TIME + 0.1
LAP = 9.0                            # seconds per lap; the first lap tills the field
TRACTOR_PARK_C = 150                 # where it sits if the viewer prefers reduced motion

CSS = (
    "@keyframes print{from{opacity:0}to{opacity:1}}"
    ".r{opacity:0;animation:print .3s ease-out both}"
    "@keyframes scan{0%{opacity:.9;transform:translateY(0)}92%{opacity:.9}"
    f"100%{{opacity:0;transform:translateY({SCENE_ROWS * CH}px)}}}}"
    f".sc{{opacity:0;animation:scan {PRINT_TIME}s linear both}}"
    "@keyframes till{to{opacity:0}}"
    ".u{animation:till .3s ease-out both}"
    "@keyframes sprout{0%{opacity:0;transform:translateY(8px)}100%{opacity:1;transform:none}}"
    ".g{opacity:0;animation:sprout .5s ease-out both}"
    "@keyframes puff{0%{opacity:0;transform:translate(0,0)}20%{opacity:.8}"
    "100%{opacity:0;transform:translate(16px,-50px)}}"
    ".pf{opacity:0;animation:puff 2.2s ease-out infinite}"
    "@keyframes peck{0%,55%,100%{transform:none}65%,85%{transform:translate(6px,11px)}}"
    ".p{animation:peck 2.4s ease-in-out infinite}"
    "@keyframes wander{0%,100%{transform:none}50%{transform:translateX(90px)}}"
    ".wa{animation:wander 10s ease-in-out infinite}"
    "@keyframes spin{0%,49%{opacity:1}50%,100%{opacity:0}}"
    ".ha{animation:spin .36s step-end infinite}"
    ".hb{animation:spin .36s step-end -.18s infinite}"
)


def noise(r, c):
    return ((c * 73856093) ^ (r * 19349663)) % 1000 / 1000


def cx(col):
    return X0 + col * CW


def cy(row):
    """Baseline of a character row."""
    return ART_TOP + row * CH + CH * 0.78


def runs(chars, colors):
    """Group a row into (color, text) runs; spaces inherit the current color."""
    out, current, buf = [], None, ""
    for char, color in zip(chars, colors):
        color = color if char != " " else current
        if color != current and buf:
            out.append((current, buf))
            buf = ""
        current = color
        buf += char
    if buf:
        out.append((current, buf))
    return out


def line_svg(chars, colors, col, row, cls="", style=""):
    if not "".join(chars).strip():
        return ""
    body = "".join(f'<tspan fill="{c}">{esc(s)}</tspan>' if c else esc(s) for c, s in runs(chars, colors))
    attrs = (f' class="{cls}"' if cls else "") + (f' style="{style}"' if style else "")
    return (f'<text{attrs} x="{cx(col):.1f}" y="{cy(row):.1f}" font-size="{FONT_SIZE:.1f}" xml:space="preserve" '
            f'textLength="{len(chars) * CW}" lengthAdjust="spacingAndGlyphs">{body}</text>')


def sprite_svg(lines, row, col, color_of, cls="", style="", backing=False):
    """A movable sprite: one <text> per line. With backing, nothing behind shows through its spaces."""
    attrs = (f' class="{cls}"' if cls else "") + (f' style="{style}"' if style else "")
    out = [f"<g{attrs}>"]
    for i, line in enumerate(lines):
        filled = [j for j, char in enumerate(line) if char != " "]
        if backing and filled:
            out.append(f'<rect x="{cx(col + filled[0]):.1f}" y="{ART_TOP + (row + i) * CH:.1f}" '
                       f'width="{(filled[-1] - filled[0] + 1) * CW}" height="{CH}" fill="url(#bg)"/>')
        out.append(line_svg(list(line), [color_of(i, j, ch) for j, ch in enumerate(line)], col, row + i))
    out.append("</g>")
    return out


def weeks(days):
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


def column_layer(col, cells, cls, delay):
    """One <text> per field column, with a positioned <tspan> for each non-empty row."""
    spans = "".join(f'<tspan x="{cx(col):.1f}" y="{cy(r):.1f}" fill="{color}" textLength="{PLOT_W * CW}" '
                    f'lengthAdjust="spacingAndGlyphs">{esc(s)}</tspan>' for r, s, color in cells if s.strip())
    if not spans:
        return ""
    return (f'<text class="{cls}" font-size="{FONT_SIZE:.1f}" xml:space="preserve" '
            f'style="animation-delay:{delay:.2f}s">{spans}</text>')


def main():
    data = json.load(open(SRC))
    scene = json.load(open(SCENE))
    grid = weeks(data["days"])
    cols = scene["cols"]
    width = X0 * 2 + cols * CW

    # The tractor laps from just off the left edge of the scene to just off the right.
    tractor_w = len(TRACTOR[0]) * CW
    park_x = cx(TRACTOR_PARK_C)
    enter_x, exit_x = cx(0) - tractor_w, cx(cols)

    def till_time(col):
        """When the middle of the tractor first passes this column."""
        progress = (cx(col) - enter_x - tractor_w / 2) / (exit_x - enter_x)
        return DRIVE_START + LAP * progress

    footer_top = ART_TOP + ROWS * CH + 18
    height = footer_top + 108
    css = CSS + (f"@keyframes drive{{from{{transform:translateX({enter_x - park_x:.1f}px)}}"
                 f"to{{transform:translateX({exit_x - park_x:.1f}px)}}}}"
                 f".tr{{animation:drive {LAP}s linear {DRIVE_START}s infinite both}}")
    parts = window(width, height, f"~$ ./farm.sh --season {data['range']['end'][:4]}", scale=SCALE, css=css)

    # Scenery prints top to bottom under a scanline, like the portrait.
    for r, (line, colors) in enumerate(zip(scene["scene"], scene["scene_colors"])):
        parts.append(line_svg(list(line), [SCENE_COLORS.get(c) for c in colors], 0, r, cls="r",
                              style=f"animation-delay:{PRINT_TIME * r / SCENE_ROWS:.3f}s"))
    parts.append(f'<rect class="sc tw" x="0" y="{ART_TOP}" width="{width}" height="3" fill="{CYAN}"/>')

    labels = [(ci, datetime.date.fromisoformat(col[0]["date"]).strftime("%b"))
              for ci, col in enumerate(grid) if col[0] and int(col[0]["date"][8:]) <= 7 and ci < len(grid) - 2]
    month_row = [" "] * cols
    for i, (ci, label) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - ci < 3:
            continue
        for k, ch in enumerate(label):
            month_row[FIELD_C0 + ci * PLOT_W + k] = ch
    parts.append(line_svg(month_row, [MUTED] * cols, 0, MONTHS))
    for d, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(line_svg(list(name), [MUTED] * 3, FIELD_C0 - 5, FIELD_TOP + d * 2 + 1))

    # Field: grass until the tractor's first pass, then each day's seed bed in its
    # contribution color with a crop that grows with the level. The best day gets a gold ring.
    best = data["best_day"]
    planted = 0
    for ci, column in enumerate(grid):
        col = FIELD_C0 + ci * PLOT_W
        when = till_time(col + 1)
        grass, beds = [], []
        for d, day in enumerate(column):
            if not day:
                continue
            top = FIELD_TOP + d * 2
            for r in (top, top + 1):
                tex = "".join("'" if noise(r, col + k) < 0.28 else " " for k in range(PLOT_W))
                grass.append((r, tex, UNTILLED))
            level = min(day["level"], 4)
            planted += bool(level)
            x = cx(col) + (PLOT_W * CW - BED) / 2
            y = ART_TOP + top * CH + (2 * CH - BED) / 2
            ring = f' stroke="{GOLD}" stroke-width="3"' if day["date"] == best["date"] else ""
            beds.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BED}" height="{BED}" rx="4" fill="{BEDS[level]}"{ring}>'
                        f'<title>{day["count"]} contributions on {day["date"]}</title></rect>')
            if level:
                beds.append(f'<text x="{x + BED / 2:.1f}" y="{y + BED * 0.74:.1f}" fill="#e6ffec" opacity=".85" '
                            f'font-size="17" font-weight="700" text-anchor="middle">{CROPS[level]}</text>')
        parts.append(column_layer(col, grass, "u", when))
        parts.append(f'<g class="g" style="animation-delay:{when + 0.12:.2f}s">{"".join(beds)}</g>')

    # Tractor, driving along the meadow from beside the barn to the far end, puffing exhaust.
    def tractor_color(i, j, ch):
        if i >= 4:
            return GOLD if ch in "o+" else SOFT_INK
        return "#3fb950"

    tractor_row = SCENE_ROWS - len(TRACTOR)
    hubs = TRACTOR.index(next(line for line in TRACTOR if "(o)" in line))
    spun = TRACTOR[hubs].replace("(o)", "(+)")
    parts.append(f'<clipPath id="lane"><rect x="{cx(0)}" y="{ART_TOP}" width="{cols * CW}" '
                 f'height="{SCENE_ROWS * CH}"/></clipPath>')
    parts.append(f'<g clip-path="url(#lane)"><g transform="translate({park_x - cx(0):.1f} 0)"><g class="tr">')
    frame = [line if i != hubs else " " * len(line) for i, line in enumerate(TRACTOR)]
    parts += sprite_svg(frame, tractor_row, 0, tractor_color, backing=True)
    # Hubs alternate between (o) and (+) so the wheels look like they're turning.
    parts += sprite_svg([TRACTOR[hubs]], tractor_row + hubs, 0, lambda i, j, ch: tractor_color(hubs, j, ch),
                        cls="ha", backing=True)
    parts += sprite_svg([spun], tractor_row + hubs, 0, lambda i, j, ch: tractor_color(hubs, j, ch),
                        cls="hb cf", backing=True)
    for k, delay in enumerate([0, 0.7, 1.4]):
        parts.append(f'<text class="pf" x="{cx(16):.1f}" y="{cy(tractor_row - 1):.1f}" fill="#8b949e" '
                     f'font-size="{FONT_SIZE + k * 2:.1f}" style="animation-delay:{delay}s">{"oO°"[k]}</text>')
    parts.append("</g></g></g>")

    # The yard: two hens pecking in place, one wandering with her chick.
    def chicken_color(i, j, ch):
        return RED if i == 0 else GOLD if ch == ">" or i == 4 else SOFT_INK

    def hen(col, delay):
        head = sprite_svg(CHICKEN[:2], YARD_TOP, col, chicken_color, cls="p", style=f"animation-delay:{delay}s")
        body = sprite_svg(CHICKEN[2:], YARD_TOP + 2, col, lambda i, j, ch: chicken_color(i + 2, j, ch))
        return head + body

    grass_line = ["\"',."[int(noise(GRASS, c) * 4)] if noise(c, GRASS) < 0.6 else " " for c in range(cols)]
    parts.append(line_svg(grass_line, ["#2ea043"] * cols, 0, GRASS))
    parts += hen(30, 0)
    parts.append('<g class="wa" style="animation-delay:-2s">')
    parts += hen(66, 0.9)
    parts += sprite_svg(CHICK, YARD_TOP + 3, 76, lambda i, j, ch: GOLD, cls="p", style="animation-delay:1.3s")
    parts.append("</g>")
    parts += hen(118, 1.6)
    parts += sprite_svg([": . : ."], YARD_TOP + 4, 38, lambda i, j, ch: "#bb8009")

    # Footer: the headline numbers and a legend in the same colors as the beds.
    parts.append(f'<line x1="{X0}" y1="{footer_top}" x2="{width - X0}" y2="{footer_top}" stroke="{FRAME}"/>')
    best_date = datetime.date.fromisoformat(best["date"]).strftime("%b %-d, %Y")
    size, line1, line2 = 26, footer_top + 44, footer_top + 88
    parts.append(
        f'<text x="{X0}" y="{line1}" font-size="{size}" fill="{MUTED}"><tspan fill="{CYAN}">$</tspan> '
        f'<tspan fill="#39d353" font-weight="700">{data["total_contributions"]:,}</tspan> contributions in the last year'
        f'  &#183;  <tspan fill="{INK}" font-weight="700">{planted}</tspan> days planted</text>')
    parts.append(f'<text x="{width - X0}" y="{line1}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">'
                 f'<tspan fill="{GOLD}">&#9675;</tspan> best day <tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan>'
                 f' on {esc(best_date)}</text>')
    char = (size - 2) * 0.6
    parts.append(f'<text x="{X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}">'
                 f'<tspan fill="{CYAN}">$</tspan> less</text>')
    lx = X0 + char * 7
    for level, color in enumerate(BEDS):
        parts.append(f'<rect x="{lx:.1f}" y="{line2 - 19}" width="{BED}" height="{BED}" rx="4" fill="{color}"/>')
        if level:
            parts.append(f'<text x="{lx + BED / 2:.1f}" y="{line2 - 19 + BED * 0.74:.1f}" fill="#e6ffec" opacity=".85" '
                         f'font-size="17" font-weight="700" text-anchor="middle">{CROPS[level]}</text>')
        lx += BED + 8
    parts.append(f'<text x="{lx + 6:.1f}" y="{line2}" font-size="{size - 2}" fill="{MUTED}">more  &#183;  one bed per day</text>')
    parts.append(f'<text x="{width - X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">'
                 f'flock <tspan fill="{INK}" font-weight="700">3</tspan> + 1 chick &#183; on bug patrol</text>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
