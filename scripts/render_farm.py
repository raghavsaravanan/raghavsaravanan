#!/usr/bin/env python3
"""
Render the last year of contributions as a dense ASCII farm, drawn on the same
fine character grid as the portrait.

Shaded mountains, the sun, a barn, and a silo print in under a scanline. Then a
tractor drives across the field: each week's column turns from grass to soil as
it passes, and that week's crops sprout to GitHub's contribution level for each
day. A flock of chickens keeps pecking in the yard after everything else stops.

Drawn at 2x and shown at half size in the README.

    python scripts/render_farm.py
"""
import datetime
import json
import math
import os

from theme import CYAN, FRAME, GOLD, INK, MUTED, SOFT_INK, TITLEBAR_H, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "stats.json")
OUT = os.path.join(ROOT, "assets", "farm.svg")

SCALE = 2
COLS, ROWS = 200, 46
CW, CH = 8, 15                      # character cell, same ~1:1.9 aspect as the portrait
FONT_SIZE = CH * 0.9
X0 = 40
W = X0 * 2 + COLS * CW
ART_TOP = TITLEBAR_H * SCALE + 18

HORIZON = 15                         # base of the mountain range; a meadow runs from here to the track
GROUND = 22                          # dirt track the barn, silo, and tractor stand on
FENCE = 23
MONTHS = 24
FIELD_TOP = 25                       # 7 days x 2 rows per plot
YARD_TOP = 40
GRASS = 45
FIELD_C0 = 23                        # first plot column; day labels sit just left of it
PLOT_W = 3

SOIL = "#7a6244"
UNTILLED = "#2b4a33"
GREENS = ["#2ea043", "#3fb950", "#56d364"]
BARN_RED = "#e5534b"
RED = "#ff7b72"
STEEL = "#8b949e"
BACK_RANGE = "#6e7681"
FRONT_RANGE = "#a5adb6"
SNOW = "#e6edf3"

PRINT_TIME = 1.0                    # scenery prints in over this long
DRIVE_START = PRINT_TIME + 0.1
DRIVE = 4.5

BARN = [
    "     ______     ",
    "   /`      `\\   ",
    "  /  .----.  \\  ",
    " |   | [] |   | ",
    " |   '----'   | ",
    " |  ___  ___  | ",
    " | |\\ /||\\ /| | ",
    " | | X || X | | ",
    " |_|/_\\||/_\\|_| ",
]
SILO = [
    "  .--.  ",
    " /    \\ ",
    "|======|",
    "|      |",
    "|======|",
    "|      |",
    "|======|",
    "|      |",
    "|======|",
    "|______|",
]
TRACTOR = [
    "   ___      |   ",
    "  |   |_____|_  ",
    "  |___|       \\ ",
    "  |___|________|",
    "  /   \\    / \\  ",
    " | (o) |--| o | ",
    "  \\___/    \\_/  ",
]
CHICKEN = ["  \\\\", "  (o>", "\\\\_//)", " \\_/_)", "  _|_"]
CHICK = ["(.>", " ^ "]
CLOUD = ["   .--.    ", ".-(    ).  ", "(___.__)__)"]

CSS = (
    "@keyframes print{from{opacity:0}to{opacity:1}}"
    ".r{opacity:0;animation:print .3s ease-out both}"
    "@keyframes scan{0%{opacity:.9;transform:translateY(0)}92%{opacity:.9}"
    f"100%{{opacity:0;transform:translateY({(MONTHS + 1) * CH}px)}}}}"
    f".sc{{opacity:0;animation:scan {PRINT_TIME}s linear both}}"
    "@keyframes till{to{opacity:0}}"
    ".u{animation:till .3s ease-out both}"
    "@keyframes soil{from{opacity:0}to{opacity:1}}"
    ".o{opacity:0;animation:soil .3s ease-out both}"
    "@keyframes sprout{0%{opacity:0;transform:translateY(8px)}100%{opacity:1;transform:none}}"
    ".g{opacity:0;animation:sprout .5s ease-out both}"
    "@keyframes puff{0%{opacity:0;transform:translate(0,0)}20%{opacity:.8}"
    "100%{opacity:0;transform:translate(14px,-46px)}}"
    ".pf{opacity:0;animation:puff 2.2s ease-out infinite}"
    "@keyframes peck{0%,55%,100%{transform:none}65%,85%{transform:translate(6px,11px)}}"
    ".p{animation:peck 2.4s ease-in-out infinite}"
    "@keyframes wander{0%,100%{transform:none}50%{transform:translateX(90px)}}"
    ".wa{animation:wander 10s ease-in-out infinite}"
    "@keyframes drift{0%,100%{transform:none}50%{transform:translateX(70px)}}"
    ".cl{animation:drift 24s ease-in-out infinite}"
)


