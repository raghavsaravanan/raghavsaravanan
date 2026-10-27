#!/usr/bin/env python3
"""
Render the last year of contributions as an ASCII crop field. A tractor leaves
the barn and drives across once, and each column of crops sprouts as it passes;
a small flock of chickens pecks along the bottom on a loop.

Each day is one plot, grown to GitHub's own contribution level for that day.

    python scripts/render_farm.py
"""
import datetime
import json
import os

from theme import CYAN, FRAME, GOLD, INK, MUTED, TITLEBAR_H, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "stats.json")
OUT = os.path.join(ROOT, "assets", "farm.svg")

STEP_X, STEP_Y = 15, 17
PAD = 24
DAY_LABEL_W = 32
ART = 12          # font size for the barn, tractor, mountains, and chickens
LINE = 13         # line height for that ASCII art
CHAR = ART * 0.6
CHICK_SIZE, CHICK_LINE = 14, 15

SOIL = "#6e5a3e"
UNTILLED = "#24452c"
CROPS = [(".", SOIL), (",", "#2ea043"), ("v", "#3fb950"), ("Y", "#56d364"), ("¥", GOLD)]
RED = "#ff7b72"

DRIVE = 4.5       # seconds for the tractor to cross the field

BARN = [
    "    ______",
    "   /\\     \\",
    "  /  \\_____\\",
    "  |[]| [] |",
    "  |__|_||_|",
]
SILO = [" _", "( )", "| |", "| |", "|_|"]
TRACTOR = [
    "   _|__",
    " _|  _ \\__",
    "|_|_| |___|",
    "(@)----(O)",
]
MOUNTAINS = [
    "          /\\                    /\\                         /\\        ",
    "    /\\   /  \\      /\\          /  \\    /\\        /\\       /  \\   /\\  ",
    "   /  \\_/    \\    /  \\   /\\  _/    \\  /  \\  /\\  /  \\  /\\_/    \\_/  \\ ",
]
CHICKEN = ["  \\\\", "  (o>", "\\\\_//)", " \\_/_)", "  _|_"]

CSS = (
    "@keyframes sprout{0%{opacity:0;transform:translateY(5px) scale(.4)}"
    "100%{opacity:1;transform:none}}"
    ".g{opacity:0;transform-box:fill-box;transform-origin:bottom;animation:sprout .5s ease-out both}"
    "@keyframes till{to{opacity:0}}"
    ".s{animation:till .25s ease-out both}"
    "@keyframes soil{from{opacity:0}to{opacity:1}}"
    ".t{opacity:0;animation:soil .25s ease-out both}"
    "@keyframes peck{0%,55%,100%{transform:none}65%,85%{transform:translate(4px,7px)}}"
    ".p{animation:peck 2.4s ease-in-out infinite}"
    "@keyframes wander{0%,100%{transform:none}50%{transform:translateX(26px)}}"
    ".w{animation:wander 9s ease-in-out infinite}"
)


def ascii_block(lines, x, y, fill, size=ART, line=LINE, cls="", style=""):
    attrs = f' class="{cls}"' if cls else ""
    attrs += f' style="{style}"' if style else ""
    out = [f"<g{attrs}>"]
    for i, text in enumerate(lines):
        out.append(f'<text x="{x}" y="{y + i * line}" fill="{fill}" font-size="{size}" '
                   f'xml:space="preserve">{esc(text)}</text>')
    out.append("</g>")
    return out


