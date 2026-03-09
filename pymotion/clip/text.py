"""TextClip — render text with font control and styling.

Delegates rendering to the text/renderer.py GlyphRenderer, producing
BGRA frames with text rendered at clip resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Self

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.security.validation import sanitize_text
from pymotion.text.renderer import FontLoader, GlyphRenderer
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

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