def noise(r, c):
    return ((c * 73856093) ^ (r * 19349663)) % 1000 / 1000


def cx(col):
    return X0 + col * CW


def cy(row):
    """Baseline of a character row."""
    return ART_TOP + row * CH + CH * 0.78


class Grid:
    def __init__(self):
        self.ch = [[" "] * COLS for _ in range(ROWS)]
        self.color = [[None] * COLS for _ in range(ROWS)]

    def put(self, r, c, char, color):
        if 0 <= r < ROWS and 0 <= c < COLS and char != " ":
            self.ch[r][c] = char
            self.color[r][c] = color

    def sprite(self, lines, r0, c0, color_of):
        """Opaque between each line's first and last character, so scenery doesn't show through."""
        for i, line in enumerate(lines):
            filled = [j for j, char in enumerate(line) if char != " "]
            for j in range(filled[0], filled[-1] + 1) if filled else []:
                r, c = r0 + i, c0 + j
                if 0 <= r < ROWS and 0 <= c < COLS:
                    self.ch[r][c], self.color[r][c] = line[j], color_of(i, j, line[j])

    def text(self, r, c, s, color):
        for j, char in enumerate(s):
            self.put(r, c + j, char, color)

    def row_svg(self, r, delay):
        runs, current, buf = [], None, ""
        for char, color in zip(self.ch[r], self.color[r]):
            color = color if char != " " else current
            if color != current and buf:
                runs.append((current, buf))
                buf = ""
            current = color
            buf += char
        if buf:
            runs.append((current, buf))
        if all(not s.strip() for _, s in runs):
            return ""
        body = "".join(f'<tspan fill="{c}">{esc(s)}</tspan>' if c else esc(s) for c, s in runs)
        return (f'<text class="r" x="{X0}" y="{cy(r):.1f}" font-size="{FONT_SIZE:.1f}" xml:space="preserve" '
                f'textLength="{COLS * CW}" lengthAdjust="spacingAndGlyphs" '
                f'style="animation-delay:{delay:.3f}s">{body}</text>')


def sprite_svg(lines, row, col, color_of, cls="", style="", backing=False):
    """
    A sprite outside the static grid, so it can move. One <text> per line, colored per run.
    With backing, each line gets a background-colored rect so nothing shows through it.
    """
    attrs = (f' class="{cls}"' if cls else "") + (f' style="{style}"' if style else "")
    out = [f"<g{attrs}>"]
    for i, line in enumerate(lines):
        filled = [j for j, char in enumerate(line) if char != " "]
        if backing and filled:
            out.append(f'<rect x="{cx(col + filled[0]):.1f}" y="{ART_TOP + (row + i) * CH:.1f}" '
                       f'width="{(filled[-1] - filled[0] + 1) * CW}" height="{CH}" fill="url(#bg)"/>')
        runs, current, buf = [], None, ""
        for j, char in enumerate(line):
            color = color_of(i, j, char) if char != " " else current
            if color != current and buf:
                runs.append((current, buf))
                buf = ""
            current = color
            buf += char
        runs.append((current, buf))
        body = "".join(f'<tspan fill="{c or INK}">{esc(s)}</tspan>' for c, s in runs)
        out.append(f'<text x="{cx(col):.1f}" y="{cy(row + i):.1f}" font-size="{FONT_SIZE:.1f}" xml:space="preserve" '
                   f'textLength="{len(line) * CW}" lengthAdjust="spacingAndGlyphs">{body}</text>')
    out.append("</g>")
    return out


