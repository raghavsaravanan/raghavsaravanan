#!/usr/bin/env python3
"""
Render the stats card shown beside the ASCII portrait: six count-up tiles, a
language breakdown bar, and monthly contribution bars.

The canvas matches assets/portrait.svg (840 x 880) so the two line up when the
README shows them side by side at half size; font sizes assume that 0.5x scale.

    python scripts/render_stats.py
"""
import datetime
import json
import os

from theme import CYAN, FRAME, GOLD, GREEN, INK, MUTED, PANEL, TITLEBAR_H, VIOLET, esc, window, write

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "data", "stats.json")
OUT = os.path.join(ROOT, "assets", "stats.svg")

W, H = 840, 880
PAD, GAP = 20, 14
SCALE = 2
TILE_W = (W - PAD * 2 - GAP) / 2
TILE_H = 128
TILES_TOP = TITLEBAR_H * SCALE + PAD
LANG_TOP = TILES_TOP + 3 * TILE_H + 2 * GAP + GAP
LANG_H = 132
CHART_TOP = LANG_TOP + LANG_H + GAP
CHART_H = H - PAD - CHART_TOP

# GitHub's linguist colors, except Python and PLpgSQL, whose official blues are
# indistinguishable from TypeScript's in a thin bar.
LANG_COLORS = {"TypeScript": "#3178c6", "Python": "#ffd43b", "JavaScript": "#f1e05a", "CSS": "#c084fc",
               "HTML": "#e34c26", "PLpgSQL": "#2dd4bf", "Swift": "#f05138", "Shell": "#89e051"}
FALLBACK_COLORS = [CYAN, VIOLET, GOLD, GREEN, MUTED]

STAGGER, SLIDE, COUNT, FRAMES = 0.12, 0.45, 1.1, 18

CSS = (
    "@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}"
    f".t{{opacity:0;animation:rise {SLIDE}s ease-out both}}"
    "@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
    ".b{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .6s ease-out both}"
    "@keyframes wipe{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    ".w{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:wipe .5s ease-out both}"
    "@keyframes show{from,to{opacity:1}}"
    ".cf,.cl{opacity:0}"
)


def short(iso, year=False):
    return datetime.date.fromisoformat(iso).strftime("%b %-d, %Y" if year else "%b %-d")


def span(streak):
    return f"{short(streak['start'])} – {short(streak['end'])}" if streak["length"] else "start one today"


def count_up(x, y, value, suffix, color, start):
    """
    Pre-rendered frames easing out into the real number. Each in-between frame is
    visible only while its CSS animation runs; the final frame stays on.
    """
    is_float = isinstance(value, float)
    frame = COUNT / FRAMES
    out = []
    for k in range(1, FRAMES + 1):
        shown = value * (1 - (1 - k / FRAMES) ** 3)
        text = f"{shown:,.1f}" if is_float else f"{round(shown):,}"
        on = start + frame * (k - 1)
        if k < FRAMES:
            cls, style = "cf", f"animation:show {frame:.3f}s {on:.3f}s"
        else:
            cls, style = "cl", f"animation:show 1s {on:.3f}s forwards"
        out.append(f'<text class="{cls}" x="{x}" y="{y}" font-size="50" font-weight="700" fill="{color}" '
                   f'style="{style}">{text}<tspan font-size="22" font-weight="400" fill="{MUTED}">'
                   f'{esc(suffix)}</tspan></text>')
    return out


def panel(x, y, w, h, label):
    return [f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="10" fill="{PANEL}" stroke="{FRAME}"/>',
            f'<text x="{x + 22:.1f}" y="{y + 36}" fill="{MUTED}" font-size="21">'
            f'<tspan fill="{CYAN}">$</tspan> {esc(label)}</text>']


