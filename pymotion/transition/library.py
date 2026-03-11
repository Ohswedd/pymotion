"""Built-in transition library — 39 transitions.

Provides basic, directional, zoom, wipe, and advanced transitions between clips.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pymotion.transition.base import Transition
from pymotion.utils.color import Color, ColorInput


def _blend(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """Alpha-blend two frames. Helper to avoid code duplication."""
    af = a.astype(np.float32)
    bf = b.astype(np.float32)
    result = af * (1.0 - t) + bf * t
    return np.clip(result, 0, 255).astype(np.uint8)


# --- Basic Transitions ---


@dataclass
class Fade(Transition):
    """Simple fade transition — clip A fades out while clip B fades in.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a fade transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        return _blend(clip_a, clip_b, progress)


@dataclass
class FadeToBlack(Transition):
    """Fade to black then from black — dip to black transition.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a fade-to-black transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        black = np.zeros_like(clip_a)
        if progress < 0.5:
            return _blend(clip_a, black, progress * 2)
        return _blend(black, clip_b, (progress - 0.5) * 2)


@dataclass
class FadeToWhite(Transition):
    """Fade to white then from white — dip to white transition.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a fade-to-white transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        white = np.full_like(clip_a, 255)
        if progress < 0.5:
            return _blend(clip_a, white, progress * 2)
        return _blend(white, clip_b, (progress - 0.5) * 2)


@dataclass
class DipToColor(Transition):
    """Fade to a specified color then from that color.

    Args:
        duration: Transition duration in frames.
        color: The intermediate color.
    """

    color: Color = Color(0.0, 0.0, 0.0, 1.0)

    def __init__(self, duration: int = 30, color: ColorInput = "#000000") -> None:
        """Initialize DipToColor transition.

        Args:
            duration: Transition duration in frames.
            color: The intermediate color.
        """
        self.duration = duration
        self.color = Color.parse(color)

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a dip-to-color transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        b, g, r, a = self.color.to_bgra_uint8()
        color_frame = np.zeros_like(clip_a)
        color_frame[:, :, 0] = b
        color_frame[:, :, 1] = g
        color_frame[:, :, 2] = r
        color_frame[:, :, 3] = a
        if progress < 0.5:
            return _blend(clip_a, color_frame, progress * 2)
        return _blend(color_frame, clip_b, (progress - 0.5) * 2)


@dataclass
class CrossDissolve(Transition):
    """Cross-dissolve transition — smooth S-curve blend from A to B.

    Unlike :class:`Fade` which uses a linear blend, CrossDissolve applies
    a smoothstep ease curve for a more cinematic dissolve.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a cross-dissolve transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Blended BGRA frame.
        """
        # Smoothstep S-curve for a more cinematic dissolve
        t = progress * progress * (3.0 - 2.0 * progress)
        return _blend(clip_a, clip_b, t)


