#!/usr/bin/env python3
"""
Paint the farm's landscape as a smooth, lit grayscale image, then
convert it to ASCII with the portrait's density ramp, so the farm and the
portrait share one look. Writes data/farm_scene.json for render_farm.py.

The scene doesn't depend on contribution data, so like the portrait it only
needs rerunning when the art changes, and the daily workflow stays stdlib-only.

    pip install -r scripts/requirements-portrait.txt
    python scripts/make_farm_scene.py
"""
import json
import os

import cv2
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "farm_scene.json")

COLS, ROWS = 200, 30          # scene size in characters
CW, CH = 8, 15                # pixels per character, matching render_farm.py
RAMP = " .:;+*o#%@"           # brighter prints denser; no - or =, which streak across slopes

# Region labels, mapped to colors in render_farm.py.
SKY, SUN, FAR, SNOW, HILL, MEADOW, TREE, BARN, ROOF, WINDOW, DOOR, SILO = range(12)
NAMES = ["sky", "sun", "far", "snow", "hill", "meadow", "tree", "barn", "roof", "window", "door", "silo"]


def noise1d(n, step, seed):
    """Piecewise-linear value noise: sharp enough for ridgelines, smooth between control points."""
    rng = np.random.default_rng(seed)
    xs = np.arange(0, n + step, step)
    return np.interp(np.arange(n), xs, rng.random(len(xs)))


def ridge(n, base, amps, steps, seed):
    y = np.full(n, float(base))
    for i, (amp, step) in enumerate(zip(amps, steps)):
        y -= amp * noise1d(n, step, seed + i)
    return y


def to_ascii(lum, label, cols, rows, gamma=1.0):
    small = cv2.resize(lum, (cols, rows), interpolation=cv2.INTER_AREA)
    ys = ((np.arange(rows) + 0.5) * lum.shape[0] / rows).astype(int)
    xs = ((np.arange(cols) + 0.5) * lum.shape[1] / cols).astype(int)
    labels = label[np.ix_(ys, xs)]
    lines, colors = [], []
    for r in range(rows):
        line, row_colors = [], []
        for c in range(cols):
            v = float(small[r, c]) ** gamma
            idx = int(v * (len(RAMP) - 1) + 0.5)
            char = RAMP[max(0, min(len(RAMP) - 1, idx))] if v > 0.04 else " "
            line.append(char)
            row_colors.append(NAMES[labels[r, c]] if char != " " else "")
        lines.append("".join(line))
        colors.append(row_colors)
    return lines, colors


def mountains(w, h, xx, yy, peaks, snowline, seed):
    """
    A range of distinct peaks. Each summit's west face is in shadow and its east
    face catches the sun (which sits to the right); snow covers everything above
    a jagged snowline. Returns (inside, luminance, snowy).
    """
    jag = 6 * (noise1d(w, 9, seed) - 0.5) + 3 * (noise1d(w, 4, seed + 1) - 0.5)
    profiles = np.stack([top + abs_slope * np.abs(np.arange(w) - x) ** 1.08 for x, top, abs_slope in peaks])
    ridge_y = profiles.min(axis=0) + jag
    owner = profiles.argmin(axis=0)
    summit_x = np.array([peaks[i][0] for i in owner])
    lit = (np.arange(w) > summit_x)[None, :]
    inside = yy >= ridge_y[None, :]
    depth = (yy - ridge_y[None, :]).clip(0)
    streaks = noise1d(w, 6, seed + 2)[None, :] - 0.5
    rock = np.where(lit, 0.5, 0.2) + 0.08 * streaks - 0.0016 * depth
    line = snowline + 14 * (noise1d(w, 11, seed + 3)[None, :] - 0.5)
    snowy = inside & (yy < line)
    lum = np.where(snowy, np.where(lit, 0.95, 0.58), rock)
    # A thin bright crest along the sunlit ridgeline reads as a sharp edge.
    lum = np.where(inside & lit & (depth < 3) & ~snowy, lum + 0.18, lum)
    return inside, lum.clip(0.08, 1).astype(np.float32), snowy


