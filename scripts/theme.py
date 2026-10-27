"""Shared palette and the terminal-window chrome every card is drawn inside."""
import html

USER = "raghavsaravanan"
PROMPT_USER = "raghav"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

BG_TOP = "#111722"
BG_BOTTOM = "#0b0f15"
PANEL = "#161b22"
FRAME = "#30363d"
MUTED = "#7d8590"
INK = "#e6edf3"
SOFT_INK = "#c9d1d9"
CYAN = "#22d3ee"
GREEN = "#39d353"
GOLD = "#f2cc60"
VIOLET = "#a78bfa"

GREENS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

TITLEBAR_H = 34

# GitHub runs CSS and SMIL inside <img> SVGs but never JavaScript, so every
# animation here is declarative and freezes on its final frame.
REDUCED_MOTION = (
    "@media (prefers-reduced-motion: reduce){"
    "*{animation:none!important;opacity:1!important;transform:none!important}}"
)


def esc(text):
    return html.escape(str(text), quote=True)


def window(width, height, title, scale=1.0, css=""):
    """Open an <svg> drawn as a dark terminal window. Returns a list of parts; close with '</svg>'."""
    bar = TITLEBAR_H * scale
    dot_r = 5.5 * scale
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f"<style>{css}{REDUCED_MOTION}</style>",
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/>'
        "</linearGradient></defs>",
        f'<rect width="{width}" height="{height}" rx="{12 * scale:.0f}" fill="url(#bg)"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="{12 * scale:.0f}" '
        f'fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{bar}" x2="{width}" y2="{bar}" stroke="{FRAME}"/>',
    ]
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{(20 + i * 18) * scale}" cy="{bar / 2}" r="{dot_r}" fill="{color}"/>')
    parts.append(
        f'<text x="{width / 2}" y="{bar / 2 + 4.5 * scale}" fill="{MUTED}" font-size="{13 * scale:.0f}" '
        f'text-anchor="middle">{esc(PROMPT_USER)}@github: {esc(title)}</text>'
    )
    return parts


def write(path, parts):
    svg = "".join(parts)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({len(svg) // 1024} KB)")
