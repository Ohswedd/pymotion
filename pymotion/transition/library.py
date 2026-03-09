"""Built-in transition library — 20 transitions for Phase 0.2.

Provides basic, directional, and zoom transitions between clips.
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
    """Cross-dissolve transition — linear blend from A to B.

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
        return _blend(clip_a, clip_b, progress)


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
    """Resize an image using nearest-neighbor interpolation.

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

    y_indices = np.clip((np.arange(target_h) * sh / target_h).astype(np.intp), 0, sh - 1)
    x_indices = np.clip((np.arange(target_w) * sw / target_w).astype(np.intp), 0, sw - 1)
    return src[np.ix_(y_indices, x_indices)]