@dataclass
class Cut(Transition):
    """Hard cut — instant switch from A to B at midpoint.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(
        self,
        clip_a: np.ndarray,
        clip_b: np.ndarray,
        progress: float,
    ) -> np.ndarray:
        """Render a cut transition frame.

        Args:
            clip_a: Outgoing clip frame (BGRA).
            clip_b: Incoming clip frame (BGRA).
            progress: Transition progress (0.0-1.0).

        Returns:
            Either clip A or clip B frame.
        """
        if progress < 0.5:
            return clip_a.copy()
        return clip_b.copy()


# --- Directional: Slide ---


def _slide(
    clip_a: np.ndarray,
    clip_b: np.ndarray,
    progress: float,
    dx: int,
    dy: int,
) -> np.ndarray:
    """Slide transition helper. A slides out in (dx,dy) direction, B slides in from opposite."""
    h, w = clip_a.shape[:2]
    result = np.zeros_like(clip_a)
    offset_x = int(dx * progress * w)
    offset_y = int(dy * progress * h)

    # Draw clip A shifted
    _blit_shifted(result, clip_a, offset_x, offset_y)
    # Draw clip B shifted from the opposite side
    _blit_shifted(result, clip_b, offset_x - dx * w, offset_y - dy * h)

    return result


def _blit_shifted(dst: np.ndarray, src: np.ndarray, ox: int, oy: int) -> None:
    """Blit src onto dst with pixel offset, clipping at edges."""
    h, w = dst.shape[:2]
    sy0 = max(0, -oy)
    sx0 = max(0, -ox)
    dy0 = max(0, oy)
    dx0 = max(0, ox)
    ch = min(h - dy0, h - sy0)
    cw = min(w - dx0, w - sx0)
    if ch > 0 and cw > 0:
        dst[dy0 : dy0 + ch, dx0 : dx0 + cw] = src[sy0 : sy0 + ch, sx0 : sx0 + cw]


@dataclass
class SlideLeft(Transition):
    """Slide transition — both clips slide to the left.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render slide-left transition."""
        return _slide(clip_a, clip_b, progress, -1, 0)


@dataclass
class SlideRight(Transition):
    """Slide transition — both clips slide to the right.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render slide-right transition."""
        return _slide(clip_a, clip_b, progress, 1, 0)


@dataclass
class SlideUp(Transition):
    """Slide transition — both clips slide upward.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render slide-up transition."""
        return _slide(clip_a, clip_b, progress, 0, -1)


@dataclass
class SlideDown(Transition):
    """Slide transition — both clips slide downward.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render slide-down transition."""
        return _slide(clip_a, clip_b, progress, 0, 1)


# --- Directional: Push ---


def _push(
    clip_a: np.ndarray,
    clip_b: np.ndarray,
    progress: float,
    dx: int,
    dy: int,
) -> np.ndarray:
    """Push transition. B pushes A out in the given direction."""
    h, w = clip_a.shape[:2]
    result = np.zeros_like(clip_a)
    offset_x = int(dx * progress * w)
    offset_y = int(dy * progress * h)

    # A is pushed away
    _blit_shifted(result, clip_a, offset_x, offset_y)
    # B comes in from the opposite side
    _blit_shifted(result, clip_b, offset_x - dx * w, offset_y - dy * h)

    return result


@dataclass
class PushLeft(Transition):
    """Push transition — B pushes A to the left.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render push-left transition."""
        return _push(clip_a, clip_b, progress, -1, 0)


@dataclass
class PushRight(Transition):
    """Push transition — B pushes A to the right.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render push-right transition."""
        return _push(clip_a, clip_b, progress, 1, 0)


@dataclass
class PushUp(Transition):
    """Push transition — B pushes A upward.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render push-up transition."""
        return _push(clip_a, clip_b, progress, 0, -1)


@dataclass
class PushDown(Transition):
    """Push transition — B pushes A downward.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render push-down transition."""
        return _push(clip_a, clip_b, progress, 0, 1)


# --- Directional: Cover ---


@dataclass
class CoverLeft(Transition):
    """Cover transition — B slides in from the right, covering A.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render cover-left transition."""
        h, w = clip_a.shape[:2]
        result = clip_a.copy()
        offset = int((1 - progress) * w)
        _blit_shifted(result, clip_b, offset, 0)
        return result


@dataclass
class CoverRight(Transition):
    """Cover transition — B slides in from the left, covering A.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render cover-right transition."""
        h, w = clip_a.shape[:2]
        result = clip_a.copy()
        offset = -int((1 - progress) * w)
        _blit_shifted(result, clip_b, offset, 0)
        return result


# --- Directional: Reveal ---


@dataclass
class RevealLeft(Transition):
    """Reveal transition — A slides away to the left, revealing B beneath.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render reveal-left transition."""
        h, w = clip_a.shape[:2]
        result = clip_b.copy()
        offset = -int(progress * w)
        _blit_shifted(result, clip_a, offset, 0)
        return result


@dataclass
class RevealRight(Transition):
    """Reveal transition — A slides away to the right, revealing B beneath.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render reveal-right transition."""
        h, w = clip_a.shape[:2]
        result = clip_b.copy()
        offset = int(progress * w)
        _blit_shifted(result, clip_a, offset, 0)
        return result


# --- Zoom ---


@dataclass
class ZoomIn(Transition):
    """Zoom-in transition — A zooms in while fading to B.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render zoom-in transition."""
        h, w = clip_a.shape[:2]
        scale = 1.0 + progress * 0.5  # Zoom from 1x to 1.5x

        # Crop center of A at increasing zoom
        crop_h = int(h / scale)
        crop_w = int(w / scale)
        y0 = (h - crop_h) // 2
        x0 = (w - crop_w) // 2
        cropped = clip_a[y0 : y0 + crop_h, x0 : x0 + crop_w]

        # Resize back to full size using simple nearest-neighbor
        zoomed = _resize_nearest(cropped, w, h)

        return _blend(zoomed, clip_b, progress)


@dataclass
class ZoomOut(Transition):
    """Zoom-out transition — B zooms out from large to normal while blending.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render zoom-out transition."""
        h, w = clip_a.shape[:2]
        scale = 1.5 - progress * 0.5  # Zoom from 1.5x to 1x

        crop_h = int(h / scale)
        crop_w = int(w / scale)
        y0 = (h - crop_h) // 2
        x0 = (w - crop_w) // 2
        cropped = clip_b[y0 : y0 + crop_h, x0 : x0 + crop_w]

        zoomed = _resize_nearest(cropped, w, h)

        return _blend(clip_a, zoomed, progress)


def _resize_nearest(src: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """Resize an image using bilinear interpolation.

    Args:
        src: Source BGRA image.
        target_w: Target width.
        target_h: Target height.

    Returns:
        Resized BGRA image.
    """
    sh, sw = src.shape[:2]
    if sh == 0 or sw == 0:
        return np.zeros((target_h, target_w, 4), dtype=np.uint8)

    # Bilinear interpolation for smooth scaling
    y_src = np.linspace(0, sh - 1, target_h, dtype=np.float32)
    x_src = np.linspace(0, sw - 1, target_w, dtype=np.float32)

    y0 = np.floor(y_src).astype(np.intp)
    x0 = np.floor(x_src).astype(np.intp)
    y1 = np.minimum(y0 + 1, sh - 1)
    x1 = np.minimum(x0 + 1, sw - 1)

    wy = (y_src - y0).reshape(target_h, 1, 1)
    wx = (x_src - x0).reshape(1, target_w, 1)

    top = (
        src[np.ix_(y0, x0)].astype(np.float32) * (1.0 - wx)
        + src[np.ix_(y0, x1)].astype(np.float32) * wx
    )
    bot = (
        src[np.ix_(y1, x0)].astype(np.float32) * (1.0 - wx)
        + src[np.ix_(y1, x1)].astype(np.float32) * wx
    )
    result = top * (1.0 - wy) + bot * wy
    out: np.ndarray = np.clip(result, 0, 255).astype(np.uint8)
    return out


@dataclass
class ZoomBlur(Transition):
    """Zoom-blur transition — A blurs outward while fading to B.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render zoom-blur transition."""
        h, w = clip_a.shape[:2]
        # Simulate zoom blur by blending multiple zoom levels of A
        blurred = clip_a.astype(np.float32)
        n_samples = 5
        for i in range(1, n_samples + 1):
            scale = 1.0 + progress * 0.3 * i / n_samples
            crop_h = max(1, int(h / scale))
            crop_w = max(1, int(w / scale))
            y0 = (h - crop_h) // 2
            x0 = (w - crop_w) // 2
            cropped = clip_a[y0 : y0 + crop_h, x0 : x0 + crop_w]
            zoomed = _resize_nearest(cropped, w, h)
            blurred += zoomed.astype(np.float32)
        blurred /= n_samples + 1
        blurred_u8 = np.clip(blurred, 0, 255).astype(np.uint8)
        return _blend(blurred_u8, clip_b, progress)


@dataclass
class ScaleDissolve(Transition):
    """Scale-dissolve — A scales down while dissolving to B.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render scale-dissolve transition."""
        h, w = clip_a.shape[:2]
        scale = 1.0 - progress * 0.5  # Scale A from 1.0 to 0.5
        new_h = max(1, int(h * scale))
        new_w = max(1, int(w * scale))
        scaled = _resize_nearest(clip_a, new_w, new_h)

        # Center the scaled A on a transparent canvas
        canvas = np.zeros_like(clip_a)
        y0 = (h - new_h) // 2
        x0 = (w - new_w) // 2
        canvas[y0 : y0 + new_h, x0 : x0 + new_w] = scaled

        return _blend(canvas, clip_b, progress)


# --- Directional: Cover Up/Down ---


@dataclass
class CoverUp(Transition):
    """Cover transition — B slides in from the bottom, covering A.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render cover-up transition."""
        h, _w = clip_a.shape[:2]
        result = clip_a.copy()
        offset = int((1 - progress) * h)
        _blit_shifted(result, clip_b, 0, offset)
        return result


@dataclass
class CoverDown(Transition):
    """Cover transition — B slides in from the top, covering A.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render cover-down transition."""
        h, _w = clip_a.shape[:2]
        result = clip_a.copy()
        offset = -int((1 - progress) * h)
        _blit_shifted(result, clip_b, 0, offset)
        return result


# --- Directional: Reveal Up/Down ---


@dataclass
class RevealUp(Transition):
    """Reveal transition — A slides upward, revealing B beneath.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render reveal-up transition."""
        h, _w = clip_a.shape[:2]
        result = clip_b.copy()
        offset = -int(progress * h)
        _blit_shifted(result, clip_a, 0, offset)
        return result


@dataclass
class RevealDown(Transition):
    """Reveal transition — A slides downward, revealing B beneath.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render reveal-down transition."""
        h, _w = clip_a.shape[:2]
        result = clip_b.copy()
        offset = int(progress * h)
        _blit_shifted(result, clip_a, 0, offset)
        return result


# --- Wipe Transitions ---


@dataclass
class WipeLeft(Transition):
    """Wipe-left transition — B is revealed from right to left.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render wipe-left transition."""
        h, w = clip_a.shape[:2]
        result = clip_a.copy()
        boundary = int((1 - progress) * w)
        result[:, :boundary] = clip_a[:, :boundary]
        result[:, boundary:] = clip_b[:, boundary:]
        return result


@dataclass
class WipeRight(Transition):
    """Wipe-right transition — B is revealed from left to right.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render wipe-right transition."""
        h, w = clip_a.shape[:2]
        result = clip_a.copy()
        boundary = int(progress * w)
        result[:, :boundary] = clip_b[:, :boundary]
        return result


@dataclass
class WipeDiagonal(Transition):
    """Diagonal wipe — B is revealed along a top-left to bottom-right diagonal.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render diagonal wipe transition."""
        h, w = clip_a.shape[:2]
        # Normalized coordinates: (x/w + y/h) ranges from 0 to 2
        y_coords = np.arange(h).reshape(h, 1) / max(h - 1, 1)
        x_coords = np.arange(w).reshape(1, w) / max(w - 1, 1)
        diagonal = (x_coords + y_coords) / 2.0  # Normalize to 0..1
        if progress >= 1.0:
            return clip_b.copy()
        mask = (diagonal < progress).reshape(h, w, 1)
        return np.where(mask, clip_b, clip_a)


@dataclass
class CircularWipe(Transition):
    """Circular wipe — B is revealed through an expanding circle from center.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render circular wipe transition."""
        h, w = clip_a.shape[:2]
        cy, cx = h / 2.0, w / 2.0
        max_radius = np.sqrt(cx * cx + cy * cy)
        radius = progress * max_radius

        y_coords = np.arange(h).reshape(h, 1) - cy
        x_coords = np.arange(w).reshape(1, w) - cx
        dist = np.sqrt(y_coords * y_coords + x_coords * x_coords)

        mask = (
            (dist < radius).reshape(h, w, 1) if progress < 1.0 else np.ones((h, w, 1), dtype=bool)
        )
        return np.where(mask, clip_b, clip_a)


# --- Advanced Transitions ---


@dataclass
class IrisIn(Transition):
    """Iris-in transition — B is revealed through a shrinking circle to full.

    The circle starts at zero radius and expands to cover the full frame.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render iris-in transition with feathered edge."""
        h, w = clip_a.shape[:2]
        cy, cx = h / 2.0, w / 2.0
        max_radius = np.sqrt(cx * cx + cy * cy)
        radius = progress * max_radius
        feather = max(4.0, max_radius * 0.03)  # Soft edge

        y_coords = np.arange(h, dtype=np.float32).reshape(h, 1) - cy
        x_coords = np.arange(w, dtype=np.float32).reshape(1, w) - cx
        dist = np.sqrt(y_coords * y_coords + x_coords * x_coords)

        if progress >= 1.0:
            return clip_b.copy()
        # Smooth feathered alpha with smoothstep curve
        t = np.clip((radius - dist) / max(feather, 0.01), 0.0, 1.0)
        alpha = t * t * (3.0 - 2.0 * t)  # smoothstep
        alpha_3d = alpha.reshape(h, w, 1)
        result = clip_a.astype(np.float32) * (1.0 - alpha_3d) + clip_b.astype(np.float32) * alpha_3d
        out: np.ndarray = np.clip(result, 0, 255).astype(np.uint8)
        return out


@dataclass
class IrisOut(Transition):
    """Iris-out transition — A is hidden by a shrinking circle revealing B.

    The circle starts at full size and shrinks to zero, showing B underneath.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render iris-out transition."""
        h, w = clip_a.shape[:2]
        cy, cx = h / 2.0, w / 2.0
        max_radius = np.sqrt(cx * cx + cy * cy)
        radius = (1 - progress) * max_radius

        y_coords = np.arange(h).reshape(h, 1) - cy
        x_coords = np.arange(w).reshape(1, w) - cx
        dist = np.sqrt(y_coords * y_coords + x_coords * x_coords)

        if progress <= 0.0:
            return clip_a.copy()
        if progress >= 1.0:
            return clip_b.copy()
        feather = max(4.0, max_radius * 0.03)
        t = np.clip((radius - dist) / max(feather, 0.01), 0.0, 1.0)
        alpha = t * t * (3.0 - 2.0 * t)  # smoothstep
        alpha_3d = alpha.reshape(h, w, 1)
        result = clip_a.astype(np.float32) * alpha_3d + clip_b.astype(np.float32) * (1.0 - alpha_3d)
        out: np.ndarray = np.clip(result, 0, 255).astype(np.uint8)
        return out


@dataclass
class PixelDissolve(Transition):
    """Pixel-dissolve transition — pixels randomly switch from A to B.

    Uses a deterministic random pattern (seeded) so the transition is reproducible.

    Args:
        duration: Transition duration in frames.
        seed: Random seed for the pixel ordering.
    """

    seed: int = 42

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render pixel-dissolve transition."""
        h, w = clip_a.shape[:2]
        rng = np.random.default_rng(self.seed)
        # Generate a random threshold per pixel
        thresholds = rng.random((h, w)).reshape(h, w, 1)
        mask = thresholds <= progress
        return np.where(mask, clip_b, clip_a)


