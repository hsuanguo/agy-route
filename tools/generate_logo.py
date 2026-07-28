#!/usr/bin/env python3
"""Generate the agy-route logo (assets/logo.svg + assets/icon.svg).

Style mirrors https://github.com/hsuanguo/act-cli/blob/main/assets/logo.svg :
a horizontal lockup (icon + wordmark) in a single SVG, with a CSS-driven
fill that flips black ↔ near-white between light and dark color schemes.

Run from the repo root:

    python3 tools/generate_logo.py

Writes:
    assets/logo.svg   # horizontal lockup, 640×128
    assets/icon.svg   # icon only, 512×512 (favicon / social-card use)

Re-run after any letterform tweak; the file is fully derived from this
script and is checked into the repo.
"""
from __future__ import annotations

from pathlib import Path

CELL = 10  # px per pixel-cell in the wordmark
LETTER_GAP_CELLS = 1  # 1 cell gap between letters (matches act-cli)


# Each letter is a list of (col, row) cells that should be filled, on a
# 5-col × 7-row grid (with `width` overriding 5 for narrower letters like
# `t`, `r`, `-`). y is from the top.
LETTERS: dict[str, tuple[int, list[tuple[int, int]]]] = {
    "a": (
        5,
        [
            (1, 0), (2, 0), (3, 0),
            (0, 1), (4, 1),
            (0, 2), (4, 2),
            (0, 3), (1, 3), (2, 3), (3, 3), (4, 3),
            (0, 4), (4, 4),
            (0, 5), (4, 5),
            (0, 6), (4, 6),
        ],
    ),
    "g": (
        5,
        [
            (1, 0), (2, 0), (3, 0),
            (0, 1), (4, 1),
            (0, 2), (4, 2),
            (0, 3), (4, 3),
            (1, 4), (2, 4), (3, 4), (4, 4),
            (0, 5), (4, 5),
            (1, 6), (2, 6), (3, 6),
        ],
    ),
    "y": (
        5,
        [
            (0, 0), (4, 0),
            (0, 1), (4, 1),
            (0, 2), (4, 2),
            (1, 3), (2, 3), (3, 3),
            (4, 4),
            (4, 5),
            (1, 6), (2, 6), (3, 6),
        ],
    ),
    "-": (
        3,
        [
            (0, 3), (1, 3), (2, 3),
        ],
    ),
    "r": (
        4,
        [
            (0, 0), (1, 0),
            (0, 1), (1, 1), (3, 1),
            (0, 2), (3, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
        ],
    ),
    "o": (
        5,
        [
            (1, 0), (2, 0), (3, 0),
            (0, 1), (4, 1),
            (0, 2), (4, 2),
            (0, 3), (4, 3),
            (0, 4), (4, 4),
            (0, 5), (4, 5),
            (1, 6), (2, 6), (3, 6),
        ],
    ),
    "u": (
        5,
        [
            (0, 0), (4, 0),
            (0, 1), (4, 1),
            (0, 2), (4, 2),
            (0, 3), (4, 3),
            (0, 4), (4, 4),
            (0, 5), (4, 5),
            (1, 6), (2, 6), (3, 6),
        ],
    ),
    "t": (
        3,
        [
            (1, 0),
            (1, 1),
            (0, 2), (1, 2), (2, 2),
            (1, 3),
            (1, 4),
            (1, 5),
            (1, 6), (2, 6),
        ],
    ),
    "e": (
        5,
        [
            (1, 0), (2, 0), (3, 0),
            (0, 1), (4, 1),
            (0, 2), (4, 2),
            (0, 3), (1, 3), (2, 3), (3, 3), (4, 3),
            (0, 4),
            (0, 5),
            (1, 6), (2, 6), (3, 6),
        ],
    ),
}


def render_wordmark(text: str) -> tuple[str, int, int]:
    """Render `text` as a single SVG <path d="…">. Returns (d_attr, w, h) in px.

    Caller wraps the result in a `<g class="logo-fill">` (or applies
    `fill="currentColor"` directly). The path itself uses no fill attr.
    """
    pieces: list[str] = []
    x_cursor = 0  # cell units
    max_w_cells = 0
    for ch in text:
        if ch not in LETTERS:
            raise KeyError(f"no glyph defined for {ch!r}")
        width, cells = LETTERS[ch]
        if x_cursor > 0:
            x_cursor += LETTER_GAP_CELLS
        for col, row in cells:
            x = (x_cursor + col) * CELL
            y = row * CELL
            # Each cell: Mx,y h10 v10 h-10 z
            pieces.append(f"M{x},{y}h10v10h-10z")
        x_cursor += width
        max_w_cells = x_cursor
    width_px = max_w_cells * CELL
    height_px = 7 * CELL
    return "".join(pieces), width_px, height_px


def render_icon() -> str:
    """A 512×512 routing icon: input bar → junction node → two branches.

    Drawn entirely with rounded rects, no transforms, so the path data is
    straightforward and copy-pasteable. Themed "split-route" — fits the
    project name (agy-route: one CLI, many routes).

    Each rect uses `fill="currentColor"` so the wrapping <style> block
    can flip the fill via `prefers-color-scheme` without any class
    selectors getting in the way.
    """
    f = ' fill="currentColor"'
    parts = [
        # input bar (left)
        f'<rect x="64" y="240" width="160" height="32" rx="4"{f}/>',
        # junction node (center)
        f'<rect x="224" y="224" width="64" height="64" rx="8"{f}/>',
        # branch stem (center → up): vertical segment
        f'<rect x="288" y="128" width="32" height="96"{f}/>',
        # branch stem (center → up): horizontal segment
        f'<rect x="320" y="128" width="128" height="32"{f}/>',
        # branch stem (center → down): vertical segment
        f'<rect x="288" y="288" width="32" height="96"{f}/>',
        # branch stem (center → down): horizontal segment
        f'<rect x="320" y="352" width="128" height="32"{f}/>',
    ]
    return "".join(parts)


CSS = """
    .logo-fill { color: #000000; }
    @media (prefers-color-scheme: dark) {
      .logo-fill { color: #e6edf3; }
    }
"""


def build_logo_svg() -> str:
    wordmark_d, wm_w, wm_h = render_wordmark("agy-route")
    icon = render_icon()
    # Icon is 112×112 placed at (24, 8) — matches act-cli's geometry.
    # Wordmark is 460×70 placed at (152, 29). Scale wordmark to fit.
    # Our wordmark is sized for 480×70 by default; we size to 460×70 to
    # match act-cli's wordmark box width.
    wm_box_w = 460
    wm_box_h = 70
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 128" role="img" aria-labelledby="title desc">
  <title id="title">agy-route horizontal lockup</title>
  <desc id="desc">Icon left, wordmark right. Fill flips in dark mode via prefers-color-scheme.</desc>
  <defs>
    <style type="text/css"><![CDATA[
{CSS}    ]]></style>
  </defs>
  <rect width="640" height="128" fill="none"/>
  <svg x="24" y="8" width="112" height="112" viewBox="0 0 512 512" aria-hidden="true">
    <g class="logo-fill">{icon}</g>
  </svg>
  <svg x="152" y="29" width="{wm_box_w}" height="{wm_box_h}" viewBox="0 0 {wm_w} {wm_h}" aria-hidden="true">
    <g class="logo-fill" fill="currentColor"><path d="{wordmark_d}"/></g>
  </svg>
</svg>
"""


def build_icon_svg() -> str:
    icon = render_icon()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-labelledby="title desc">
  <title id="title">agy-route icon</title>
  <desc id="desc">A split-route icon: input bar, junction node, two branches.</desc>
  <defs>
    <style type="text/css"><![CDATA[
{CSS}    ]]></style>
  </defs>
  <g class="logo-fill">{icon}</g>
</svg>
"""


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    assets = repo_root / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "logo.svg").write_text(build_logo_svg())
    (assets / "icon.svg").write_text(build_icon_svg())
    print("wrote assets/logo.svg + assets/icon.svg")


if __name__ == "__main__":
    main()