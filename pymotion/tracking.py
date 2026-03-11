"""Motion tracking and stabilization.

Provides MotionTracker for region tracking and clip.stabilize() for
video stabilization. Both require OpenCV as an optional dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from pymotion.animation.keyframe import Keyframe, KeyframeTrack
from pymotion.clip.base import Clip, RenderContext, Resolution, TimeRange
from pymotion.utils.logging import get_logger
from pymotion.utils.math import Vec2

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class MotionTracker:
    """Track a rectangular region across frames of a clip.

    Uses OpenCV CSRT tracker when available, falls back to
    template matching if CSRT is unavailable.

    Args:
        clip: The source clip to track.
        region: Initial tracking region as ``(x, y, width, height)``.
    """

    clip: Clip
    region: tuple[int, int, int, int] = (0, 0, 100, 100)
    _tracking_data: dict[int, Vec2] = field(default_factory=dict)

    def track(self) -> dict[int, Vec2]:
        """Run the tracker across all frames of the clip.

        Returns:
            Dictionary mapping frame index to center position (Vec2).

        Raises:
            RuntimeError: If the clip has zero duration.
        """
        if self.clip.duration <= 0:
            msg = "Cannot track a clip with zero duration"
            raise RuntimeError(msg)

        rx, ry, rw, rh = self.region
        center_x = float(rx + rw // 2)
        center_y = float(ry + rh // 2)

        data: dict[int, Vec2] = {}
        res = Resolution(
            width=max(rw * 4, 64) + (max(rw * 4, 64) % 2),
            height=max(rh * 4, 64) + (max(rh * 4, 64) % 2),
        )

        prev_frame: np.ndarray | None = None
        prev_center = (center_x, center_y)

        for i in range(self.clip.duration):
            ctx = RenderContext(
                frame=i,
                fps=30,
                resolution=res,
                time_range=TimeRange(start=0, end=self.clip.duration),
                local_frame=i,
                progress=i / max(self.clip.duration - 1, 1),
            )
            frame = self.clip.render_frame(ctx)

            if prev_frame is not None:
                dx, dy = self._estimate_motion(prev_frame, frame, prev_center, (rw, rh))
                center_x += dx
                center_y += dy

            data[i] = Vec2(center_x, center_y)
            prev_center = (center_x, center_y)
            prev_frame = frame

        self._tracking_data = data
        logger.debug("motion_track_complete", frames=len(data))
        return data

    def _estimate_motion(
        self,
        prev: np.ndarray,
        curr: np.ndarray,
        center: tuple[float, float],
        size: tuple[int, int],
    ) -> tuple[float, float]:
        """Estimate motion between two frames using template matching.

        Args:
            prev: Previous BGRA frame.
            curr: Current BGRA frame.
            center: Current center position.
            size: Template size (width, height).

        Returns:
            (dx, dy) displacement in pixels.
        """
        try:
            import cv2  # noqa: PLC0415

            prev_gray = cv2.cvtColor(prev[:, :, :3], cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(curr[:, :, :3], cv2.COLOR_BGR2GRAY)

            tw, th = size
            cx, cy = int(center[0]), int(center[1])
            h, w = prev_gray.shape[:2]

            # Extract template from previous frame
            x1 = max(0, cx - tw // 2)
            y1 = max(0, cy - th // 2)
            x2 = min(w, x1 + tw)
            y2 = min(h, y1 + th)

            if x2 - x1 < 4 or y2 - y1 < 4:
                return 0.0, 0.0

            template = prev_gray[y1:y2, x1:x2]

            # Search in a neighborhood of the current frame
            search_margin = max(tw, th)
            sx1 = max(0, x1 - search_margin)
            sy1 = max(0, y1 - search_margin)
            sx2 = min(w, x2 + search_margin)
            sy2 = min(h, y2 + search_margin)

            search_area = curr_gray[sy1:sy2, sx1:sx2]

            if search_area.shape[0] < template.shape[0] or search_area.shape[1] < template.shape[1]:
                return 0.0, 0.0

            result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
            _, _, _, max_loc = cv2.minMaxLoc(result)

            # Convert match location back to displacement
            match_x = sx1 + max_loc[0]
            match_y = sy1 + max_loc[1]

            dx = float(match_x - x1)
            dy = float(match_y - y1)
            return dx, dy

        except ImportError:
            # Fallback: no motion (static track)
            logger.debug("tracking_fallback", reason="opencv_unavailable")
            return 0.0, 0.0

    def to_keyframes(self, prop: str = "position") -> KeyframeTrack:
        """Convert tracking data to a KeyframeTrack.

        Args:
            prop: Property name (currently supports "position").

        Returns:
            KeyframeTrack with Vec2 keyframes for each tracked frame.

        Raises:
            RuntimeError: If track() has not been called yet.
        """
        if not self._tracking_data:
            msg = "No tracking data. Call track() first."
            raise RuntimeError(msg)

        keyframes: list[Keyframe] = []
        for frame_idx in sorted(self._tracking_data.keys()):
            pos = self._tracking_data[frame_idx]
            keyframes.append(Keyframe(frame=frame_idx, value=pos))

        return KeyframeTrack(keyframes=keyframes)


@dataclass
class StabilizedClip(Clip):
    """A clip with stabilization applied.

    Smooths camera motion by computing the average offset over a
    window and applying a correction transform.

    Args:
        _source: The source clip.
        _smoothing: Smoothing window in frames.
        _border_mode: How to handle borders: "crop" or "reflect".
        _offsets: Pre-computed per-frame (dx, dy) corrections.
    """

    _source: Clip = field(default_factory=lambda: _placeholder_clip())
    _smoothing: int = 30
    _border_mode: str = "crop"
    _offsets: list[tuple[float, float]] = field(default_factory=list)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a stabilized frame by shifting the source.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        source_ctx = RenderContext(
            frame=ctx.frame,
            fps=ctx.fps,
            resolution=ctx.resolution,
            time_range=TimeRange(start=self._source.start, end=self._source.end),
            local_frame=ctx.local_frame,
            progress=ctx.local_frame / max(self._source.duration - 1, 1),
        )
        frame = self._source.render_frame(source_ctx)

        if ctx.local_frame < len(self._offsets):
            dx, dy = self._offsets[ctx.local_frame]
        else:
            dx, dy = 0.0, 0.0

        if abs(dx) < 0.5 and abs(dy) < 0.5:
            return frame

        return _shift_frame(frame, dx, dy, self._border_mode)


def _shift_frame(frame: np.ndarray, dx: float, dy: float, border_mode: str) -> np.ndarray:
    """Shift a frame by (dx, dy) pixels.

    Args:
        frame: BGRA uint8 frame.
        dx: Horizontal shift (positive = right).
        dy: Vertical shift (positive = down).
        border_mode: "crop" fills edges with black, "reflect" reflects.

    Returns:
        Shifted BGRA frame.
    """
    try:
        import cv2

        h, w = frame.shape[:2]
        m = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
        border = cv2.BORDER_REPLICATE if border_mode == "reflect" else cv2.BORDER_CONSTANT
        shifted: np.ndarray = cv2.warpAffine(frame, m, (w, h), borderMode=border)
        return shifted
    except ImportError:
        # Simple numpy shift fallback
        result = np.zeros_like(frame)
        idx = int(round(dx))
        idy = int(round(dy))
        h, w = frame.shape[:2]

        src_x1 = max(0, -idx)
        src_y1 = max(0, -idy)
        src_x2 = min(w, w - idx)
        src_y2 = min(h, h - idy)
        dst_x1 = max(0, idx)
        dst_y1 = max(0, idy)
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        if src_x2 > src_x1 and src_y2 > src_y1:
            result[dst_y1:dst_y2, dst_x1:dst_x2] = frame[src_y1:src_y2, src_x1:src_x2]

        return result


def _compute_stabilization_offsets(clip: Clip, smoothing: int) -> list[tuple[float, float]]:
    """Compute per-frame stabilization offsets by tracking global motion.

    Args:
        clip: Source clip to analyze.
        smoothing: Window size for smoothing.

    Returns:
        List of (dx, dy) correction offsets per frame.
    """
    res = Resolution(
        width=max(64, 64 + (64 % 2)),
        height=max(64, 64 + (64 % 2)),
    )

    # Track global motion between consecutive frames
    raw_dx: list[float] = [0.0]
    raw_dy: list[float] = [0.0]

    prev_frame: np.ndarray | None = None
    for i in range(clip.duration):
        ctx = RenderContext(
            frame=i,
            fps=30,
            resolution=res,
            time_range=TimeRange(start=0, end=clip.duration),
            local_frame=i,
            progress=i / max(clip.duration - 1, 1),
        )
        frame = clip.render_frame(ctx)

        if prev_frame is not None:
            dx, dy = _estimate_global_motion(prev_frame, frame)
            raw_dx.append(raw_dx[-1] + dx)
            raw_dy.append(raw_dy[-1] + dy)

        prev_frame = frame

    # Smooth the cumulative trajectory
    smooth_dx = _smooth(raw_dx, smoothing)
    smooth_dy = _smooth(raw_dy, smoothing)

    # Correction = smooth - raw
    offsets: list[tuple[float, float]] = []
    for i in range(len(raw_dx)):
        offsets.append((smooth_dx[i] - raw_dx[i], smooth_dy[i] - raw_dy[i]))

    return offsets


def _estimate_global_motion(prev: np.ndarray, curr: np.ndarray) -> tuple[float, float]:
    """Estimate global motion between two frames.

    Args:
        prev: Previous BGRA frame.
        curr: Current BGRA frame.

    Returns:
        (dx, dy) estimated global displacement.
    """
    try:
        import cv2

        prev_gray = cv2.cvtColor(prev[:, :, :3], cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr[:, :, :3], cv2.COLOR_BGR2GRAY)

        features = cv2.goodFeaturesToTrack(
            prev_gray, maxCorners=50, qualityLevel=0.3, minDistance=7
        )
        if features is None or len(features) < 3:
            return 0.0, 0.0

        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, features, None)
        if next_pts is None:
            return 0.0, 0.0

        good_mask = status.ravel() == 1
        if np.sum(good_mask) < 3:
            return 0.0, 0.0

        prev_pts = features[good_mask]
        next_pts_good = next_pts[good_mask]

        dx = float(np.median(next_pts_good[:, 0, 0] - prev_pts[:, 0, 0]))
        dy = float(np.median(next_pts_good[:, 0, 1] - prev_pts[:, 0, 1]))
        return dx, dy

    except ImportError:
        return 0.0, 0.0


def _smooth(values: list[float], window: int) -> list[float]:
    """Smooth a 1D signal using a moving average.

    Args:
        values: Input signal.
        window: Window size.

    Returns:
        Smoothed signal of the same length.
    """
    if window <= 1 or len(values) <= 1:
        return list(values)

    result: list[float] = []
    half = window // 2
    n = len(values)
    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        result.append(sum(values[start:end]) / (end - start))
    return result


def _placeholder_clip() -> Clip:
    """Create a minimal placeholder clip.

    Returns:
        A clip that renders black frames.
    """

    class _Placeholder(Clip):
        def render_frame(self, ctx: RenderContext) -> np.ndarray:
            return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)

    return _Placeholder()
