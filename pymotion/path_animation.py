"""Path animation — follow_path, StrokeClip, and path morphing.

Provides SVG path following, animated stroke trim, and bezier path
interpolation (morphing) for ShapeClip.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.expressions import ExpressionContext
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.logging import get_logger
from pymotion.utils.math import Vec2

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# SVG path parsing (minimal: M, L, C, Z)
# ---------------------------------------------------------------------------


@dataclass
class _PathSegment:
    """A segment of an SVG path (line or cubic bezier)."""

    start: Vec2
    end: Vec2
    # For cubic bezier: control points; None for lines
    cp1: Vec2 | None = None
    cp2: Vec2 | None = None
    length: float = 0.0


def _parse_svg_path(d: str) -> list[_PathSegment]:
    """Parse a minimal SVG path string into segments.

    Supports M (moveto), L (lineto), C (cubic bezier), Z (close).
    All coordinates are absolute.

    Args:
        d: SVG path data string.

    Returns:
        List of path segments.
    """
    segments: list[_PathSegment] = []
    tokens = re.findall(r"[MmLlCcZz]|[-+]?\d*\.?\d+", d)

    pos = Vec2(0.0, 0.0)
    start_pos = pos
    i = 0

    while i < len(tokens):
        cmd = tokens[i]
        i += 1

        if cmd in ("M", "m"):
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            if cmd == "m":
                pos = Vec2(pos.x + x, pos.y + y)
            else:
                pos = Vec2(x, y)
            start_pos = pos

        elif cmd in ("L", "l"):
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            if cmd == "l":
                end = Vec2(pos.x + x, pos.y + y)
            else:
                end = Vec2(x, y)
            seg = _PathSegment(start=pos, end=end, length=_line_length(pos, end))
            segments.append(seg)
            pos = end

        elif cmd in ("C", "c"):
            x1 = float(tokens[i])
            y1 = float(tokens[i + 1])
            x2 = float(tokens[i + 2])
            y2 = float(tokens[i + 3])
            x = float(tokens[i + 4])
            y = float(tokens[i + 5])
            i += 6
            if cmd == "c":
                cp1 = Vec2(pos.x + x1, pos.y + y1)
                cp2 = Vec2(pos.x + x2, pos.y + y2)
                end = Vec2(pos.x + x, pos.y + y)
            else:
                cp1 = Vec2(x1, y1)
                cp2 = Vec2(x2, y2)
                end = Vec2(x, y)
            seg = _PathSegment(
                start=pos,
                end=end,
                cp1=cp1,
                cp2=cp2,
                length=_bezier_length(pos, cp1, cp2, end),
            )
            segments.append(seg)
            pos = end

        elif cmd in ("Z", "z"):
            if pos.x != start_pos.x or pos.y != start_pos.y:
                seg = _PathSegment(
                    start=pos,
                    end=start_pos,
                    length=_line_length(pos, start_pos),
                )
                segments.append(seg)
            pos = start_pos

    return segments


def _line_length(a: Vec2, b: Vec2) -> float:
    return math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)


def _bezier_point(t: float, p0: Vec2, p1: Vec2, p2: Vec2, p3: Vec2) -> Vec2:
    """Evaluate cubic bezier at parameter t."""
    u = 1.0 - t
    x = u**3 * p0.x + 3 * u**2 * t * p1.x + 3 * u * t**2 * p2.x + t**3 * p3.x
    y = u**3 * p0.y + 3 * u**2 * t * p1.y + 3 * u * t**2 * p2.y + t**3 * p3.y
    return Vec2(x, y)


def _bezier_length(p0: Vec2, p1: Vec2, p2: Vec2, p3: Vec2, steps: int = 20) -> float:
    """Approximate cubic bezier length by subdivision."""
    total = 0.0
    prev = p0
    for i in range(1, steps + 1):
        t = i / steps
        pt = _bezier_point(t, p0, p1, p2, p3)
        total += _line_length(prev, pt)
        prev = pt
    return total


def _bezier_tangent(t: float, p0: Vec2, p1: Vec2, p2: Vec2, p3: Vec2) -> Vec2:
    """First derivative of cubic bezier at parameter t."""
    u = 1.0 - t
    dx = 3 * u**2 * (p1.x - p0.x) + 6 * u * t * (p2.x - p1.x) + 3 * t**2 * (p3.x - p2.x)
    dy = 3 * u**2 * (p1.y - p0.y) + 6 * u * t * (p2.y - p1.y) + 3 * t**2 * (p3.y - p2.y)
    return Vec2(dx, dy)


def _point_on_path(
    segments: list[_PathSegment],
    total_length: float,
    distance: float,
) -> tuple[Vec2, float]:
    """Find point and tangent angle at a given distance along path.

    Args:
        segments: Path segments.
        total_length: Total path length.
        distance: Distance from start.

    Returns:
        (position, angle_degrees) tuple.
    """
    distance = max(0.0, min(distance, total_length))
    accumulated = 0.0

    for seg in segments:
        if accumulated + seg.length >= distance or seg is segments[-1]:
            local_d = distance - accumulated
            t = local_d / max(seg.length, 1e-10)
            t = max(0.0, min(1.0, t))

            if seg.cp1 is not None and seg.cp2 is not None:
                pos = _bezier_point(t, seg.start, seg.cp1, seg.cp2, seg.end)
                tan = _bezier_tangent(t, seg.start, seg.cp1, seg.cp2, seg.end)
            else:
                pos = Vec2(
                    seg.start.x + (seg.end.x - seg.start.x) * t,
                    seg.start.y + (seg.end.y - seg.start.y) * t,
                )
                tan = Vec2(
                    seg.end.x - seg.start.x,
                    seg.end.y - seg.start.y,
                )

            angle = math.degrees(math.atan2(tan.y, tan.x))
            return pos, angle

        accumulated += seg.length

    # Fallback: return end of last segment
    if segments:
        last = segments[-1]
        return last.end, 0.0
    return Vec2(0.0, 0.0), 0.0


def follow_path(
    clip: Clip,
    svg_path_str: str,
    duration: int,
    align: bool = True,
) -> Clip:
    """Animate a clip's center along an SVG path.

    Sets expressions on the clip's ``position.x``, ``position.y``,
    and optionally ``rotation`` to follow the path over the given
    duration in frames.

    Args:
        clip: The clip to animate.
        svg_path_str: SVG path data string (M, L, C, Z commands).
        duration: Number of frames for the animation.
        align: If True, rotate the clip to follow the path tangent.

    Returns:
        The clip (for method chaining).

    Raises:
        ValueError: If the path is empty or duration is not positive.
    """
    if duration <= 0:
        msg = f"Duration must be positive, got {duration}"
        raise ValueError(msg)

    segments = _parse_svg_path(svg_path_str)
    if not segments:
        msg = "SVG path is empty or invalid"
        raise ValueError(msg)

    total_length = sum(s.length for s in segments)

    def _pos_x(ctx: ExpressionContext) -> float:
        progress = ctx.local_frame / max(duration - 1, 1)
        distance = progress * total_length
        pos, _ = _point_on_path(segments, total_length, distance)
        return pos.x

    def _pos_y(ctx: ExpressionContext) -> float:
        progress = ctx.local_frame / max(duration - 1, 1)
        distance = progress * total_length
        pos, _ = _point_on_path(segments, total_length, distance)
        return pos.y

    clip.set_expression("position.x", _pos_x)
    clip.set_expression("position.y", _pos_y)

    if align:

        def _rotation(ctx: ExpressionContext) -> float:
            progress = ctx.local_frame / max(duration - 1, 1)
            distance = progress * total_length
            _, angle = _point_on_path(segments, total_length, distance)
            return angle

        clip.set_expression("rotation", _rotation)

    return clip


# ---------------------------------------------------------------------------
# StrokeClip
# ---------------------------------------------------------------------------


@dataclass
class StrokeClip(Clip):
    """An animated stroke along an SVG path — draw-on / draw-off effect.

    Renders a stroked path with animatable ``trim_start`` and ``trim_end``
    parameters that control how much of the path is visible, enabling
    draw-on and draw-off effects.

    Args:
        path: SVG path data string.
        trim_start: Start of visible portion (0.0–1.0). Animatable.
        trim_end: End of visible portion (0.0–1.0). Animatable.
        stroke_color: Color of the stroke.
        stroke_width: Width of the stroke in pixels.
    """

    path: str = ""
    trim_start: float = 0.0
    trim_end: float = 1.0
    stroke_color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0, 1.0))
    stroke_width: float = 2.0
    _segments: list[_PathSegment] = field(default_factory=list, repr=False)
    _total_length: float = 0.0

    def __init__(
        self,
        path: str = "",
        trim_start: float = 0.0,
        trim_end: float = 1.0,
        stroke_color: ColorInput = "#FFFFFF",
        stroke_width: float = 2.0,
    ) -> None:
        """Initialize a StrokeClip.

        Args:
            path: SVG path data string.
            trim_start: Start of visible portion (0.0–1.0).
            trim_end: End of visible portion (0.0–1.0).
            stroke_color: Stroke color.
            stroke_width: Stroke width in pixels.
        """
        super().__init__()
        self.path = path
        self.trim_start = trim_start
        self.trim_end = trim_end
        self.stroke_color = Color.parse(stroke_color)
        self.stroke_width = stroke_width
        self._segments = _parse_svg_path(path) if path else []
        self._total_length = sum(s.length for s in self._segments)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render the trimmed stroke path via Cairo.

        Args:
            ctx: Render context.

        Returns:
            BGRA numpy array with the stroked path.
        """
        w, h = ctx.resolution.width, ctx.resolution.height
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surface)

        if not self._segments or self.trim_start >= self.trim_end:
            buf = surface.get_data()
            return np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4)).copy()

        # Set up dash pattern to achieve trimming
        start_dist = self.trim_start * self._total_length
        visible_dist = (self.trim_end - self.trim_start) * self._total_length

        # Draw the full path
        self._draw_path(cr)

        # Set stroke color (BGRA → Cairo expects RGBA)
        cr.set_source_rgba(
            self.stroke_color.r,
            self.stroke_color.g,
            self.stroke_color.b,
            self.stroke_color.a,
        )
        cr.set_line_width(self.stroke_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Use dash offset for trimming
        if start_dist > 0 or visible_dist < self._total_length:
            remaining = self._total_length - start_dist - visible_dist
            cr.set_dash([visible_dist, max(remaining, 0.001)], start_dist)

        cr.stroke()

        buf = surface.get_data()
        frame = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4)).copy()
        return frame

    def _draw_path(self, cr: cairo.Context[cairo.ImageSurface]) -> None:
        """Draw the SVG path segments onto a Cairo context.

        Args:
            cr: Cairo context.
        """
        if not self._segments:
            return

        first = self._segments[0]
        cr.move_to(first.start.x, first.start.y)

        for seg in self._segments:
            if seg.cp1 is not None and seg.cp2 is not None:
                cr.curve_to(
                    seg.cp1.x,
                    seg.cp1.y,
                    seg.cp2.x,
                    seg.cp2.y,
                    seg.end.x,
                    seg.end.y,
                )
            else:
                cr.line_to(seg.end.x, seg.end.y)


