"""ColorClip and GradientClip — solid color and gradient backgrounds.

Used as background layers or mask sources within compositions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.utils.color import Color, ColorInput


@dataclass
class ColorClip(Clip):
    """A clip that fills its frame with a solid color.

    Args:
        color: The fill color (hex string, CSS name, tuple, or Color).
    """

    color: Color = Color(0.0, 0.0, 0.0, 1.0)

    def __init__(self, color: ColorInput = "#000000", **kwargs: object) -> None:
        """Initialize a ColorClip with the given color.

        Args:
            color: Color in any supported format.
            **kwargs: Additional Clip parameters.
        """
        super().__init__()
        self.color = Color.parse(color)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a solid color frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array filled with the clip's color.
        """
        h = ctx.resolution.height
        w = ctx.resolution.width
        frame = np.zeros((h, w, 4), dtype=np.uint8)
        b, g, r, a = self.color.to_bgra_uint8()
        frame[:, :, 0] = b
        frame[:, :, 1] = g
        frame[:, :, 2] = r
        frame[:, :, 3] = a
        return frame


@dataclass
class GradientClip(Clip):
    """A clip that fills its frame with a linear gradient.

    Args:
        color_start: Starting color of the gradient.
        color_end: Ending color of the gradient.
        direction: Gradient direction in degrees (0=top-to-bottom).
    """

    color_start: Color = Color(0.0, 0.0, 0.0, 1.0)
    color_end: Color = Color(1.0, 1.0, 1.0, 1.0)
    direction: float = 0.0

    def __init__(
        self,
        color_start: ColorInput = "#000000",
        color_end: ColorInput = "#FFFFFF",
        direction: float = 0.0,
    ) -> None:
        """Initialize a GradientClip.

        Args:
            color_start: Starting color in any supported format.
            color_end: Ending color in any supported format.
            direction: Gradient angle in degrees (0 = top to bottom).
        """
        super().__init__()
        self.color_start = Color.parse(color_start)
        self.color_end = Color.parse(color_end)
        self.direction = direction

    def set_colors(self, start: ColorInput, end: ColorInput) -> Self:
        """Set the gradient colors.

        Args:
            start: Starting color.
            end: Ending color.

        Returns:
            Self for method chaining.
        """
        self.color_start = Color.parse(start)
        self.color_end = Color.parse(end)
        return self

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a gradient frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array with gradient fill.
        """
        h = ctx.resolution.height
        w = ctx.resolution.width
        frame = np.zeros((h, w, 4), dtype=np.uint8)

        # Create vertical gradient (direction=0 means top-to-bottom)
        t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, np.newaxis]

        bs, gs, rs, a_s = self.color_start.to_bgra_uint8()
        be, ge, re, ae = self.color_end.to_bgra_uint8()

        frame[:, :, 0] = (bs + (be - bs) * t).astype(np.uint8)
        frame[:, :, 1] = (gs + (ge - gs) * t).astype(np.uint8)
        frame[:, :, 2] = (rs + (re - rs) * t).astype(np.uint8)
        frame[:, :, 3] = (a_s + (ae - a_s) * t).astype(np.uint8)

        return frame
