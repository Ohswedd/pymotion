"""CairoRenderer — 2D rendering backend using pycairo.

Renders ShapeClip, ColorClip, GradientClip, and ImageClip types
using Cairo surfaces. One surface per frame per clip, stateless.
"""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.image import ImageClip
from pymotion.clip.shape import ShapeClip
from pymotion.render.interface import RendererInterface
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

_SUPPORTED_TYPES = (ColorClip, GradientClip, ShapeClip, ImageClip)


class CairoRenderer(RendererInterface):
    """2D rendering backend using pycairo.

    Handles rendering of 2D clip types (shapes, colors, images).
    Each render call creates a fresh Cairo surface.
    """

    def can_render(self, clip: Clip) -> bool:
        """Check whether this backend can render the given clip.

        Args:
            clip: The clip to check.

        Returns:
            True if the clip is a 2D type handled by Cairo.
        """
        return isinstance(clip, _SUPPORTED_TYPES)

    def render_frame(self, clip: Clip, ctx: RenderContext) -> np.ndarray:
        """Render a frame using the clip's own render_frame method.

        Args:
            clip: The clip to render.
            ctx: Render context.

        Returns:
            BGRA numpy array.
        """
        return clip.render_frame(ctx)
