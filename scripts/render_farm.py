#!/usr/bin/env python3
"""
Render the last year of contributions as an ASCII farm in the portrait's style.

The landscape (mountains, sun, pines, barn, silo) comes from
data/farm_scene.json, painted and converted to ASCII by make_farm_scene.py.
The scenery prints in under a scanline, then the tractor drives across the field:
each week's column turns from grass to crops as it passes, and every day's crop
grows denser with that day's contribution level. Chickens keep pecking in the yard.

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
TRACTOR_C0 = 40

GREENS = ["#2ea043", "#3fb950", "#56d364"]
SOIL = "#7a6244"
UNTILLED = "#2b4a33"
RED = "#ff7b72"

SCENE_COLORS = {
    "sun": GOLD, "far": "#8b949e", "snow": INK, "hill": "#6e7681", "meadow": "#3d5a45",
    "tree": "#2ea043", "barn": "#e5534b", "roof": "#f47067", "window": GOLD, "door": "#a0413b",
    "silo": "#adbac7",
}

# (top row, bottom row, color) per contribution level: crops bunch up as the day gets busier.
PLOTS = [("   ", " . ", "#5a4a35"), (" , ", " : ", GREENS[0]), (" + ", ":+:", GREENS[1]),
         ("+*+", "*#*", GREENS[2]), ("#@#", "@%@", GOLD)]

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
DRIVE = 4.5

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

    tractor_w = len(TRACTOR[0]) * CW
    start_x = cx(TRACTOR_C0)
    end_x = cx(cols - len(TRACTOR[0]) - 30)

    def till_time(col):
        progress = (cx(col) - start_x - tractor_w / 2) / (end_x - start_x)
        return DRIVE_START + DRIVE * min(max(progress, 0), 1)

    footer_top = ART_TOP + ROWS * CH + 18
    height = footer_top + 108
    css = CSS + (f"@keyframes drive{{to{{transform:translateX({end_x - start_x:.1f}px)}}}}"
                 f".tr{{animation:drive {DRIVE}s linear {DRIVE_START}s both}}")
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

    # Field: grass until the tractor passes, then that week's crops.
    planted = 0
    for ci, column in enumerate(grid):
        col = FIELD_C0 + ci * PLOT_W
        when = till_time(col + 1)
        grass, crops = [], []
        for d, day in enumerate(column):
            if not day:
                continue
            top, bottom = FIELD_TOP + d * 2, FIELD_TOP + d * 2 + 1
            for r in (top, bottom):
                tex = "".join("'" if noise(r, col + k) < 0.28 else " " for k in range(PLOT_W))
                grass.append((r, tex, UNTILLED))
            level = min(day["level"], 4)
            planted += bool(level)
            upper, lower, color = PLOTS[level]
            crops += [(top, upper, color), (bottom, lower, color)]
        parts.append(column_layer(col, grass, "u", when))
        parts.append(column_layer(col, crops, "g", when + 0.12))

    # Tractor, driving along the meadow from beside the barn to the far end, puffing exhaust.
    def tractor_color(i, j, ch):
        if i >= 4:
            return GOLD if ch == "o" else SOFT_INK
        return "#3fb950"

    tractor_row = SCENE_ROWS - len(TRACTOR)
    parts.append(f'<g transform="translate({start_x - cx(0):.1f} 0)"><g class="tr">')
    parts += sprite_svg(TRACTOR, tractor_row, 0, tractor_color, backing=True)
    for k, delay in enumerate([0, 0.7, 1.4]):
        parts.append(f'<text class="pf" x="{cx(16):.1f}" y="{cy(tractor_row - 1):.1f}" fill="#8b949e" '
                     f'font-size="{FONT_SIZE + k * 2:.1f}" style="animation-delay:{delay}s">{"oO°"[k]}</text>')
    parts.append("</g></g>")

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

    # Footer, in the same voice as the contributions card.
    parts.append(f'<line x1="{X0}" y1="{footer_top}" x2="{width - X0}" y2="{footer_top}" stroke="{FRAME}"/>')
    best = data["best_day"]
    best_date = datetime.date.fromisoformat(best["date"]).strftime("%b %-d, %Y")
    size, line1, line2 = 26, footer_top + 44, footer_top + 88
    parts.append(
        f'<text x="{X0}" y="{line1}" font-size="{size}" fill="{MUTED}"><tspan fill="{CYAN}">$</tspan> harvest '
        f'<tspan fill="{GOLD}" font-weight="700">{data["total_contributions"]:,}</tspan> commits from '
        f'<tspan fill="{INK}" font-weight="700">{planted}</tspan> planted days</text>')
    parts.append(f'<text x="{width - X0}" y="{line1}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">best yield '
                 f'<tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> on {esc(best_date)}</text>')
    legend = "  ".join(f'<tspan fill="{color}" font-weight="700">{esc(lower)}</tspan>'
                       for _, lower, color in PLOTS)
    parts.append(f'<text x="{X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" xml:space="preserve">'
                 f'<tspan fill="{CYAN}">$</tspan> fallow {legend} ripe</text>')
    parts.append(f'<text x="{width - X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">'
                 f'flock <tspan fill="{INK}" font-weight="700">3</tspan> + 1 chick &#183; on bug patrol</text>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