def chicken(x, y, delay, wander=False):
    """Comb and head peck together; the body stays planted."""
    head = [f'<g class="p" style="animation-delay:{delay:.2f}s">',
            f'<text x="{x}" y="{y}" fill="{RED}" font-size="{CHICK_SIZE}" xml:space="preserve">{esc(CHICKEN[0])}</text>',
            f'<text x="{x}" y="{y + CHICK_LINE}" fill="{INK}" font-size="{CHICK_SIZE}" xml:space="preserve">  (o'
            f'<tspan fill="{GOLD}">&gt;</tspan></text>',
            "</g>"]
    body = ascii_block(CHICKEN[2:4], x, y + 2 * CHICK_LINE, INK, CHICK_SIZE, CHICK_LINE)
    feet = ascii_block(CHICKEN[4:], x, y + 4 * CHICK_LINE, GOLD, CHICK_SIZE, CHICK_LINE)
    parts = head + body + feet
    if wander:
        parts = [f'<g class="w" style="animation-delay:{delay:.2f}s">'] + parts + ["</g>"]
    return parts


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
    grid = weeks(data["days"])
    width = PAD * 2 + DAY_LABEL_W + len(grid) * STEP_X
    field_left = PAD + DAY_LABEL_W

    scene_top = TITLEBAR_H + 18
    ground_y = scene_top + len(BARN) * LINE + 4
    month_y = ground_y + 26
    field_top = month_y + 14
    field_bottom = field_top + 7 * STEP_Y
    yard_top = field_bottom + 22
    footer_y = yard_top + len(CHICKEN) * CHICK_LINE + 26
    height = footer_y + 46

    parts = window(width, height, f"~$ ./farm.sh --season {data['range']['end'][:4]}", css=CSS)

    # Background range, then barn and silo on the left edge of the field.
    parts += ascii_block(MOUNTAINS, field_left + 120, scene_top + 6, FRAME)
    parts += ascii_block(BARN, PAD - 8, scene_top + LINE - 2, "#da7756")
    parts += ascii_block(SILO, PAD + len(BARN[2]) * CHAR - 4, scene_top + LINE - 2, MUTED)
    parts.append(f'<text x="{width - PAD - 40}" y="{scene_top + 14}" fill="{GOLD}" font-size="{ART + 2}" '
                 f'xml:space="preserve">\\ | /</text>')
    parts.append(f'<text x="{width - PAD - 40}" y="{scene_top + 14 + LINE}" fill="{GOLD}" font-size="{ART + 2}" '
                 f'xml:space="preserve">- O -</text>')

    fence = "+--" * ((width - PAD * 2) // int(CHAR * 3) + 1)
    parts.append(f'<text x="{PAD}" y="{ground_y + 10}" fill="{SOIL}" font-size="{ART}" '
                 f'textLength="{width - PAD * 2}" lengthAdjust="spacing">{fence}</text>')

    # Tractor drives from the barn to the far end and parks there.
    tractor_w = max(len(line) for line in TRACTOR) * CHAR
    start_x = PAD + len(BARN[2]) * CHAR + 30
    end_x = width - PAD - tractor_w - 50
    tractor_y = ground_y - (len(TRACTOR) - 1) * LINE + 2
    parts.append('<g><animateTransform attributeName="transform" type="translate" '
                 f'from="{start_x} 0" to="{end_x} 0" begin="0.3s" dur="{DRIVE}s" fill="freeze"/>')
    parts += ascii_block(TRACTOR[:3], 0, tractor_y, "#3fb950")
    parts += ascii_block(TRACTOR[3:], 0, tractor_y + 3 * LINE, INK)
    parts.append("</g>")

    def arrival(x):
        """When the middle of the tractor passes x; the drive is linear so this stays in sync."""
        progress = (x - start_x - tractor_w / 2) / (end_x - start_x)
        return 0.3 + DRIVE * min(max(progress, 0), 1)

    labels = [(ci, datetime.date.fromisoformat(col[0]["date"]).strftime("%b"))
              for ci, col in enumerate(grid)
              if col[0] and int(col[0]["date"][8:]) <= 7 and ci < len(grid) - 2]
    for i, (ci, label) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - ci < 3:
            continue
        parts.append(f'<text x="{field_left + ci * STEP_X}" y="{month_y}" fill="{MUTED}" font-size="11">{label}</text>')

    for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(f'<text x="{PAD}" y="{field_top + row * STEP_Y + 12}" fill="{MUTED}" font-size="10">{name}</text>')

    # Each column starts as untilled grass; the tractor turns it to soil and the
    # day's crop sprouts right behind it.
    planted = 0
    soil_char, soil_color = CROPS[0]
    for ci, column in enumerate(grid):
        x = field_left + ci * STEP_X + 3
        till_at = arrival(x)
        rows = [(ri, day, field_top + ri * STEP_Y + 13) for ri, day in enumerate(column) if day]
        parts.append(f'<g class="s" style="animation-delay:{till_at:.2f}s">')
        parts += [f'<text x="{x}" y="{y}" fill="{UNTILLED}" font-size="15">"</text>' for _, _, y in rows]
        parts.append(f'</g><g class="t" style="animation-delay:{till_at:.2f}s">')
        parts += [f'<text x="{x}" y="{y}" fill="{soil_color}" font-size="15">{soil_char}</text>'
                  for _, day, y in rows if not day["level"]]
        parts.append("</g>")
        for ri, day, y in rows:
            level = min(day["level"], 4)
            if not level:
                continue
            planted += 1
            char, color = CROPS[level]
            parts.append(f'<text class="g" x="{x}" y="{y}" fill="{color}" font-size="15" font-weight="700" '
                         f'style="animation-delay:{till_at + 0.15 + ri * 0.03:.2f}s">{esc(char)}</text>')

    # The flock: two peck in place, one wanders the yard.
    grass = "\"'.,\"'.," * 20
    parts.append(f'<text x="{PAD}" y="{yard_top + len(CHICKEN) * CHICK_LINE - 8}" fill="#2ea043" font-size="{ART}" '
                 f'opacity="0.6" textLength="{width - PAD * 2}" lengthAdjust="spacing">{esc(grass)}</text>')
    parts += chicken(field_left + 30, yard_top, 0.0)
    parts += chicken(field_left + 170, yard_top, 0.9, wander=True)
    parts += chicken(field_left + 330, yard_top, 1.6)
    parts.append(f'<text x="{field_left + 88}" y="{yard_top + 4 * CHICK_LINE}" fill="{GOLD}" font-size="{ART}">: . :</text>')

    legend = "  ".join(f"{c} {name}" for (c, _), name in zip(CROPS, ["soil", "sprout", "leaf", "stalk", "ripe"]))
    parts.append(f'<text x="{width - PAD}" y="{yard_top + 12}" fill="{MUTED}" font-size="11" text-anchor="end" '
                 f'xml:space="preserve">{esc(legend)}</text>')

    parts.append(f'<line x1="{PAD}" y1="{footer_y - 20}" x2="{width - PAD}" y2="{footer_y - 20}" stroke="{FRAME}"/>')
    best = data["best_day"]
    best_date = datetime.date.fromisoformat(best["date"]).strftime("%b %-d, %Y")
    parts.append(
        f'<text x="{PAD}" y="{footer_y + 6}" font-size="14" fill="{MUTED}"><tspan fill="{CYAN}">$</tspan> harvest '
        f'<tspan fill="{GOLD}" font-weight="700">{data["total_contributions"]:,}</tspan> commits from '
        f'<tspan fill="{INK}" font-weight="700">{planted}</tspan> planted days  &#183;  best yield '
        f'<tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> on {esc(best_date)}</text>'
    )
    parts.append(f'<text x="{width - PAD}" y="{footer_y + 6}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'flock <tspan fill="{INK}" font-weight="700">3</tspan> &#183; on bug patrol</text>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
