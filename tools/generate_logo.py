#!/usr/bin/env python3
"""Generate the AGY-ROUTE logo (assets/logo.svg + assets/icon.svg).

Style:
- Icon: clean routing diagram — input source node, junction node,
  two output branches.
- Wordmark: uppercase pixelized block letterforms ("AGY-ROUTE"), matching the
  act-cli pixel art aesthetic. Centered lockup within 640x128 canvas.

Run from the repo root:

    python3 tools/generate_logo.py

Writes:
    assets/logo.svg   # horizontal lockup, 640×128 (centered)
    assets/icon.svg   # icon only, 512×512
"""
from __future__ import annotations

from pathlib import Path

# Icon canvas geometry
ICON_W, ICON_H = 112, 112
ICON_STROKE = 14

# Pixelized UPPERCASE letterforms defined on a 7-row grid (0 to 6)
# 1 = filled pixel block, 0 = empty
PIXEL_MAP: dict[str, list[list[int]]] = {
    "A": [
        [0, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
    ],
    "G": [
        [0, 1, 1, 1, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    "Y": [
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 0, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
    ],
    "-": [
        [0, 0, 0],
        [0, 0, 0],
        [1, 1, 1],
        [1, 1, 1],
        [0, 0, 0],
        [0, 0, 0],
    ],
    "R": [
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 0],
        [1, 0, 1, 0, 0],
        [1, 0, 0, 1, 0],
        [1, 0, 0, 0, 1],
    ],
    "O": [
        [0, 1, 1, 1, 0],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    "U": [
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 1, 1, 1, 0],
    ],
    "T": [
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
    ],
    "E": [
        [1, 1, 1, 1],
        [1, 0, 0, 0],
        [1, 1, 1, 0],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 1, 1, 1],
    ],
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
    pixel_size: float = 7.5,
    gap: float = 1.5,
    corner_radius: float = 1.5,
) -> tuple[str, float, float]:
    """Render pixelized text as SVG rect elements.

    Returns (svg_elements, total_width, total_height).
    """
    col_step = pixel_size + gap
    row_step = pixel_size + gap
    char_gap_cols = 1

    rect_elements: list[str] = []
    current_col = 0

    for ch in text:
        if ch not in PIXEL_MAP:
            raise KeyError(f"unsupported character {ch!r} in pixel wordmark")
        grid = PIXEL_MAP[ch]
        ch_width_cols = len(grid[0])

        for r, row in enumerate(grid):
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
    total_height = 6 * row_step - gap
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
        "AGY-ROUTE", pixel_size=7.5, gap=1.5, corner_radius=1.5
    )

    # Canvas dimensions & centering calculations
    canvas_w, canvas_h = 640, 128
    gap_between_icon_and_wordmark = 24.0
    total_lockup_w = ICON_W + gap_between_icon_and_wordmark + total_w

    # Horizontal & vertical centering offsets
    start_x = (canvas_w - total_lockup_w) / 2.0
    icon_x = start_x
    icon_y = (canvas_h - ICON_H) / 2.0

    wordmark_x = icon_x + ICON_W + gap_between_icon_and_wordmark
    wordmark_y = (canvas_h - total_h) / 2.0

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" role="img" aria-labelledby="title desc">
  <title id="title">AGY-ROUTE horizontal lockup</title>
  <desc id="desc">Icon left, uppercase pixelized wordmark right, centered horizontally and vertically.</desc>
  <defs>
    <style type="text/css"><![CDATA[
{CSS}    ]]></style>
  </defs>
  <rect width="{canvas_w}" height="{canvas_h}" fill="none"/>
  <svg x="{icon_x:.1f}" y="{icon_y:.1f}" width="{ICON_W}" height="{ICON_H}" viewBox="0 0 512 512" aria-hidden="true">
    <g class="logo-fill">
      {icon}
    </g>
  </svg>
  <svg x="{wordmark_x:.1f}" y="{wordmark_y:.1f}" width="{total_w:.1f}" height="{total_h:.1f}" viewBox="0 0 {total_w:.1f} {total_h:.1f}" preserveAspectRatio="xMinYMid meet" aria-hidden="true">
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
  <title id="title">AGY-ROUTE icon</title>
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