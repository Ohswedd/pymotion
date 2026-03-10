"""ColorClip and GradientClip — solid color and gradient backgrounds.

Used as background layers or mask sources within compositions.
Supports linear, radial, and conic gradient types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Self

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
    _cached_frame: np.ndarray | None = None

    def __init__(self, color: ColorInput = "#000000", **kwargs: object) -> None:
        """Initialize a ColorClip with the given color.

        Args:
            color: Color in any supported format.
            **kwargs: Additional Clip parameters.
        """
        super().__init__()
        self.color = Color.parse(color)
        self._cached_frame = None

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a solid color frame (cached after first render).

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array filled with the clip's color.
        """
        h = ctx.resolution.height
        w = ctx.resolution.width

        if self._cached_frame is not None and self._cached_frame.shape[:2] == (h, w):
            return self._cached_frame

        frame = np.zeros((h, w, 4), dtype=np.uint8)
        b, g, r, a = self.color.to_bgra_uint8()
        frame[:, :, 0] = b
        frame[:, :, 1] = g
        frame[:, :, 2] = r
        frame[:, :, 3] = a
        self._cached_frame = frame
        return frame


@dataclass
class GradientClip(Clip):
    """A clip that fills its frame with a gradient.

    Supports linear, radial, and conic gradient types.

    Args:
        color_start: Starting color of the gradient.
        color_end: Ending color of the gradient.
        direction: Gradient direction angle in degrees (linear only, 0=top-to-bottom).
        gradient_type: Type of gradient ("linear", "radial", "conic").
        center_x: Center X for radial/conic (0.0-1.0, default 0.5).
        center_y: Center Y for radial/conic (0.0-1.0, default 0.5).
        radius: Radius for radial gradient (0.0-1.0 of max dimension).
    """

    color_start: Color = Color(0.0, 0.0, 0.0, 1.0)
    color_end: Color = Color(1.0, 1.0, 1.0, 1.0)
    direction: float = 0.0
    gradient_type: Literal["linear", "radial", "conic"] = "linear"
    center_x: float = 0.5
    center_y: float = 0.5
    radius: float = 0.5

    def __init__(
        self,
        color_start: ColorInput = "#000000",
        color_end: ColorInput = "#FFFFFF",
        direction: float = 0.0,
        *,
        gradient_type: Literal["linear", "radial", "conic"] = "linear",
        center_x: float = 0.5,
        center_y: float = 0.5,
        radius: float = 0.5,
    ) -> None:
        """Initialize a GradientClip.

        Args:
            color_start: Starting color in any supported format.
            color_end: Ending color in any supported format.
            direction: Gradient angle in degrees (0 = top to bottom, linear only).
            gradient_type: Type of gradient ("linear", "radial", "conic").
            center_x: Center X for radial/conic (0.0-1.0).
            center_y: Center Y for radial/conic (0.0-1.0).
            radius: Radius for radial gradient (0.0-1.0 of max dimension).
        """
        super().__init__()
        self.color_start = Color.parse(color_start)
        self.color_end = Color.parse(color_end)
        self.direction = direction
        self.gradient_type = gradient_type
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self._cached_frame: np.ndarray | None = None

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
        """Render a gradient frame (cached after first render).

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array with gradient fill.
        """
        h = ctx.resolution.height
        w = ctx.resolution.width

        if self._cached_frame is not None and self._cached_frame.shape[:2] == (h, w):
            return self._cached_frame

        if self.gradient_type == "radial":
            t = self._radial_gradient(h, w)
        elif self.gradient_type == "conic":
            t = self._conic_gradient(h, w)
        else:
            t = self._linear_gradient(h, w)

        frame = self._apply_gradient(t, h, w)
        self._cached_frame = frame
        return frame

    def _linear_gradient(self, h: int, w: int) -> np.ndarray:
        """Generate linear gradient parameter field.

        Args:
            h: Image height.
            w: Image width.

        Returns:
            Float32 array of shape (h, w) with values in [0, 1].
        """
        angle_rad = np.radians(self.direction)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        # Create coordinate grids normalized to [0, 1]
        y = np.linspace(0.0, 1.0, h, dtype=np.float32)
        x = np.linspace(0.0, 1.0, w, dtype=np.float32)
        yy, xx = np.meshgrid(y, x, indexing="ij")

        # Project onto gradient direction
        t = (xx - 0.5) * sin_a + (yy - 0.5) * cos_a + 0.5
        result: np.ndarray = np.clip(t, 0.0, 1.0)
        return result

    def _radial_gradient(self, h: int, w: int) -> np.ndarray:
        """Generate radial gradient parameter field.

        Args:
            h: Image height.
            w: Image width.

        Returns:
            Float32 array of shape (h, w) with values in [0, 1].
        """
        y = np.linspace(0.0, 1.0, h, dtype=np.float32)
        x = np.linspace(0.0, 1.0, w, dtype=np.float32)
        yy, xx = np.meshgrid(y, x, indexing="ij")

        dist = np.sqrt((xx - self.center_x) ** 2 + (yy - self.center_y) ** 2)
        r = max(self.radius, 1e-6)
        t = dist / r
        return np.clip(t, 0.0, 1.0)

    def _conic_gradient(self, h: int, w: int) -> np.ndarray:
        """Generate conic (angular) gradient parameter field.

        Args:
            h: Image height.
            w: Image width.

        Returns:
            Float32 array of shape (h, w) with values in [0, 1].
        """
        y = np.linspace(0.0, 1.0, h, dtype=np.float32)
        x = np.linspace(0.0, 1.0, w, dtype=np.float32)
        yy, xx = np.meshgrid(y, x, indexing="ij")

        angle = np.arctan2(yy - self.center_y, xx - self.center_x)
        # Normalize from [-pi, pi] to [0, 1]
        t = (angle + np.pi) / (2 * np.pi)
        # Rotate by direction
        t = (t + self.direction / 360.0) % 1.0
        result: np.ndarray = t.astype(np.float32)
        return result

    def _apply_gradient(self, t: np.ndarray, h: int, w: int) -> np.ndarray:
        """Apply gradient colors using the parameter field.

        Args:
            t: Gradient parameter field (h, w) in [0, 1].
            h: Image height.
            w: Image width.

        Returns:
            BGRA numpy array.
        """
        frame = np.zeros((h, w, 4), dtype=np.uint8)

        bs, gs, rs, a_s = self.color_start.to_bgra_uint8()
        be, ge, re, ae = self.color_end.to_bgra_uint8()

        t_exp = t[:, :, np.newaxis] if t.ndim == 2 else t

        for c, (sv, ev) in enumerate([(bs, be), (gs, ge), (rs, re), (a_s, ae)]):
            frame[:, :, c] = np.clip(
                sv + (ev - sv) * t_exp[:, :, 0] if t_exp.ndim == 3 else sv + (ev - sv) * t,
                0,
                255,
            ).astype(np.uint8)

        return frame
