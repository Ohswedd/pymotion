"""Masking system — BezierMask, gradient masks, TrackMatte, TextMask.

Masks produce a single-channel (H, W) uint8 array where 255 = visible
and 0 = hidden.  Multiple masks per clip are combined via boolean
operations (union, intersect, subtract).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.utils.logging import get_logger
from pymotion.utils.math import Vec2

if TYPE_CHECKING:
    from pymotion.clip.base import Clip

logger = get_logger(__name__)


class MaskOp(Enum):
    """Boolean operation for combining multiple masks.

    Attributes:
        ADD: Union — ``max(existing, new)``.
        INTERSECT: Intersection — ``min(existing, new)``.
        SUBTRACT: Subtraction — ``clamp(existing - new, 0, 255)``.
    """

    ADD = "add"
    INTERSECT = "intersect"
    SUBTRACT = "subtract"


class Mask(ABC):
    """Abstract base class for all mask types.

    Subclasses implement :meth:`render_mask` to produce a grayscale
    ``(H, W)`` uint8 array.  Post-processing (feather, expansion,
    invert, opacity) is handled by :func:`_process_single_mask`.
    """

    @abstractmethod
    def render_mask(self, ctx: RenderContext) -> np.ndarray:
        """Render the raw mask for a single frame.

        Args:
            ctx: Render context providing resolution and frame info.

        Returns:
            Single-channel ``(H, W)`` numpy array, dtype uint8,
            where 255 = fully visible and 0 = fully hidden.
        """
        ...


@dataclass
class MaskGroup:
    """A mask paired with its boolean combine operation.

    Args:
        mask: The mask instance.
        op: Boolean operation used when combining with previous masks.
    """

    mask: Mask
    op: MaskOp = MaskOp.ADD


# ---------------------------------------------------------------------------
# Mask post-processing and combination
# ---------------------------------------------------------------------------


def _process_single_mask(
    mask: Mask,
    ctx: RenderContext,
    feather: float,
    expansion: float,
    invert: bool,
    opacity: float,
) -> np.ndarray:
    """Render a mask and apply feather / expansion / invert / opacity.

    Args:
        mask: Mask instance.
        ctx: Render context.
        feather: Feather radius in pixels.
        expansion: Expand (>0) or contract (<0) mask.
        invert: If True, invert the mask.
        opacity: Mask opacity (0.0–1.0).

    Returns:
        Processed ``(H, W)`` uint8 mask.
    """
    raw = mask.render_mask(ctx)

    # Convert to float32 0-1 for processing
    mask_f = raw.astype(np.float32) / 255.0

    # Expansion (choke)
    if abs(expansion) > 1e-6:
        from pymotion.effects.keying import _choke_mask

        mask_f = _choke_mask(mask_f, expansion)

    # Feather (blur)
    if feather > 0:
        from pymotion.effects.keying import _feather_mask

        mask_f = _feather_mask(mask_f, int(feather))

    # Invert
    if invert:
        mask_f = 1.0 - mask_f

    # Opacity
    if opacity < 1.0:
        mask_f = mask_f * opacity

    return np.clip(mask_f * 255, 0, 255).astype(np.uint8)


def apply_masks(
    frame: np.ndarray,
    masks: list[MaskGroup],
    ctx: RenderContext,
) -> np.ndarray:
    """Combine all masks and multiply into the frame's alpha channel.

    The first mask always uses ADD (union with an initial zero mask).
    Subsequent masks use their specified operation.

    Args:
        frame: BGRA frame ``(H, W, 4)`` uint8.
        masks: List of MaskGroup instances.
        ctx: Render context.

    Returns:
        Frame with alpha channel modified by the combined mask.
    """
    if not masks:
        return frame

    h, w = frame.shape[:2]
    combined = np.zeros((h, w), dtype=np.uint8)

    for i, mg in enumerate(masks):
        m = mg.mask
        # Extract per-mask settings
        feather = getattr(m, "feather", 0.0)
        expansion = getattr(m, "expansion", 0.0)
        invert = getattr(m, "invert", False)
        opacity = getattr(m, "opacity", 1.0)

        processed = _process_single_mask(m, ctx, feather, expansion, invert, opacity)

        if i == 0 or mg.op == MaskOp.ADD:
            combined = np.maximum(combined, processed)
        elif mg.op == MaskOp.INTERSECT:
            combined = np.minimum(combined, processed)
        elif mg.op == MaskOp.SUBTRACT:
            combined = np.clip(
                combined.astype(np.int16) - processed.astype(np.int16), 0, 255
            ).astype(np.uint8)

    # Multiply combined mask into frame alpha
    result = frame.copy()
    result[:, :, 3] = ((frame[:, :, 3].astype(np.uint16) * combined.astype(np.uint16)) >> 8).astype(
        np.uint8
    )
    return result


# ---------------------------------------------------------------------------
# BezierMask
# ---------------------------------------------------------------------------


@dataclass
class BezierPoint:
    """A control point on a bezier path.

    Args:
        vertex: The on-curve point position (pixels).
        in_handle: Incoming tangent handle (absolute coords). None for sharp corners.
        out_handle: Outgoing tangent handle (absolute coords). None for sharp corners.
    """

    vertex: Vec2
    in_handle: Vec2 | None = None
    out_handle: Vec2 | None = None


@dataclass
class BezierMask(Mask):
    """A closed bezier-path mask rasterized via Cairo.

    Args:
        points: List of BezierPoint defining the closed path.
        feather: Edge softness radius in pixels.
        expansion: Expand (positive) or contract (negative) the mask.
        invert: If True, invert visibility.
        opacity: Mask opacity (0.0–1.0).
    """

    points: list[BezierPoint] = field(default_factory=list)
    feather: float = 0.0
    expansion: float = 0.0
    invert: bool = False
    opacity: float = 1.0
    _keyframes: dict[int, list[BezierPoint]] = field(default_factory=dict, repr=False)

    def set_points_at(self, frame: int, points: list[BezierPoint]) -> None:
        """Set control points for a specific frame (for animation).

        All keyframe point lists must have the same length as the
        initial ``points`` list.

        Args:
            frame: Frame number for this keyframe.
            points: Control points at this frame.

        Raises:
            ValueError: If point count differs from initial points.
        """
        if self.points and len(points) != len(self.points):
            msg = f"Point count mismatch: expected {len(self.points)}, got {len(points)}"
            raise ValueError(msg)
        self._keyframes[frame] = points

    def _get_points_at_frame(self, frame: int) -> list[BezierPoint]:
        """Get interpolated control points for a given frame.

        Args:
            frame: The frame to interpolate for.

        Returns:
            List of BezierPoint with interpolated positions.
        """
        if not self._keyframes:
            return self.points

        sorted_frames = sorted(self._keyframes.keys())

        # Exact match
        if frame in self._keyframes:
            return self._keyframes[frame]

        # Before first keyframe
        if frame <= sorted_frames[0]:
            return self._keyframes[sorted_frames[0]]

        # After last keyframe
        if frame >= sorted_frames[-1]:
            return self._keyframes[sorted_frames[-1]]

        # Find surrounding keyframes and interpolate
        for i in range(len(sorted_frames) - 1):
            f_a, f_b = sorted_frames[i], sorted_frames[i + 1]
            if f_a <= frame <= f_b:
                t = (frame - f_a) / max(f_b - f_a, 1)
                pts_a = self._keyframes[f_a]
                pts_b = self._keyframes[f_b]
                return _interpolate_points(pts_a, pts_b, t)

        return self.points

    def render_mask(self, ctx: RenderContext) -> np.ndarray:
        """Rasterize the bezier path to a grayscale mask via Cairo.

        Args:
            ctx: Render context.

        Returns:
            ``(H, W)`` uint8 mask.
        """
        import cairo

        w, h = ctx.resolution.width, ctx.resolution.height
        points = self._get_points_at_frame(ctx.local_frame)

        if len(points) < 2:
            return np.zeros((h, w), dtype=np.uint8)

        surface = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
        cr = cairo.Context(surface)

        # Build path
        first = points[0]
        cr.move_to(first.vertex.x, first.vertex.y)

        for i in range(1, len(points)):
            prev = points[i - 1]
            curr = points[i]

            if prev.out_handle is not None and curr.in_handle is not None:
                cr.curve_to(
                    prev.out_handle.x,
                    prev.out_handle.y,
                    curr.in_handle.x,
                    curr.in_handle.y,
                    curr.vertex.x,
                    curr.vertex.y,
                )
            elif prev.out_handle is not None:
                cr.curve_to(
                    prev.out_handle.x,
                    prev.out_handle.y,
                    curr.vertex.x,
                    curr.vertex.y,
                    curr.vertex.x,
                    curr.vertex.y,
                )
            elif curr.in_handle is not None:
                cr.curve_to(
                    prev.vertex.x,
                    prev.vertex.y,
                    curr.in_handle.x,
                    curr.in_handle.y,
                    curr.vertex.x,
                    curr.vertex.y,
                )
            else:
                cr.line_to(curr.vertex.x, curr.vertex.y)

        # Close path back to first point
        last = points[-1]
        if last.out_handle is not None and first.in_handle is not None:
            cr.curve_to(
                last.out_handle.x,
                last.out_handle.y,
                first.in_handle.x,
                first.in_handle.y,
                first.vertex.x,
                first.vertex.y,
            )
        else:
            cr.close_path()

        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.fill()

        # Extract alpha channel
        buf = surface.get_data()
        mask_arr = np.frombuffer(buf, dtype=np.uint8).reshape((h, w)).copy()
        return mask_arr


def _interpolate_points(
    pts_a: list[BezierPoint],
    pts_b: list[BezierPoint],
    t: float,
) -> list[BezierPoint]:
    """Linearly interpolate between two sets of BezierPoints.

    Args:
        pts_a: Start points.
        pts_b: End points.
        t: Interpolation factor (0.0 = pts_a, 1.0 = pts_b).

    Returns:
        Interpolated point list.
    """
    result: list[BezierPoint] = []
    for a, b in zip(pts_a, pts_b, strict=True):
        vertex = Vec2(
            a.vertex.x + (b.vertex.x - a.vertex.x) * t,
            a.vertex.y + (b.vertex.y - a.vertex.y) * t,
        )
        in_h: Vec2 | None = None
        if a.in_handle is not None and b.in_handle is not None:
            in_h = Vec2(
                a.in_handle.x + (b.in_handle.x - a.in_handle.x) * t,
                a.in_handle.y + (b.in_handle.y - a.in_handle.y) * t,
            )
        elif a.in_handle is not None:
            in_h = a.in_handle
        elif b.in_handle is not None:
            in_h = b.in_handle

        out_h: Vec2 | None = None
        if a.out_handle is not None and b.out_handle is not None:
            out_h = Vec2(
                a.out_handle.x + (b.out_handle.x - a.out_handle.x) * t,
                a.out_handle.y + (b.out_handle.y - a.out_handle.y) * t,
            )
        elif a.out_handle is not None:
            out_h = a.out_handle
        elif b.out_handle is not None:
            out_h = b.out_handle

        result.append(BezierPoint(vertex=vertex, in_handle=in_h, out_handle=out_h))
    return result


# ---------------------------------------------------------------------------
# Gradient Masks
# ---------------------------------------------------------------------------


@dataclass
class LinearGradientMask(Mask):
    """A linear gradient mask from start to end point.

    Pixels along the gradient direction ramp from 0 (at ``start``)
    to 255 (at ``end``).

    Args:
        start: Gradient start position (fully hidden).
        end: Gradient end position (fully visible).
        feather: Edge softness radius in pixels.
        expansion: Expand (positive) or contract (negative).
        invert: If True, invert visibility.
        opacity: Mask opacity (0.0–1.0).
    """

    start: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    end: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    feather: float = 0.0
    expansion: float = 0.0
    invert: bool = False
    opacity: float = 1.0

    def render_mask(self, ctx: RenderContext) -> np.ndarray:
        """Render the linear gradient mask.

        Args:
            ctx: Render context.

        Returns:
            ``(H, W)`` uint8 mask.
        """
        w, h = ctx.resolution.width, ctx.resolution.height

        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length_sq = dx * dx + dy * dy

        if length_sq < 1e-10:
            return np.full((h, w), 255, dtype=np.uint8)

        # Pixel grid
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        # Project each pixel onto the gradient vector
        proj = ((xx - self.start.x) * dx + (yy - self.start.y) * dy) / length_sq
        # Clamp to [0, 1] and scale to [0, 255]
        result: np.ndarray = np.clip(proj * 255, 0, 255).astype(np.uint8)
        return result


@dataclass
class RadialGradientMask(Mask):
    """A radial gradient mask centered at a point.

    Pixels ramp from 255 (at center) to 0 (at radius).

    Args:
        center: Gradient center position.
        radius: Gradient radius in pixels.
        feather: Edge softness radius in pixels.
        expansion: Expand (positive) or contract (negative).
        invert: If True, invert visibility.
        opacity: Mask opacity (0.0–1.0).
    """

    center: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    radius: float = 100.0
    feather: float = 0.0
    expansion: float = 0.0
    invert: bool = False
    opacity: float = 1.0

    def render_mask(self, ctx: RenderContext) -> np.ndarray:
        """Render the radial gradient mask.

        Args:
            ctx: Render context.

        Returns:
            ``(H, W)`` uint8 mask.
        """
        w, h = ctx.resolution.width, ctx.resolution.height

        if self.radius <= 0:
            return np.zeros((h, w), dtype=np.uint8)

        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dist = np.sqrt((xx - self.center.x) ** 2 + (yy - self.center.y) ** 2)
        # 255 at center, 0 at radius
        mask_f = 1.0 - dist / self.radius
        result: np.ndarray = np.clip(mask_f * 255, 0, 255).astype(np.uint8)
        return result


# ---------------------------------------------------------------------------
# TrackMatte
# ---------------------------------------------------------------------------


@dataclass
class TrackMatte(Mask):
    """Use another clip's alpha or luminance as a mask.

    Args:
        source: The clip whose output drives the mask.
        mode: ``"alpha"`` uses the clip's alpha channel directly.
            ``"luma"`` computes BT.601 luminance from BGR.
        feather: Edge softness radius in pixels.
        expansion: Expand (positive) or contract (negative).
        invert: If True, invert visibility.
        opacity: Mask opacity (0.0–1.0).
    """

    source: Clip = field(default=None)  # type: ignore[assignment]
    mode: Literal["alpha", "luma"] = "alpha"
    feather: float = 0.0
    expansion: float = 0.0
    invert: bool = False
    opacity: float = 1.0

    def render_mask(self, ctx: RenderContext) -> np.ndarray:
        """Render the track matte mask from the source clip.

        Args:
            ctx: Render context.

        Returns:
            ``(H, W)`` uint8 mask.
        """
        if self.source is None:
            msg = "TrackMatte requires a source clip"
            raise ValueError(msg)

        rendered = self.source.render_with_effects(ctx)
        h, w = ctx.resolution.height, ctx.resolution.width

        # Resize if source has different resolution
        if rendered.shape[:2] != (h, w):
            try:
                import cv2  # type: ignore[import-not-found]

                rendered = cv2.resize(rendered, (w, h))
            except ImportError:
                row_idx = (np.arange(h) * rendered.shape[0] // h).clip(0, rendered.shape[0] - 1)
                col_idx = (np.arange(w) * rendered.shape[1] // w).clip(0, rendered.shape[1] - 1)
                rendered = rendered[np.ix_(row_idx, col_idx)]

        if self.mode == "alpha":
            return rendered[:, :, 3].copy()

        # Luma mode: BT.601 from BGR
        b = rendered[:, :, 0].astype(np.float32)
        g = rendered[:, :, 1].astype(np.float32)
        r = rendered[:, :, 2].astype(np.float32)
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        result: np.ndarray = np.clip(luma, 0, 255).astype(np.uint8)
        return result


# ---------------------------------------------------------------------------
# TextMask
# ---------------------------------------------------------------------------


@dataclass
class TextMask(Mask):
    """A text-shaped mask — clip is visible only through letterforms.

    Uses Cairo to render text to an alpha surface.

    Args:
        text: The text string to use as the mask.
        font: Font family name.
        size: Font size in pixels.
        feather: Edge softness radius in pixels.
        expansion: Expand (positive) or contract (negative).
        invert: If True, invert visibility.
        opacity: Mask opacity (0.0–1.0).
    """

    text: str = ""
    font: str = "sans-serif"
    size: float = 48.0
    feather: float = 0.0
    expansion: float = 0.0
    invert: bool = False
    opacity: float = 1.0

    def render_mask(self, ctx: RenderContext) -> np.ndarray:
        """Render text as a mask via Cairo.

        Args:
            ctx: Render context.

        Returns:
            ``(H, W)`` uint8 mask where letterforms are 255.
        """
        import cairo

        w, h = ctx.resolution.width, ctx.resolution.height

        if not self.text:
            return np.zeros((h, w), dtype=np.uint8)

        surface = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
        cr = cairo.Context(surface)

        cr.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(self.size)

        # Center the text
        extents = cr.text_extents(self.text)
        x = (w - extents.width) / 2 - extents.x_bearing
        y = (h - extents.height) / 2 - extents.y_bearing

        cr.move_to(x, y)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.show_text(self.text)

        buf = surface.get_data()
        mask_arr = np.frombuffer(buf, dtype=np.uint8).copy()

        # Cairo A8 format: stride may differ from width
        stride = surface.get_stride()
        if stride != w:
            padded = mask_arr.reshape((h, stride))
            mask_arr = padded[:, :w].copy()
        else:
            mask_arr = mask_arr.reshape((h, w))

        return mask_arr