def landscape():
    w, h = COLS * CW, ROWS * CH
    lum = np.zeros((h, w), np.float32)
    label = np.full((h, w), SKY, np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]

    def paint(mask, value, region):
        nonlocal lum
        lum = np.where(mask, value, lum)
        label[mask] = region

    # Sun with a soft glow, high on the right.
    d = np.hypot(xx - 1440, yy - 70)
    glow = np.where(d < 40, 1.0, 0.38 * np.exp(-(d - 40) / 20)).astype(np.float32)
    paint(glow > 0.1, glow, SUN)

    # Distant range: lower and dimmer, for depth.
    inside, rock, snowy = mountains(w, h, xx, yy, [(120, 200, 0.75), (420, 185, 0.7), (760, 210, 0.8),
                                                   (1080, 190, 0.72), (1500, 205, 0.75)], 212, seed=40)
    paint(inside, rock * 0.55, FAR)
    paint(snowy, rock * 0.75, SNOW)

    # Main range: a few big, distinct summits.
    inside, rock, snowy = mountains(w, h, xx, yy, [(260, 95, 1.05), (640, 55, 0.95), (1000, 110, 1.1),
                                                   (1300, 80, 1.0)], 148, seed=50)
    paint(inside, rock, FAR)
    paint(snowy, rock, SNOW)

    # Rolling foothills, smooth and dark.
    near = cv2.GaussianBlur(ridge(w, 318, [36, 12], [320, 130], seed=21).reshape(1, -1).astype(np.float32),
                            (0, 0), 12).ravel()
    nslope = np.gradient(near)
    depth = yy - near[None, :]
    hills = depth >= 0
    paint(hills, (0.2 + 0.1 * np.tanh(nslope * 3)[None, :] - 0.001 * depth).clip(0.07, 1).astype(np.float32), HILL)

    # Meadow along the bottom, where the farm stands.
    meadow = yy >= 338
    paint(meadow, (0.06 + 0.03 * noise1d(w, 5, seed=31)[None, :]).astype(np.float32) * np.ones_like(lum), MEADOW)

    base = h - 2
    # Pines in two clusters, lit from the right.
    for cx, hgt in [(262, 92), (292, 120), (326, 84), (356, 104), (1050, 96), (1084, 124), (1120, 88)]:
        t = (base - yy) / hgt
        tri = (t >= 0) & (t <= 1) & (np.abs(xx - cx) <= hgt * 0.3 * (1 - t) + 2)
        paint(tri, np.where(xx > cx, 0.55, 0.28).astype(np.float32), TREE)

    # Barn: shaded walls, gambrel roof, dark doors with a bright cross brace, glowing loft window.
    left, right, eave, ridge_y = 30, 200, base - 92, base - 150
    mid = (left + right) // 2
    walls = (xx >= left) & (xx <= right) & (yy >= eave) & (yy <= base)
    paint(walls, np.where(xx > mid, 0.62, 0.42).astype(np.float32), BARN)
    roof = np.zeros((h, w), np.uint8)
    cv2.fillPoly(roof, [np.array([[left - 10, eave + 2], [left + 14, eave - 38], [mid, ridge_y],
                                   [right - 14, eave - 38], [right + 10, eave + 2]], np.int32)], 1)
    paint(roof.astype(bool), np.where(xx > mid, 0.82, 0.6).astype(np.float32), ROOF)
    door = (xx >= mid - 30) & (xx <= mid + 30) & (yy >= base - 58) & (yy <= base)
    paint(door, np.float32(0.12), DOOR)
    brace = np.zeros((h, w), np.uint8)
    for (x1, y1, x2, y2) in [(mid - 30, base - 58, mid + 30, base), (mid + 30, base - 58, mid - 30, base)]:
        cv2.line(brace, (x1, y1), (x2, y2), 1, 4)
    paint(brace.astype(bool) & door, np.float32(0.85), BARN)
    loft = (xx >= mid - 14) & (xx <= mid + 14) & (yy >= eave - 30) & (yy <= eave - 8)
    paint(loft, np.float32(0.97), WINDOW)

    # Silo: a cylinder shaded across its width, with hoops and a dome.
    scx, sr, stop = 232, 22, base - 190
    cyl = 0.22 + 0.6 * np.clip(np.cos((xx - scx - 8) / sr * np.pi / 2), 0, 1)
    body = (np.abs(xx - scx) <= sr) & (yy >= stop) & (yy <= base)
    hoops = (yy - stop) % 30 < 3
    paint(body, np.where(hoops, cyl * 0.55, cyl).astype(np.float32), SILO)
    dome = (np.hypot(xx - scx, (yy - stop) * 1.15) <= sr) & (yy < stop)
    paint(dome, (cyl * 1.15).clip(0, 1).astype(np.float32), SILO)

    return to_ascii(lum, label, COLS, ROWS)


def main():
    scene, scene_colors = landscape()
    with open(OUT, "w") as f:
        json.dump({"cols": COLS, "rows": ROWS, "scene": scene, "scene_colors": scene_colors}, f)
    print(f"wrote {OUT}")
    print("\n".join(scene))


if __name__ == "__main__":
    main()
