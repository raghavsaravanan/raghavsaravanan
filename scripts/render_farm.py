#!/usr/bin/env python3
"""
Render the last year of contributions as an ASCII farm in the portrait's style.

The landscape (mountains, sun, pines, barn, silo) comes from
data/farm_scene.json, painted and converted to ASCII by make_farm_scene.py.
The scenery prints in under a scanline, then the tractor starts doing laps of the
field. On its quick first pass each week's column turns from grass to seed beds in
GitHub's contribution greens, each with a crop that grows with the day's level. After that it keeps
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
FIELD_TOP = MONTHS + 2               # 14 text rows = 7 day rows of PITCH_Y; a row of air above
YARD_TOP = FIELD_TOP + 14 + 1
GRASS = YARD_TOP + 5
ROWS = GRASS + 1
# The field is laid out in pixels, not on the text grid, so the beds come out square
# like GitHub's: the horizontal pitch fits however many weeks the year spans.
PITCH_Y = 2 * CH
DAY_LABEL_W = 44
GAP = 4

UNTILLED = "#2b4a33"
# GitHub's own contribution greens, so the field reads like the graph every visitor
# already knows. Days with no contributions are bare soil.
BEDS = ["#3a2f23", "#0e4429", "#006d32", "#26a641", "#39d353"]
CROPS = ["", ",", "v", "Y", "\u00a5"]   # a crop on each bed that grows with the level
RED = "#ff7b72"

SCENE_COLORS = {
    "sun": GOLD, "far": "#8b949e", "snow": INK, "hill": "#6e7681", "meadow": "#3d5a45",
    "tree": "#2ea043", "barn": "#e5534b", "roof": "#f47067", "window": GOLD, "door": "#a0413b",
    "silo": "#adbac7", "trim": INK,
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
HAY = ["    ____", "   (____)", " ____(____)", "(____)(____)"]

PRINT_TIME = 1.2
DRIVE_START = PRINT_TIME + 0.1
FIRST_LAP = 5.0                      # a brisk first pass tills the field, so the graph appears quickly
LAP = 9.0                            # then it cruises
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


def main():
    data = json.load(open(SRC))
    scene = json.load(open(SCENE))
    grid = weeks(data["days"])
    cols = scene["cols"]
    width = X0 * 2 + cols * CW

    # Field geometry: square beds on a pixel pitch that fits the year's week count.
    art_w = cols * CW
    pitch_x = min(PITCH_Y, int((art_w - DAY_LABEL_W) / len(grid)))
    bed = pitch_x - GAP
    field_w = len(grid) * pitch_x - GAP
    field_x0 = cx(0) + (art_w - DAY_LABEL_W - field_w) / 2 + DAY_LABEL_W
    field_y0 = ART_TOP + FIELD_TOP * CH

    # The tractor laps from just off the left edge of the scene to just off the right.
    # It's drawn at its parked spot and animated relative to it, so with reduced motion
    # (which strips transforms) it simply stays parked.
    tractor_w = len(TRACTOR[0]) * CW
    park_x = cx(TRACTOR_PARK_C)
    enter_x, exit_x = cx(0) - tractor_w, cx(cols)

    def till_time(x):
        """When the middle of the tractor first passes x, on the quick first lap."""
        progress = (x - enter_x - tractor_w / 2) / (exit_x - enter_x)
        return DRIVE_START + FIRST_LAP * progress

    footer_top = ART_TOP + ROWS * CH + 18
    height = footer_top + 108
    drive = (f"from{{transform:translateX({enter_x - park_x:.1f}px)}}"
             f"to{{transform:translateX({exit_x - park_x:.1f}px)}}")
    css = CSS + (f"@keyframes drive{{{drive}}}"
                 f".tr{{animation:drive {FIRST_LAP}s linear {DRIVE_START}s 1 both,"
                 f"drive {LAP}s linear {DRIVE_START + FIRST_LAP}s infinite}}")
    parts = window(width, height, f"~$ ./farm.sh --season {data['range']['end'][:4]}", scale=SCALE, css=css)

    # Scenery prints top to bottom under a scanline, like the portrait.
    for r, (line, colors) in enumerate(zip(scene["scene"], scene["scene_colors"])):
        parts.append(line_svg(list(line), [SCENE_COLORS.get(c) for c in colors], 0, r, cls="r",
                              style=f"animation-delay:{PRINT_TIME * r / SCENE_ROWS:.3f}s"))
    parts.append(f'<rect class="sc tw" x="0" y="{ART_TOP}" width="{width}" height="3" fill="{CYAN}"/>')

    labels = [(ci, datetime.date.fromisoformat(col[0]["date"]).strftime("%b"))
              for ci, col in enumerate(grid) if col[0] and int(col[0]["date"][8:]) <= 7 and ci < len(grid) - 2]
    for i, (ci, label) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - ci < 3:
            continue
        parts.append(f'<text x="{field_x0 + ci * pitch_x:.1f}" y="{field_y0 - 12:.1f}" fill="{MUTED}" '
                     f'font-size="22">{label}</text>')
    for d, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(f'<text x="{field_x0 - 10:.1f}" y="{field_y0 + d * PITCH_Y + PITCH_Y / 2 + 7:.1f}" '
                     f'fill="{MUTED}" font-size="20" text-anchor="end">{name}</text>')

    # Field: untilled grass until the tractor's first pass, then each day's seed bed in its
    # contribution color with a crop that grows with the level. The best day gets a gold ring.
    best = data["best_day"]
    planted = 0
    crop_size = round(bed * 0.72)
    for ci, column in enumerate(grid):
        x = field_x0 + ci * pitch_x
        when = till_time(x + bed / 2)
        grass, beds = [], []
        for d, day in enumerate(column):
            if not day:
                continue
            y = field_y0 + d * PITCH_Y + (PITCH_Y - bed) / 2
            tuft = "'" if noise(d, ci) < 0.5 else '"'
            grass.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bed}" height="{bed}" rx="4" fill="{UNTILLED}" '
                         f'opacity=".45"/><text x="{x + bed / 2:.1f}" y="{y + bed * 0.8:.1f}" fill="#3d6b47" '
                         f'font-size="{crop_size}" text-anchor="middle">{tuft}</text>')
            level = min(day["level"], 4)
            planted += bool(level)
            ring = f' stroke="{GOLD}" stroke-width="3"' if day["date"] == best["date"] else ""
            beds.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bed}" height="{bed}" rx="4" fill="{BEDS[level]}"{ring}>'
                        f'<title>{day["count"]} contributions on {day["date"]}</title></rect>')
            if level:
                beds.append(f'<text x="{x + bed / 2:.1f}" y="{y + bed * 0.74:.1f}" fill="#e6ffec" opacity=".85" '
                            f'font-size="{crop_size}" font-weight="700" text-anchor="middle">{CROPS[level]}</text>')
        parts.append(f'<g class="u tw" style="animation-delay:{when:.2f}s">{"".join(grass)}</g>')
        parts.append(f'<g class="g" style="animation-delay:{when + 0.12:.2f}s">{"".join(beds)}</g>')

    # Tractor, driving along the meadow from beside the barn to the far end, puffing exhaust.
    def tractor_color(i, j, ch):
        if i >= 4:
            return GOLD if ch in "o+" else SOFT_INK
        return "#3fb950"

    tractor_row = SCENE_ROWS - len(TRACTOR)
    hubs = TRACTOR.index(next(line for line in TRACTOR if "(o)" in line))
    spun = TRACTOR[hubs].replace("(o)", "(+)")
    hub_color = lambda i, j, ch: tractor_color(hubs, j, ch)
    parts.append(f'<clipPath id="lane"><rect x="{cx(0)}" y="{ART_TOP}" width="{cols * CW}" '
                 f'height="{SCENE_ROWS * CH}"/></clipPath>')
    parts.append('<g clip-path="url(#lane)"><g class="tr">')
    frame = [line if i != hubs else " " * len(line) for i, line in enumerate(TRACTOR)]
    parts += sprite_svg(frame, tractor_row, TRACTOR_PARK_C, tractor_color, backing=True)
    # Hubs alternate between (o) and (+) so the wheels look like they're turning.
    parts += sprite_svg([TRACTOR[hubs]], tractor_row + hubs, TRACTOR_PARK_C, hub_color, cls="ha", backing=True)
    parts += sprite_svg([spun], tractor_row + hubs, TRACTOR_PARK_C, hub_color, cls="hb cf", backing=True)
    exhaust = TRACTOR[0].index("|")
    for k, delay in enumerate([0, 0.7, 1.4]):
        parts.append(f'<text class="pf tw" x="{cx(TRACTOR_PARK_C + exhaust):.1f}" y="{cy(tractor_row - 1):.1f}" '
                     f'fill="#8b949e" font-size="{FONT_SIZE + k * 2:.1f}" style="animation-delay:{delay}s">'
                     f'{"oO°"[k]}</text>')
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
    parts += sprite_svg(HAY, YARD_TOP + 1, 160, lambda i, j, ch: "#d29922")

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
    # textLength pins the label's width so the legend swatches land right after it in any font.
    parts.append(f'<text x="{X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" xml:space="preserve" '
                 f'textLength="{6 * char:.1f}" lengthAdjust="spacingAndGlyphs"><tspan fill="{CYAN}">$</tspan> less</text>')
    lx = X0 + char * 7
    for level, color in enumerate(BEDS):
        parts.append(f'<rect x="{lx:.1f}" y="{line2 - bed + 4:.1f}" width="{bed}" height="{bed}" rx="4" fill="{color}"/>')
        if level:
            parts.append(f'<text x="{lx + bed / 2:.1f}" y="{line2 - bed + 4 + bed * 0.74:.1f}" fill="#e6ffec" '
                         f'opacity=".85" font-size="{crop_size}" font-weight="700" text-anchor="middle">{CROPS[level]}</text>')
        lx += bed + 6
    parts.append(f'<text x="{lx + 6:.1f}" y="{line2}" font-size="{size - 2}" fill="{MUTED}">more  &#183;  one bed per day</text>')
    parts.append(f'<text x="{width - X0}" y="{line2}" font-size="{size - 2}" fill="{MUTED}" text-anchor="end">'
                 f'flock <tspan fill="{INK}" font-weight="700">3</tspan> + 1 chick &#183; on bug patrol</text>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