@dataclass
class Glitch(Transition):
    """Glitch transition — random horizontal slices shift with color channel separation.

    Args:
        duration: Transition duration in frames.
        seed: Random seed for glitch pattern.
    """

    seed: int = 42

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render glitch transition."""
        h, w = clip_a.shape[:2]
        # Start with a blend base
        base = _blend(clip_a, clip_b, progress)
        result = base.copy()

        # Generate slice-based distortion
        rng = np.random.default_rng(self.seed + int(progress * 100))
        intensity = int(progress * (1 - progress) * 4 * w * 0.2)  # Peak at midpoint
        n_slices = max(1, int(h * 0.15))

        for _ in range(n_slices):
            y = rng.integers(0, h)
            slice_h = min(rng.integers(1, max(2, h // 10)), h - y)
            shift = rng.integers(-intensity, max(1, intensity + 1))
            if shift != 0:
                result[y : y + slice_h] = np.roll(base[y : y + slice_h], shift, axis=1)

        # Color channel separation — shift R and B channels in opposite directions
        channel_shift = max(1, int(progress * (1 - progress) * 4 * w * 0.03))
        if channel_shift > 0:
            # Shift blue channel (index 0) left, red channel (index 2) right
            result[:, :, 0] = np.roll(result[:, :, 0], -channel_shift, axis=1)
            result[:, :, 2] = np.roll(result[:, :, 2], channel_shift, axis=1)

        return result


@dataclass
class FilmBurn(Transition):
    """Film-burn transition — bright overexposure wipe from A to B.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render film-burn transition."""
        h, w = clip_a.shape[:2]

        # Create a horizontal burn gradient
        x_coords = np.arange(w, dtype=np.float32) / max(w - 1, 1)
        # The burn edge sweeps across with progress
        burn_center = progress
        burn = np.exp(-((x_coords - burn_center) ** 2) / max(0.01, progress * (1 - progress) * 0.5))
        burn_2d = burn.reshape(1, w, 1)  # broadcast over h and channels

        base = _blend(clip_a, clip_b, progress)
        # Add white burn glow
        result = base.astype(np.float32) + burn_2d * 255 * 0.7 * (4 * progress * (1 - progress))
        out: np.ndarray = np.clip(result, 0, 255).astype(np.uint8)
        return out


@dataclass
class PageTurn(Transition):
    """Page-turn transition — A peels away like a turning page, revealing B.

    Simulated with a diagonal wipe and shadow effect.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render page-turn transition."""
        h, w = clip_a.shape[:2]

        # Diagonal fold line sweeps from right to left
        x_coords = np.arange(w, dtype=np.float32) / max(w - 1, 1)
        y_coords = np.arange(h, dtype=np.float32) / max(h - 1, 1)
        xx, yy = np.meshgrid(x_coords, y_coords)
        # Fold boundary: line sweeps from x=1 to x=0
        fold = (1.0 - progress) + yy * 0.2  # slight diagonal
        mask = (xx > fold).reshape(h, w, 1)

        # Shadow near fold edge
        dist_to_fold = np.abs(xx - fold)
        shadow = np.clip(1.0 - dist_to_fold * 5, 0, 1) * 0.3 * (1 if progress > 0 else 0)
        shadow_3d = shadow.reshape(h, w, 1)

        base = np.where(mask, clip_b, clip_a)
        # Darken near the fold
        result = base.astype(np.float32) * (1.0 - shadow_3d)
        out: np.ndarray = np.clip(result, 0, 255).astype(np.uint8)
        return out


@dataclass
class Vortex(Transition):
    """Vortex transition — pixels swirl from A to B.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render vortex transition."""
        h, w = clip_a.shape[:2]
        cy, cx = h / 2.0, w / 2.0

        y_coords = np.arange(h, dtype=np.float32) - cy
        x_coords = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

        dist = np.sqrt(xx * xx + yy * yy)
        max_dist = np.sqrt(cx * cx + cy * cy)
        normalized_dist = dist / max(max_dist, 1)

        # Swirl angle increases with progress, stronger near center
        angle = progress * np.pi * 2 * (1 - normalized_dist)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        src_x = (cos_a * xx - sin_a * yy + cx).astype(np.intp)
        src_y = (sin_a * xx + cos_a * yy + cy).astype(np.intp)

        src_x = np.clip(src_x, 0, w - 1)
        src_y = np.clip(src_y, 0, h - 1)

        # Sample from A with swirl distortion, then blend to B
        swirled = clip_a[src_y, src_x]
        return _blend(swirled, clip_b, progress)


@dataclass
class Shatter(Transition):
    """Shatter transition — A breaks into rectangular pieces that fall away.

    Args:
        duration: Transition duration in frames.
        seed: Random seed for shard pattern.
        grid_size: Number of shard columns/rows.
    """

    seed: int = 42
    grid_size: int = 6

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render shatter transition."""
        h, w = clip_a.shape[:2]
        result = clip_b.copy()
        rng = np.random.default_rng(self.seed)

        cell_h = max(1, h // self.grid_size)
        cell_w = max(1, w // self.grid_size)

        # Each shard has a random "break time" — once progress passes it, the shard disappears
        for gy in range(self.grid_size + 1):
            for gx in range(self.grid_size + 1):
                break_time = rng.random()
                if progress < break_time:
                    # This shard of A still visible
                    y0 = gy * cell_h
                    x0 = gx * cell_w
                    y1 = min(y0 + cell_h, h)
                    x1 = min(x0 + cell_w, w)
                    if y1 > y0 and x1 > x0:
                        # Apply slight offset based on progress for "falling" feel
                        fall = int((progress / max(break_time, 0.01)) * cell_h * 0.3)
                        dy = min(fall, h - y1)
                        result[y0 + dy : y1 + dy, x0:x1] = clip_a[y0:y1, x0:x1]

        return result


@dataclass
class MorphWarp(Transition):
    """Morph-warp transition — A warps and morphs into B.

    Uses a sinusoidal displacement field that increases with progress.

    Args:
        duration: Transition duration in frames.
    """

    def render_frame(self, clip_a: np.ndarray, clip_b: np.ndarray, progress: float) -> np.ndarray:
        """Render morph-warp transition."""
        h, w = clip_a.shape[:2]

        y_coords = np.arange(h, dtype=np.float32)
        x_coords = np.arange(w, dtype=np.float32)
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

        # Sinusoidal warp that increases with progress
        amplitude = progress * (1 - progress) * 40  # Peak at midpoint
        freq = 0.05
        dx = (amplitude * np.sin(yy * freq + progress * 10)).astype(np.intp)
        dy = (amplitude * np.cos(xx * freq + progress * 10)).astype(np.intp)

        src_x = np.clip(xx.astype(np.intp) + dx, 0, w - 1)
        src_y = np.clip(yy.astype(np.intp) + dy, 0, h - 1)

        # Warp A, then blend with B
        warped = clip_a[src_y, src_x]
        return _blend(warped, clip_b, progress)
