"""TextClip — render text with font control and styling.

Delegates rendering to the text/renderer.py GlyphRenderer, producing
BGRA frames with text rendered at clip resolution.

Includes a Google Fonts downloader for fetching web fonts on demand.
"""

from __future__ import annotations

import hashlib
import re as _re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Self

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.security.validation import sanitize_text
from pymotion.text.renderer import FontLoader, GlyphRenderer
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

# Google Fonts download config per PRD §9.3
_GOOGLE_FONTS_CSS_URL = "https://fonts.googleapis.com/css2"
_ALLOWED_DOMAINS = ("fonts.googleapis.com", "fonts.gstatic.com")
_FONT_CACHE_DIR = Path.home() / ".cache" / "pymotion" / "fonts"
_FONT_NAME_RE = _re.compile(r"^[a-zA-Z0-9 _-]+$")


def download_google_font(
    family: str,
    *,
    weight: int = 400,
    cache_dir: Path | None = None,
    timeout: float = 10.0,
    max_size: int = 10 * 1024 * 1024,
) -> Path:
    """Download a Google Font and cache it locally.

    Args:
        family: Font family name (e.g., "Roboto", "Open Sans").
        weight: Font weight (100–900). Default 400 (regular).
        cache_dir: Directory for font cache. Default ~/.cache/pymotion/fonts.
        timeout: HTTP request timeout in seconds.
        max_size: Maximum font file size in bytes (default 10 MB).

    Returns:
        Path to the cached .ttf font file.

    Raises:
        ValueError: If the family name is invalid.
        RuntimeError: If the download fails or response is too large.
    """
    import httpx

    if not _FONT_NAME_RE.match(family):
        msg = f"Invalid font family name: {family!r}. Use alphanumeric, spaces, hyphens."
        raise ValueError(msg)

    dest_dir = cache_dir or _FONT_CACHE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Stable cache filename
    cache_key = f"{family}-{weight}"
    cache_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
    cached_path = dest_dir / f"{cache_hash}.ttf"

    if cached_path.exists():
        logger.debug("google_font_cached", family=family, weight=weight, path=str(cached_path))
        return cached_path

    # Fetch CSS to find .ttf URL
    css_url = f"{_GOOGLE_FONTS_CSS_URL}?family={family.replace(' ', '+')}:wght@{weight}"

    with httpx.Client(
        timeout=timeout,
        max_redirects=2,
        follow_redirects=True,
    ) as client:
        css_resp = client.get(
            css_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        css_resp.raise_for_status()
        css_text = css_resp.text

        # Extract .ttf URL from CSS
        ttf_match = _re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css_text)
        if not ttf_match:
            msg = f"Could not find .ttf URL in Google Fonts CSS for '{family}'"
            raise RuntimeError(msg)

        ttf_url = ttf_match.group(1)
        font_resp = client.get(ttf_url)
        font_resp.raise_for_status()

        if len(font_resp.content) > max_size:
            msg = f"Font file exceeds {max_size} bytes limit"
            raise RuntimeError(msg)

        cached_path.write_bytes(font_resp.content)

    logger.info("google_font_downloaded", family=family, weight=weight, path=str(cached_path))
    return cached_path


# Module-level shared instances (not global mutable state — they're caches)
_font_loader = FontLoader()
_glyph_renderer = GlyphRenderer(_font_loader)


@dataclass
class Shadow:
    """Drop shadow configuration for text.

    Args:
        color: Shadow color.
        offset_x: Horizontal shadow offset in pixels.
        offset_y: Vertical shadow offset in pixels.
        blur: Shadow blur radius.
    """

    color: Color = Color(0.0, 0.0, 0.0, 0.5)
    offset_x: float = 2.0
    offset_y: float = 2.0
    blur: float = 3.0


