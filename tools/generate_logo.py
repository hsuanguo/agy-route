#!/usr/bin/env python3
"""Generate the agy-route logo (assets/logo.svg + assets/icon.svg).

Style:
- Icon: a clean, line-art "routing diagram" — input source (small
  circle), input stem, junction node (rounded square), two branches
  ending at destination nodes. All stroked; reads at any size and
  matches the project name: one CLI (agy), many routes (search today;
  review/research/etc. tomorrow).
- Wordmark: glyphs extracted from DejaVu Sans Bold via fontTools at
  generation time. Self-contained SVG path data — no font dependency
  at render time, so the SVG looks the same in browsers, GitHub
  READMEs, and local previews.

Why fontTools: act-cli's logo uses pixel-block letterforms which read
well for short angular words ("act-cli") but get cramped for longer
rounder names ("agy-route", 9 chars with several round shapes). A
proper proportional sans is always legible and looks modern.

Run from the repo root:

    python3 tools/generate_logo.py

Writes:
    assets/logo.svg   # horizontal lockup, 640×128
    assets/icon.svg   # icon only, 512×512

Re-run after any layout / icon tweak or to regenerate the wordmark.
"""
from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Wordmark vertical box: height 100, fits the font cap-height with a
# little whitespace on top.
WORDMARK_BOX_W = 460
WORDMARK_BOX_H = 100
WORDMARK_BOX_X = 152
WORDMARK_BOX_Y = 14

# Icon placement matches act-cli's geometry.
ICON_X, ICON_Y, ICON_W, ICON_H = 24, 8, 112, 112
ICON_STROKE = 14


# --- Icon -------------------------------------------------------------------


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
        # top branch — vertical out of junction up
        f'<line x1="{cx + j_w // 2}" y1="{cy - j_h // 2}" x2="{cx + j_w // 2}" y2="{top_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        # top branch — horizontal
        f'<line x1="{cx + j_w // 2}" y1="{top_y}" x2="{right_x_end}" y2="{top_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        # top destination
        f'<circle cx="{right_x_end + 16}" cy="{top_y}" r="18" fill="currentColor"/>'
        # bottom branch — vertical out of junction down
        f'<line x1="{cx + j_w // 2}" y1="{cy + j_h // 2}" x2="{cx + j_w // 2}" y2="{bot_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        # bottom branch — horizontal
        f'<line x1="{cx + j_w // 2}" y1="{bot_y}" x2="{right_x_end}" y2="{bot_y}" '
        f'stroke="currentColor" stroke-width="{ICON_STROKE}" stroke-linecap="round"/>'
        # bottom destination
        f'<circle cx="{right_x_end + 16}" cy="{bot_y}" r="18" fill="currentColor"/>'
    )


# --- Wordmark ---------------------------------------------------------------

# We pull glyph paths from a real font so the wordmark is always readable,
# no matter the rendering context.

_FONT: TTFont | None = None
_GLYPH_SET = None
_CMAP = None
_HMTX = None
_UPEM = 0


def _font() -> tuple[TTFont, object, dict[int, str], dict[str, tuple[int, int]], int]:
    global _FONT, _GLYPH_SET, _CMAP, _HMTX, _UPEM
    if _FONT is None:
        _FONT = TTFont(FONT_PATH)
        _GLYPH_SET = _FONT.getGlyphSet()
        _CMAP = _FONT.getBestCmap()
        _HMTX = _FONT["hmtx"]
        _UPEM = _FONT["head"].unitsPerEm
    return _FONT, _GLYPH_SET, _CMAP, _HMTX, _UPEM


def render_wordmark(
    text: str,
    font_size_units: int = 100,
    x_offset_units: int = 0,
) -> tuple[str, float, float]:
    """Render `text` as a single SVG path d-string.

    Args:
      text: characters to render.
      font_size_units: target cap-height in user-units. Each glyph is
        scaled so its cap-height == this value.
      x_offset_units: starting x position.

    Returns (path_d, width_units, ascent_units).
    """
    font, glyph_set, cmap, hmtx, upem = _font()
    # Cap-height heuristic: use font's OS/2 sCapHeight if available, else 70% of upem.
    cap_height = getattr(font.get("OS/2"), "sCapHeight", None) or int(upem * 0.7)
    scale = font_size_units / cap_height

    pieces: list[str] = []
    x_cursor_units = x_offset_units
    for ch in text:
        if ord(ch) not in cmap:
            raise KeyError(f"no glyph for {ch!r} in {FONT_PATH}")
        gname = cmap[ord(ch)]
        glyph = glyph_set[gname]
        pen = SVGPathPen(glyph_set)
        glyph.draw(pen)
        raw_d = pen.getCommands()
        # SVG y is down; font is y-up. Wrap with a transform that flips + scales.
        # Transform: x' = scale*x + x_cursor; y' = scale*y - cap_height*scale  + ... = ...
        # Easier: emit each subcommand with a transform wrapper using a <g>
        # transform="translate(...) scale(...)" — but we want a single path.
        # Apply the transform numerically to the raw path d by re-emitting it
        # with a leading matrix().
        # Cap-height in font units:
        cap_h_units = cap_height
        # We translate by x_cursor, scale by `scale`, then translate by (0, +cap_h) so
        # the glyph's baseline sits at y=0 and y increases downward.
        transform = (
            f"matrix({scale} 0 0 {-scale} {x_cursor_units:.2f} {cap_h_units * scale:.2f})"
        )
        pieces.append(f'<path d="{raw_d}" transform="{transform}"/>')
        adv_width, _lsb = hmtx[gname]
        x_cursor_units += adv_width * scale

    # Width is the advance sum (font units * scale).
    width_units = x_cursor_units - x_offset_units
    return "".join(pieces), width_units, font_size_units  # height = cap-height target


# --- CSS + SVG composition ---------------------------------------------------

CSS = """
    .logo-fill { color: #000000; }
    @media (prefers-color-scheme: dark) {
      .logo-fill { color: #e6edf3; }
    }
"""


def build_logo_svg() -> str:
    icon = render_icon()
    wordmark_paths, wordmark_w, wordmark_h = render_wordmark("agy-route", font_size_units=80)
    # 80-unit cap-height ⇒ visually about the right size in our 100-tall box
    # (descenders extend below baseline; we trim the top via the box viewBox).
    # Center vertically in the 100-tall wordmark box: shift the baseline path
    # so glyph baselines sit roughly at y = 76 of 100 (matches cap-height 80
    # with small top margin).
    # We re-render with an explicit y shift baked into the per-glyph matrix so
    # glyphs align within the box.
    wordmark_paths_offset, _, _ = render_wordmark(
        "agy-route", font_size_units=80, x_offset_units=0
    )
    # The glyph paths are emitted with translate/scale per glyph already; we
    # wrap the entire group with another translate to position within the box.
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 128" role="img" aria-labelledby="title desc">
  <title id="title">agy-route horizontal lockup</title>
  <desc id="desc">Icon left, wordmark right. Fill flips in dark mode via prefers-color-scheme.</desc>
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
  <svg x="{WORDMARK_BOX_X}" y="{WORDMARK_BOX_Y}" width="{WORDMARK_BOX_W}" height="{WORDMARK_BOX_H}" viewBox="0 0 {wordmark_w:.2f} {wordmark_h}" preserveAspectRatio="xMinYMid meet" aria-hidden="true">
    <g class="logo-fill" fill="currentColor">
      {wordmark_paths}
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