def main():
    data = json.load(open(SRC))
    repos = data["repos"]
    current, longest = data["current_streak"], data["longest_streak"]
    forks = repos["public_repos"] - repos["original_repos"]

    # The farm already headlines the yearly total and best day, so the card leads with momentum instead.
    this_month = data["monthly"][-1]
    month_name = datetime.date.fromisoformat(this_month["month"] + "-01").strftime("%B")
    active_share = data["active_days"] / len(data["days"])
    tiles = [
        ("this month", this_month["total"], "", f"contributions in {month_name}", GREEN),
        ("current streak", current["length"], " days", span(current), CYAN),
        ("active days", data["active_days"], "", f"{active_share:.0%} of the last year", GOLD),
        ("longest streak", longest["length"], " days", span(longest), INK),
        ("public repos", repos["public_repos"], "", f"{repos['original_repos']} original · {forks} forked", INK),
        ("avg / active day", data["avg_per_active_day"], "", "contributions", INK),
    ]

    parts = window(W, H, "~$ ./stats.sh", scale=SCALE, css=CSS)

    for i, (label, value, suffix, caption, color) in enumerate(tiles):
        x = PAD + (i % 2) * (TILE_W + GAP)
        y = TILES_TOP + (i // 2) * (TILE_H + GAP)
        start = i * STAGGER
        parts.append(f'<g class="t" style="animation-delay:{start:.2f}s">')
        parts += panel(x, y, TILE_W, TILE_H, label)
        parts += count_up(round(x + 22, 1), y + 88, value, suffix, color, start + SLIDE * 0.6)
        parts.append(f'<text x="{x + 22:.1f}" y="{y + 115}" fill="{MUTED}" font-size="18">{esc(caption)}</text>')
        parts.append("</g>")

    lang_start = len(tiles) * STAGGER + 0.3
    parts.append(f'<g class="t" style="animation-delay:{lang_start:.2f}s">')
    parts += panel(PAD, LANG_TOP, W - PAD * 2, LANG_H, "languages --top 5")
    bar_x, bar_y, bar_w = PAD + 22, LANG_TOP + 56, W - PAD * 2 - 44
    langs = repos["languages"]
    shown_total = sum(lang["share"] for lang in langs) or 1
    cursor = bar_x
    legend_x = bar_x
    for i, lang in enumerate(langs):
        color = LANG_COLORS.get(lang["name"], FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        seg = bar_w * lang["share"] / shown_total
        parts.append(f'<rect class="w" x="{cursor:.1f}" y="{bar_y}" width="{max(seg - 3, 2):.1f}" height="16" '
                     f'rx="4" fill="{color}" style="animation-delay:{lang_start + 0.3 + i * 0.12:.2f}s"/>')
        cursor += seg
        label = f"{lang['name']} {lang['share']:.0%}"
        parts.append(f'<circle cx="{legend_x + 6}" cy="{LANG_TOP + 103}" r="6" fill="{color}"/>')
        label_w = len(label) * 16 * 0.6
        parts.append(f'<text x="{legend_x + 18}" y="{LANG_TOP + 109}" fill="{INK}" font-size="16" '
                     f'textLength="{label_w:.1f}" lengthAdjust="spacingAndGlyphs">{esc(label)}</text>')
        legend_x += 18 + label_w + 22
    parts.append("</g>")

    chart_start = lang_start + 0.5
    parts.append(f'<g class="t" style="animation-delay:{chart_start:.2f}s">')
    parts += panel(PAD, CHART_TOP, W - PAD * 2, CHART_H, "contributions --per-month")
    parts.append("</g>")
    monthly = data["monthly"]
    plot_top, plot_bottom = CHART_TOP + 66, CHART_TOP + CHART_H - 40
    plot_left, plot_right = PAD + 22, W - PAD - 22
    slot = (plot_right - plot_left) / len(monthly)
    bar = slot * 0.6
    peak = max(m["total"] for m in monthly) or 1
    for i, month in enumerate(monthly):
        h = max(3, (plot_bottom - plot_top) * month["total"] / peak)
        x = plot_left + i * slot + (slot - bar) / 2
        delay = chart_start + 0.3 + i * 0.06
        color = GREEN if month["total"] == peak else "#26a641"
        parts.append(f'<rect class="b" x="{x:.1f}" y="{plot_bottom - h:.1f}" width="{bar:.1f}" height="{h:.1f}" '
                     f'rx="3" fill="{color}" style="animation-delay:{delay:.2f}s"/>')
        initial = datetime.date.fromisoformat(month["month"] + "-01").strftime("%b")[0]
        parts.append(f'<text x="{x + bar / 2:.1f}" y="{plot_bottom + 27}" fill="{MUTED}" font-size="17" '
                     f'text-anchor="middle">{initial}</text>')
        if month["total"]:
            parts.append(f'<text class="t" x="{x + bar / 2:.1f}" y="{plot_bottom - h - 9:.1f}" fill="{INK}" '
                         f'font-size="16" text-anchor="middle" style="animation-delay:{delay + 0.5:.2f}s">'
                         f'{month["total"]}</text>')
    parts.append("</svg>")
    write(OUT, parts)


if __name__ == "__main__":
    main()