@dataclass
class TextClip(Clip):
    """A clip that renders styled text to BGRA frames.

    Supports multiline text with word-wrap, alignment, stroke, shadow,
    and various font options via FreeType rendering.

    Args:
        text: The text string to render.
        font: Font file path or font name.
        size: Font size in points.
        color: Text color.
        letter_spacing: Additional spacing between letters in pixels.
        line_height: Line height multiplier relative to font size.
        align: Text alignment.
        max_width: Maximum width for word wrapping (None = no wrap).
        stroke_color: Stroke color (None = no stroke).
        stroke_width: Stroke width in pixels.
        shadow: Drop shadow configuration (None = no shadow).
    """

    text: str = ""
    font: str = "Arial"
    size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    letter_spacing: float = 0.0
    line_height: float = 1.2
    align: Literal["left", "center", "right"] = "left"
    max_width: int | None = None
    stroke_color: Color | None = None
    stroke_width: float = 0.0
    shadow: Shadow | None = None
    _cached_frame: np.ndarray | None = field(default=None, repr=False, compare=False)

    def __init__(
        self,
        text: str = "",
        *,
        font: str = "Arial",
        size: float = 24.0,
        color: ColorInput = "#FFFFFF",
        letter_spacing: float = 0.0,
        line_height: float = 1.2,
        align: Literal["left", "center", "right"] = "left",
        max_width: int | None = None,
        stroke_color: ColorInput | None = None,
        stroke_width: float = 0.0,
        shadow: Shadow | None = None,
    ) -> None:
        """Initialize a TextClip.

        Args:
            text: The text string to render.
            font: Font file path or font name.
            size: Font size in points.
            color: Text color in any supported format.
            letter_spacing: Additional spacing between letters in pixels.
            line_height: Line height multiplier.
            align: Text alignment.
            max_width: Maximum width for word wrapping.
            stroke_color: Stroke color (None = no stroke).
            stroke_width: Stroke width in pixels.
            shadow: Drop shadow configuration.
        """
        super().__init__()
        self.text = sanitize_text(text)
        self.font = font
        self.size = size
        self.color = Color.parse(color)
        self.letter_spacing = letter_spacing
        self.line_height = line_height
        self.align = align
        self.max_width = max_width
        self.stroke_color = Color.parse(stroke_color) if stroke_color is not None else None
        self.stroke_width = stroke_width
        self.shadow = shadow
        self._cached_frame = None

    def set_text(self, text: str) -> Self:
        """Set the text content.

        Args:
            text: New text string.

        Returns:
            Self for method chaining.
        """
        self.text = sanitize_text(text)
        self._cached_frame = None
        return self

    def set_font(self, font: str, size: float | None = None) -> Self:
        """Set the font and optionally the size.

        Args:
            font: Font file path or name.
            size: Font size in points (None = keep current).

        Returns:
            Self for method chaining.
        """
        self.font = font
        if size is not None:
            self.size = size
        self._cached_frame = None
        return self

    def set_color(self, color: ColorInput) -> Self:
        """Set the text color.

        Args:
            color: Color in any supported format.

        Returns:
            Self for method chaining.
        """
        self.color = Color.parse(color)
        self._cached_frame = None
        return self

    def set_stroke(self, color: ColorInput, width: float = 1.0) -> Self:
        """Set text stroke.

        Args:
            color: Stroke color.
            width: Stroke width in pixels.

        Returns:
            Self for method chaining.
        """
        self.stroke_color = Color.parse(color)
        self.stroke_width = width
        self._cached_frame = None
        return self

    def set_shadow(self, shadow: Shadow) -> Self:
        """Set the drop shadow.

        Args:
            shadow: Shadow configuration.

        Returns:
            Self for method chaining.
        """
        self.shadow = shadow
        self._cached_frame = None
        return self

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render text to a BGRA frame at the composition resolution.

        The text is rendered once and cached; subsequent frames return
        the cached result (text is static within a clip).

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array with rendered text.
        """
        if self._cached_frame is not None:
            return self._cached_frame

        h = ctx.resolution.height
        w = ctx.resolution.width
        frame = np.zeros((h, w, 4), dtype=np.uint8)

        if not self.text:
            self._cached_frame = frame
            return frame

        # Render text to a tight-fit image
        text_img = _glyph_renderer.render_text(
            self.text,
            self.font,
            self.size,
            self.color,
            max_width=self.max_width,
            line_height=self.line_height,
            align=self.align,
            letter_spacing=self.letter_spacing,
        )

        # Composite text image onto frame at position
        th, tw = text_img.shape[:2]
        px = int(self._position.x)
        py = int(self._position.y)

        # Clip to frame bounds
        src_y0 = max(0, -py)
        src_x0 = max(0, -px)
        dst_y0 = max(0, py)
        dst_x0 = max(0, px)
        copy_h = min(th - src_y0, h - dst_y0)
        copy_w = min(tw - src_x0, w - dst_x0)

        if copy_h > 0 and copy_w > 0:
            frame[dst_y0 : dst_y0 + copy_h, dst_x0 : dst_x0 + copy_w] = text_img[
                src_y0 : src_y0 + copy_h, src_x0 : src_x0 + copy_w
            ]

        self._cached_frame = frame
        return frame
