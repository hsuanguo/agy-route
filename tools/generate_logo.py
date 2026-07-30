#!/usr/bin/env python3
"""Generate the agy-route logo (assets/logo.svg + assets/icon.svg).

Style:
- Icon: clean routing diagram — input source node, junction node,
  two output branches.
- Wordmark: pixelized block letterforms ("agy-route"), matching the act-cli
  pixel art aesthetic. Each character is defined on a pixel grid and rendered
  with rounded pixel blocks.

Run from the repo root:

    python3 tools/generate_logo.py

Writes:
    assets/logo.svg   # horizontal lockup, 640×128
    assets/icon.svg   # icon only, 512×512
"""
from __future__ import annotations

from pathlib import Path

# Wordmark positioning inside 640x128 viewBox
WORDMARK_BOX_W = 460
WORDMARK_BOX_H = 100
WORDMARK_BOX_X = 152
WORDMARK_BOX_Y = 14

# Icon placement matches act-cli layout geometry
ICON_X, ICON_Y, ICON_W, ICON_H = 24, 8, 112, 112
ICON_STROKE = 14

# Pixelized letterforms defined on an 8-row grid (0 to 7)
# 1 = filled pixel block, 0 = empty
PIXEL_MAP: dict[str, list[list[int]]] = {
    "a": [
        [0, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
    ],  # rows 2..6
    "g": [
        [0, 1, 1, 1],
        [1, 0, 0, 1],
        [0, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 0],
    ],  # rows 2..7 (descender)
    "y": [
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [0, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 0],
    ],  # rows 2..7 (descender)
    "-": [
        [1, 1, 1],
    ],  # row 4
    "r": [
        [1, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 1, 1, 0],
        [1, 0, 1, 0],
        [1, 0, 0, 1],
    ],  # rows 2..6
    "o": [
        [0, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [0, 1, 1, 0],
    ],  # rows 2..6
    "u": [
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [0, 1, 1, 1],
    ],  # rows 2..6
    "t": [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 1],
    ],  # rows 1..6 (ascender)
    "e": [
        [0, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
        [1, 0, 0, 0],
        [0, 1, 1, 1],
    ],  # rows 2..6
}

# Row offset mapping per character
ROW_OFFSETS: dict[str, int] = {
    "a": 2,
    "g": 2,
    "y": 2,
    "-": 4,
    "r": 2,
    "o": 2,
    "u": 2,
    "t": 1,
    "e": 2,
}


def render_icon() -> str:
    """512x512 routing diagram: input source, junction, two branches."""
    cx, cy = 256, 256
    left_x_end = 96
    right_x_end = 432
    j_w, j_h = 88, 88
    top_y = 152
    bot_y = 360
    return (
        # input source circle
        f'<circle cx="{left_x_end - 16}" cy="{cy}" r="18" fill="currentColor"/>'
        # input stem
        f'<line x1="{left_x_end + 4}" y1="{cy}" x2="{cx - j_w // 2}" y2="{cy}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        # junction node (rounded square outline)
        f'<rect x="{cx - j_w // 2}" y="{cy - j_h // 2}" width="{j_w}" height="{j_h}" '
        f'rx="14" fill="none" stroke="currentColor" stroke-width="{ICON_STROKE}"/>'
        # top branch
        f'<line x1="{cx + j_w // 2}" y1="{cy - j_h // 2}" x2="{cx + j_w // 2}" y2="{top_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        f'<line x1="{cx + j_w // 2}" y1="{top_y}" x2="{right_x_end}" y2="{top_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        f'<circle cx="{right_x_end + 16}" cy="{top_y}" r="18" fill="currentColor"/>'
        # bottom branch
        f'<line x1="{cx + j_w // 2}" y1="{cy + j_h // 2}" x2="{cx + j_w // 2}" y2="{bot_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        f'<line x1="{cx + j_w // 2}" y1="{bot_y}" x2="{right_x_end}" y2="{bot_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        f'<circle cx="{right_x_end + 16}" cy="{bot_y}" r="18" fill="currentColor"/>'
    )


def render_pixelized_wordmark(
    text: str,
    pixel_size: float = 10.0,
    gap: float = 2.0,
    corner_radius: float = 2.0,
) -> tuple[str, float, float]:
    """Render pixelized text as SVG rect elements.

    Returns (svg_elements, total_width, total_height).
    """
    col_step = pixel_size + gap
    row_step = pixel_size + gap
    char_gap_cols = 1  # 1 empty pixel column between characters

    rect_elements: list[str] = []
    current_col = 0

    for ch in text:
        if ch not in PIXEL_MAP:
            raise KeyError(f"unsupported character {ch!r} in pixel wordmark")
        grid = PIXEL_MAP[ch]
        start_row = ROW_OFFSETS[ch]
        ch_width_cols = len(grid[0])

        for r_idx, row in enumerate(grid):
            r = start_row + r_idx
            for c, val in enumerate(row):
                if val:
                    x = (current_col + c) * col_step
                    y = r * row_step
                    rect_elements.append(
                        f'<rect x="{x:.1f}" y="{y:.1f}" width="{pixel_size:.1f}" height="{pixel_size:.1f}" '
                        f'rx="{corner_radius:.1f}"/>'
                    )

        current_col += ch_width_cols + char_gap_cols

    total_cols = max(current_col - char_gap_cols, 0)
    total_width = total_cols * col_step - gap
    total_height = 8 * row_step - gap
    return "\n      ".join(rect_elements), total_width, total_height


CSS = """
    .logo-fill { fill: #000000; color: #000000; }
    @media (prefers-color-scheme: dark) {
      .logo-fill { fill: #e6edf3; color: #e6edf3; }
    }
"""


def build_logo_svg() -> str:
    icon = render_icon()
    pixel_rects, total_w, total_h = render_pixelized_wordmark(
        "agy-route", pixel_size=10.0, gap=2.0, corner_radius=2.0
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 128" role="img" aria-labelledby="title desc">
  <title id="title">agy-route horizontal lockup</title>
  <desc id="desc">Icon left, pixelized wordmark right. Fill flips in dark mode via prefers-color-scheme.</desc>
  <defs>
    <style type="text/css"><![CDATA[
{CSS}    ]]></style>
  </defs>
  <rect width="640" height="128" fill="none"/>
  <svg x="{ICON_X}" y="{ICON_Y}" width="{ICON_W}" height="{ICON_H}" viewBox="0 0 512 512" aria-hidden="true">
    <g class="logo-fill">
      {icon}
    </g>
  </svg>
  <svg x="{WORDMARK_BOX_X}" y="{WORDMARK_BOX_Y}" width="{WORDMARK_BOX_W}" height="{WORDMARK_BOX_H}" viewBox="0 0 {total_w:.1f} {total_h:.1f}" preserveAspectRatio="xMinYMid meet" aria-hidden="true">
    <g class="logo-fill">
      {pixel_rects}
    </g>
  </svg>
</svg>
"""


def build_icon_svg() -> str:
    icon = render_icon()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-labelledby="title desc">
  <title id="title">agy-route icon</title>
  <desc id="desc">A routing diagram: input source → junction → two branches ending at destination nodes.</desc>
  <defs>
    <style type="text/css"><![CDATA[
{CSS}    ]]></style>
  </defs>
  <g class="logo-fill">
    {icon}
  </g>
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