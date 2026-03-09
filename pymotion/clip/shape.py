"""ShapeClip — render geometric shapes via Cairo.

Provides factory methods for common shapes: rect, circle, ellipse, polygon, line.
All rendering is done through pycairo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Self

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.utils.color import Color, ColorInput


@dataclass
class ShapeClip(Clip):
    """A clip that renders a geometric shape.

    Use the factory methods (rect, circle, ellipse, polygon, line)
    to create ShapeClip instances with the right parameters.

    Args:
        shape_type: Type of shape to render.
        fill_color: Fill color for the shape.
        stroke_color: Stroke color (None for no stroke).
        stroke_width: Stroke width in pixels.
        params: Shape-specific parameters.
    """

    shape_type: str = "rect"
    fill_color: Color = Color(1.0, 1.0, 1.0, 1.0)
    stroke_color: Color | None = None
    stroke_width: float = 0.0
    params: dict[str, float] = field(default_factory=dict)

    @classmethod
    def rect(
        cls,
        x: float = 0,
        y: float = 0,
        w: float = 100,
        h: float = 100,
        fill: ColorInput = "#FFFFFF",
        stroke: ColorInput | None = None,
        stroke_width: float = 0.0,
    ) -> ShapeClip:
        """Create a rectangle shape clip.

        Args:
            x: X position of top-left corner.
            y: Y position of top-left corner.
            w: Width of the rectangle.
            h: Height of the rectangle.
            fill: Fill color.
            stroke: Stroke color (None for no stroke).
            stroke_width: Stroke width in pixels.

        Returns:
            Configured ShapeClip.
        """
        clip = cls()
        clip.shape_type = "rect"
        clip.fill_color = Color.parse(fill)
        clip.stroke_color = Color.parse(stroke) if stroke is not None else None
        clip.stroke_width = stroke_width
        clip.params = {"x": x, "y": y, "w": w, "h": h}
        return clip

    @classmethod
    def circle(
        cls,
        cx: float = 0,
        cy: float = 0,
        r: float = 50,
        fill: ColorInput = "#FFFFFF",
        stroke: ColorInput | None = None,
        stroke_width: float = 0.0,
    ) -> ShapeClip:
        """Create a circle shape clip.

        Args:
            cx: X center of the circle.
            cy: Y center of the circle.
            r: Radius of the circle.
            fill: Fill color.
            stroke: Stroke color (None for no stroke).
            stroke_width: Stroke width in pixels.

        Returns:
            Configured ShapeClip.
        """
        clip = cls()
        clip.shape_type = "circle"
        clip.fill_color = Color.parse(fill)
        clip.stroke_color = Color.parse(stroke) if stroke is not None else None
        clip.stroke_width = stroke_width
        clip.params = {"cx": cx, "cy": cy, "r": r}
        return clip

    @classmethod
    def ellipse(
        cls,
        cx: float = 0,
        cy: float = 0,
        rx: float = 50,
        ry: float = 30,
        fill: ColorInput = "#FFFFFF",
    ) -> ShapeClip:
        """Create an ellipse shape clip.

        Args:
            cx: X center of the ellipse.
            cy: Y center of the ellipse.
            rx: X radius.
            ry: Y radius.
            fill: Fill color.

        Returns:
            Configured ShapeClip.
        """
        clip = cls()
        clip.shape_type = "ellipse"
        clip.fill_color = Color.parse(fill)
        clip.params = {"cx": cx, "cy": cy, "rx": rx, "ry": ry}
        return clip

    @classmethod
    def polygon(
        cls,
        points: list[tuple[float, float]],
        fill: ColorInput = "#FFFFFF",
    ) -> ShapeClip:
        """Create a polygon shape clip.

        Args:
            points: List of (x, y) vertex coordinates.
            fill: Fill color.

        Returns:
            Configured ShapeClip.
        """
        clip = cls()
        clip.shape_type = "polygon"
        clip.fill_color = Color.parse(fill)
        # Store points as flat params: x0, y0, x1, y1, ...
        params: dict[str, float] = {"n_points": float(len(points))}
        for i, (px, py) in enumerate(points):
            params[f"x{i}"] = px
            params[f"y{i}"] = py
        clip.params = params
        return clip

    @classmethod
    def line(
        cls,
        x1: float = 0,
        y1: float = 0,
        x2: float = 100,
        y2: float = 100,
        color: ColorInput = "#FFFFFF",
        width: float = 2.0,
    ) -> ShapeClip:
        """Create a line shape clip.

        Args:
            x1: Start X coordinate.
            y1: Start Y coordinate.
            x2: End X coordinate.
            y2: End Y coordinate.
            color: Line color.
            width: Line width in pixels.

        Returns:
            Configured ShapeClip.
        """
        clip = cls()
        clip.shape_type = "line"
        clip.stroke_color = Color.parse(color)
        clip.stroke_width = width
        clip.params = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        return clip

    def set_fill(self, color: ColorInput) -> Self:
        """Set the fill color.

        Args:
            color: New fill color.

        Returns:
            Self for method chaining.
        """
        self.fill_color = Color.parse(color)
        return self

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render the shape to a BGRA frame using Cairo.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # Draw the shape
        if self.shape_type == "rect":
            self._draw_rect(cr)
        elif self.shape_type == "circle":
            self._draw_circle(cr)
        elif self.shape_type == "ellipse":
            self._draw_ellipse(cr)
        elif self.shape_type == "polygon":
            self._draw_polygon(cr)
        elif self.shape_type == "line":
            self._draw_line(cr)

        # Fill
        if self.shape_type != "line" and self.fill_color is not None:
            cr.set_source_rgba(
                self.fill_color.r,
                self.fill_color.g,
                self.fill_color.b,
                self.fill_color.a,
            )
            if self.stroke_color is not None and self.stroke_width > 0:
                cr.fill_preserve()
            else:
                cr.fill()

        # Stroke
        if self.stroke_color is not None and self.stroke_width > 0:
            cr.set_source_rgba(
                self.stroke_color.r,
                self.stroke_color.g,
                self.stroke_color.b,
                self.stroke_color.a,
            )
            cr.set_line_width(self.stroke_width)
            cr.stroke()

        # Convert Cairo surface to numpy array
        # Cairo ARGB32 is stored as BGRA in memory on little-endian systems
        buf = surface.get_data()
        frame = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=bytes(buf))
        return frame.copy()

    def _draw_rect(self, cr: cairo.Context[cairo.ImageSurface]) -> None:
        """Draw a rectangle path."""
        x = self.params.get("x", 0)
        y = self.params.get("y", 0)
        w = self.params.get("w", 100)
        h = self.params.get("h", 100)
        cr.rectangle(x, y, w, h)

    def _draw_circle(self, cr: cairo.Context[cairo.ImageSurface]) -> None:
        """Draw a circle path."""
        cx = self.params.get("cx", 0)
        cy = self.params.get("cy", 0)
        r = self.params.get("r", 50)
        cr.arc(cx, cy, r, 0, 2 * math.pi)

    def _draw_ellipse(self, cr: cairo.Context[cairo.ImageSurface]) -> None:
        """Draw an ellipse path."""
        cx = self.params.get("cx", 0)
        cy = self.params.get("cy", 0)
        rx = self.params.get("rx", 50)
        ry = self.params.get("ry", 30)
        cr.save()
        cr.translate(cx, cy)
        cr.scale(rx, ry)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()

    def _draw_polygon(self, cr: cairo.Context[cairo.ImageSurface]) -> None:
        """Draw a polygon path."""
        n = int(self.params.get("n_points", 0))
        if n < 2:
            return
        cr.move_to(self.params["x0"], self.params["y0"])
        for i in range(1, n):
            cr.line_to(self.params[f"x{i}"], self.params[f"y{i}"])
        cr.close_path()

    def _draw_line(self, cr: cairo.Context[cairo.ImageSurface]) -> None:
        """Draw a line path."""
        x1 = self.params.get("x1", 0)
        y1 = self.params.get("y1", 0)
        x2 = self.params.get("x2", 100)
        y2 = self.params.get("y2", 100)
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        if self.stroke_color is not None:
            cr.set_source_rgba(
                self.stroke_color.r,
                self.stroke_color.g,
                self.stroke_color.b,
                self.stroke_color.a,
            )
            cr.set_line_width(self.stroke_width)
            cr.stroke()