def paint_scenery(g):
    # Sun high on the right, with a sparse glow.
    sun_c, sun_r, radius = 170, 3, 30
    for r in range(HORIZON):
        for c in range(COLS):
            d = math.hypot((c - sun_c) * CW, (r - sun_r) * CH)
            if d < radius:
                g.put(r, c, "@" if d < radius * 0.55 else "#" if d < radius * 0.85 else "*", GOLD)
            elif d < radius * 1.9 and noise(r, c) < 0.3:
                g.put(r, c, "." if d > radius * 1.4 else ":", "#bb8009")

    def ridge(peaks, steepness):
        """Height (rows above the horizon) of a range built from (column, height) summits."""
        def h(c):
            top = max(hp - abs(c - pc) * steepness for pc, hp in peaks)
            return top + (noise(0, c) - 0.5) * 0.7
        return h

    back = ridge([(8, 9), (44, 12.5), (78, 10), (116, 13.5), (150, 9.5), (192, 11)], 0.42)
    front = ridge([(24, 5), (62, 6), (98, 4.5), (136, 6.5), (176, 5)], 0.28)

    # Shaded like the portrait: density carries the form, no outline characters.
    # The sun is to the right, so right-facing slopes are lit; snow caps the tall back peaks.
    ramp = " .,:;+*%#@"  # no - or =, which streak horizontally across a slope
    for height, base, color, snowy in [(back, 0.22, BACK_RANGE, True), (front, 0.4, FRONT_RANGE, False)]:
        for c in range(COLS):
            h = height(c)
            lit = height(c + 1) < height(c - 1)
            for r in range(HORIZON):
                above = HORIZON - r
                depth = h - above
                if depth < 0:
                    continue
                if snowy and h > 9 and depth < 2.2 + noise(r, c) * 0.8:
                    b = (0.85 if lit else 0.5) + (noise(r, c) - 0.5) * 0.15
                    g.put(r, c, ramp[max(2, min(9, int(b * 9 + 0.5)))], SNOW)
                    continue
                b = base + (0.2 if lit else -0.06) - min(depth, 6) * 0.015 + (noise(r, c) - 0.5) * 0.1
                g.put(r, c, ramp[max(1, min(9, int(b * 9 + 0.5)))], color)

    # Meadow between the range and the track.
    for r in range(HORIZON, GROUND):
        for c in range(COLS):
            if noise(r, c) < 0.07:
                g.put(r, c, "," if noise(c, r) < 0.5 else ".", "#2b4a33")

    def barn_color(i, j, char):
        if char in "[]":
            return GOLD
        if i >= 6 and char in "X\\/":
            return INK
        return BARN_RED

    g.sprite(BARN, GROUND - len(BARN), 2, barn_color)
    g.sprite(SILO, GROUND - len(SILO), 2 + len(BARN[0]), lambda i, j, ch: SOFT_INK if i < 2 else STEEL)

    for c in range(COLS):
        g.put(GROUND, c, "_" if noise(GROUND, c) < 0.6 else ".", SOIL)
        g.put(FENCE, c, "+" if c % 6 == 0 else "-", "#8b6f47")

    for r, c in [(5, 60), (6, 63), (4, 101), (8, 120)]:
        g.put(r, c, "v", MUTED)


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


def plot_rows(day_index):
    return FIELD_TOP + day_index * 2, FIELD_TOP + day_index * 2 + 1