# ---------------------------------------------------------------------------
# Path morphing for ShapeClip
# ---------------------------------------------------------------------------


def morph_paths(
    path_a: str,
    path_b: str,
    progress: float,
) -> str:
    """Interpolate between two SVG paths.

    Both paths must have the same number of segments and the same
    command structure. Returns an SVG path string with interpolated
    coordinates.

    Args:
        path_a: Start SVG path.
        path_b: End SVG path.
        progress: Interpolation factor (0.0 = path_a, 1.0 = path_b).

    Returns:
        Interpolated SVG path string.

    Raises:
        ValueError: If paths have different segment counts.
    """
    segs_a = _parse_svg_path(path_a)
    segs_b = _parse_svg_path(path_b)

    if len(segs_a) != len(segs_b):
        msg = f"Path segment count mismatch: {len(segs_a)} vs {len(segs_b)}"
        raise ValueError(msg)

    if not segs_a:
        return ""

    t = max(0.0, min(1.0, progress))
    parts: list[str] = []

    # Move to first point
    first_a = segs_a[0].start
    first_b = segs_b[0].start
    mx = first_a.x + (first_b.x - first_a.x) * t
    my = first_a.y + (first_b.y - first_a.y) * t
    parts.append(f"M {mx:.2f} {my:.2f}")

    for sa, sb in zip(segs_a, segs_b, strict=True):
        if sa.cp1 is not None and sa.cp2 is not None and sb.cp1 is not None and sb.cp2 is not None:
            cx1 = sa.cp1.x + (sb.cp1.x - sa.cp1.x) * t
            cy1 = sa.cp1.y + (sb.cp1.y - sa.cp1.y) * t
            cx2 = sa.cp2.x + (sb.cp2.x - sa.cp2.x) * t
            cy2 = sa.cp2.y + (sb.cp2.y - sa.cp2.y) * t
            ex = sa.end.x + (sb.end.x - sa.end.x) * t
            ey = sa.end.y + (sb.end.y - sa.end.y) * t
            parts.append(f"C {cx1:.2f} {cy1:.2f} {cx2:.2f} {cy2:.2f} {ex:.2f} {ey:.2f}")
        else:
            ex = sa.end.x + (sb.end.x - sa.end.x) * t
            ey = sa.end.y + (sb.end.y - sa.end.y) * t
            parts.append(f"L {ex:.2f} {ey:.2f}")

    return " ".join(parts)
