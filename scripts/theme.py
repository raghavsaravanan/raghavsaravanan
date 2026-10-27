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

# GitHub runs CSS inside <img> SVGs but never JavaScript. SMIL also runs, but
# browsers don't reliably replay it once an image has been painted, so anything
# that has to end up visible is animated with CSS only.
# Under reduced motion: show final states, hide typing covers and count-up frames.
REDUCED_MOTION = (
    "@media (prefers-reduced-motion: reduce){"
    "*{animation:none!important;opacity:1!important;transform:none!important}"
    ".tw,.cf{display:none!important}}"
)


def esc(text):
    return html.escape(str(text), quote=True)


def gradient(height):
    """Background gradient in user space, so a cover rect filled with it matches the background exactly."""
    return (f'<defs><linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{height}">'
            f'<stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/>'
            "</linearGradient></defs>")


def type_in(uid, x, baseline, size, chars, char_w, start, per_char=0.03, cursor=INK, keep_cursor=False):
    """
    Typing effect for text already drawn at (x, baseline) with textLength == chars * char_w:
    a background-colored cover slides right one character at a time with a block cursor
    on its leading edge. Returns (css, svg) and the time typing finishes.
    """
    width = chars * char_w
    dur = chars * per_char
    done = start + dur
    top = baseline - size * 0.95
    height = size * 1.3
    cursor_y = top + size * 0.12
    # The cover is removed outright once typing ends rather than trusting its final
    # stepped position, which some browsers leave one character short.
    css = (f"@keyframes w{uid}{{from{{transform:translateX(0)}}to{{transform:translateX({width:.1f}px)}}}}"
           f"@keyframes g{uid}{{to{{opacity:0}}}}"
           f".w{uid}{{animation:w{uid} {dur:.2f}s steps({chars}) {start:.2f}s both,"
           f"g{uid} .01s {done:.2f}s forwards}}")
    svg = (f'<clipPath id="k{uid}"><rect x="{x - 2:.1f}" y="{top:.1f}" width="{width + char_w * 1.5 + 4:.1f}" '
           f'height="{height:.1f}"/></clipPath>'
           f'<g class="tw" clip-path="url(#k{uid})"><g class="w{uid}">'
           f'<rect x="{x - 1:.1f}" y="{top:.1f}" width="{width + char_w * 1.5 + 4:.1f}" height="{height:.1f}" fill="url(#bg)"/>'
           f'<rect x="{x:.1f}" y="{cursor_y:.1f}" width="{char_w * 0.9:.1f}" height="{size * 1.05:.1f}" '
           f'fill="{cursor}" opacity=".85"/></g></g>')
    if keep_cursor:
        css += (f"@keyframes b{uid}{{0%,49%{{opacity:.85}}50%,100%{{opacity:0}}}}"
                f".b{uid}{{opacity:0;animation:b{uid} 1s step-end {done:.2f}s infinite}}")
        svg += (f'<rect class="b{uid}" x="{x + width + char_w * 0.25:.1f}" y="{cursor_y:.1f}" '
                f'width="{char_w * 0.9:.1f}" height="{size * 1.05:.1f}" fill="{cursor}"/>')
    return css, svg, done


def window(width, height, title, scale=1.0, css=""):
    """Open an <svg> drawn as a dark terminal window. Returns a list of parts; close with '</svg>'."""
    bar = TITLEBAR_H * scale
    dot_r = 5.5 * scale
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f"<style>{css}{REDUCED_MOTION}</style>",
        gradient(height),
        f'<rect width="{width}" height="{height}" rx="{12 * scale:.0f}" fill="url(#bg)"/>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="{12 * scale:.0f}" '
        f'fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{bar}" x2="{width}" y2="{bar}" stroke="{FRAME}"/>',
    ]
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{(20 + i * 18) * scale}" cy="{bar / 2}" r="{dot_r}" fill="{color}"/>')
    label = f"{PROMPT_USER}@github: {title}"
    size = 13 * scale
    label_w = len(label) * size * 0.6
    # Centered, unless a long title would crowd the traffic-light dots.
    center = max(width / 2, (20 + 2 * 18 + 5.5) * scale + 16 * scale + label_w / 2)
    parts.append(
        f'<text x="{center:.1f}" y="{bar / 2 + 4.5 * scale}" fill="{MUTED}" font-size="{size:.0f}" '
        f'text-anchor="middle" textLength="{label_w:.1f}" lengthAdjust="spacingAndGlyphs">{esc(label)}</text>'
    )
    return parts


def write(path, parts):
    svg = "".join(parts)
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {path} ({len(svg) // 1024} KB)")