def column_layer(col, cells, cls, delay):
    """One <text> per field column, holding a positioned <tspan> for each non-empty row."""
    spans = "".join(f'<tspan x="{cx(col):.1f}" y="{cy(r):.1f}" fill="{color}" textLength="{PLOT_W * CW}" '
                    f'lengthAdjust="spacingAndGlyphs">{esc(s)}</tspan>' for r, s, color in cells if s.strip())
    if not spans:
        return ""
    return (f'<text class="{cls}" font-size="{FONT_SIZE:.1f}" xml:space="preserve" '
            f'style="animation-delay:{delay:.2f}s">{spans}</text>')


def main():
    data = json.load(open(SRC))
    grid = weeks(data["days"])

    g = Grid()
    paint_scenery(g)

    labels = [(ci, datetime.date.fromisoformat(col[0]["date"]).strftime("%b"))
              for ci, col in enumerate(grid) if col[0] and int(col[0]["date"][8:]) <= 7 and ci < len(grid) - 2]
    for i, (ci, label) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - ci < 3:
            continue
        g.text(MONTHS, FIELD_C0 + ci * PLOT_W, label, MUTED)
    for d, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        g.text(plot_rows(d)[1], FIELD_C0 - 5, name, MUTED)

    tractor_w = len(TRACTOR[0]) * CW
    start_x = cx(2 + len(BARN[0]) + len(SILO[0]) + 1)
    end_x = cx(COLS - len(TRACTOR[0]) - 22)

    def till_time(col):
        progress = (cx(col) - start_x - tractor_w / 2) / (end_x - start_x)
        return DRIVE_START + DRIVE * min(max(progress, 0), 1)

    footer_top = ART_TOP + ROWS * CH + 18
    height = footer_top + 108
    css = CSS + (f"@keyframes drive{{to{{transform:translateX({end_x - start_x:.1f}px)}}}}"
                 f".tr{{animation:drive {DRIVE}s linear {DRIVE_START}s both}}")
    parts = window(W, height, f"~$ ./farm.sh --season {data['range']['end'][:4]}", scale=SCALE, css=css)

    # Scenery prints top to bottom under a scanline, like the portrait.
    for r in range(MONTHS + 1):
        parts.append(g.row_svg(r, PRINT_TIME * r / (MONTHS + 1)))
    parts.append(f'<rect class="sc tw" x="0" y="{ART_TOP}" width="{W}" height="3" fill="{CYAN}"/>')

    cloud_color = lambda i, j, ch: "#6e7681"
    parts += sprite_svg(CLOUD, 1, 40, cloud_color, cls="cl")
    parts += sprite_svg(CLOUD, 4, 128, cloud_color, cls="cl", style="animation-delay:-9s")

    # Field: grass -> soil -> crops, one column at a time behind the tractor.
    planted = 0
    for ci, column in enumerate(grid):
        col = FIELD_C0 + ci * PLOT_W
        when = till_time(col + 1)
        grass, soil, crops = [], [], []
        for d, day in enumerate(column):
            if not day:
                continue
            top, bottom = plot_rows(d)
            tex = lambda r: "".join("\"',"[int(noise(r, col + k) * 3)] if noise(r + 7, col + k) < 0.55 else " "
                                    for k in range(PLOT_W))
            grass += [(top, tex(top), UNTILLED), (bottom, tex(bottom), UNTILLED)]
            level = min(day["level"], 4)
            soil.append((bottom, "._." if not level else ". .", SOIL))
            if level:
                planted += 1
            if level == 1:
                crops.append((bottom, " , ", GREENS[0]))
            elif level == 2:
                crops += [(top, " v ", GREENS[1]), (bottom, " | ", GREENS[1])]
            elif level == 3:
                crops += [(top, "\\|/", GREENS[2]), (bottom, " | ", GREENS[2])]
            elif level == 4:
                crops += [(top, "\\¥/", GOLD), (bottom, " | ", GOLD)]
        parts.append(column_layer(col, grass, "u", when))
        parts.append(column_layer(col, soil, "o", when))
        parts.append(column_layer(col, crops, "g", when + 0.15))

    # Tractor with exhaust puffs, driving from the barn to the far end of the field.
    def tractor_color(i, j, ch):
        if i >= 4:
            return GOLD if ch in "o" else SOFT_INK
        return "#3fb950"

    tractor_row = GROUND - len(TRACTOR)
    parts.append(f'<g transform="translate({start_x - cx(0):.1f} 0)"><g class="tr">')
    parts += sprite_svg(TRACTOR, tractor_row, 0, tractor_color, backing=True)
    for k, delay in enumerate([0, 0.7, 1.4]):
        parts.append(f'<text class="pf" x="{cx(12):.1f}" y="{cy(tractor_row - 1):.1f}" fill="{STEEL}" '
                     f'font-size="{FONT_SIZE + k * 2:.1f}" style="animation-delay:{delay}s">{"oO°"[k]}</text>')
    parts.append("</g></g>")

    # The yard: two hens pecking in place, one wandering with her chick.
    def chicken_color(i, j, ch):
        return RED if i == 0 else GOLD if ch == ">" or i == 4 else INK

    def hen(col, delay, wander=False):
        head = sprite_svg(CHICKEN[:2], YARD_TOP, col, chicken_color, cls="p", style=f"animation-delay:{delay}s")
        body = sprite_svg(CHICKEN[2:], YARD_TOP + 2, col, lambda i, j, ch: chicken_color(i + 2, j, ch))
        return head + body

    grass_line = "".join("\"',."[int(noise(GRASS, c) * 4)] for c in range(COLS))
    parts.append(f'<text x="{X0}" y="{cy(GRASS):.1f}" fill="#2ea043" opacity="0.7" font-size="{FONT_SIZE:.1f}" '
                 f'xml:space="preserve" textLength="{COLS * CW}" lengthAdjust="spacingAndGlyphs">{esc(grass_line)}</text>')
    parts += hen(30, 0)
    parts.append('<g class="wa" style="animation-delay:-2s">')
    parts += hen(66, 0.9)
    parts += sprite_svg(CHICK, YARD_TOP + 3, 76, lambda i, j, ch: GOLD, cls="p", style="animation-delay:1.3s")
    parts.append("</g>")
    parts += hen(118, 1.6)
    parts += sprite_svg([": . : ."], YARD_TOP + 4, 38, lambda i, j, ch: "#bb8009")

    # Footer, in the same voice as the contributions card.
    parts.append(f'<line x1="{X0}" y1="{footer_top}" x2="{W - X0}" y2="{footer_top}" stroke="{FRAME}"/>')
    best = data["best_day"]
    best_date = datetime.date.fromisoformat(best["date"]).strftime("%b %-d, %Y")
    size, line1, line2 = 26, footer_top + 44, footer_top + 88
    parts.append(
        f'<text x="{X0}" y="{line1}" font-size="{size}" fill="{MUTED}"><tspan fill="{CYAN}">$</tspan> harvest '
        f'<tspan fill="{GOLD}" font-weight="700">{data["total_contributions"]:,}</tspan> commits from '
        f'<tspan fill="{INK}" font-weight="700">{planted}</tspan> planted days</text>')
    parts.append(f'<text x="{W - X0}" y="{line1}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">best yield '
                 f'<tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> on {esc(best_date)}</text>')
    legend = [("._.", SOIL, "soil"), (".,.", GREENS[0], "sprout"), (" v ", GREENS[1], "leaf"),
              ("\\|/", GREENS[2], "stalk"), ("\\¥/", GOLD, "ripe")]
    legend_svg = "  ".join(f'<tspan fill="{c}" font-weight="700">{esc(glyph)}</tspan> {name}' for glyph, c, name in legend)
    parts.append(f'<text x="{X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" xml:space="preserve">'
                 f'<tspan fill="{CYAN}">$</tspan> {legend_svg}</text>')
    parts.append(f'<text x="{W - X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">'
                 f'flock <tspan fill="{INK}" font-weight="700">3</tspan> + 1 chick &#183; on bug patrol</text>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
