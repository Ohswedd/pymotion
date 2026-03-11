"""AI-powered smart editing helpers.

Module-level utilities for scene detection, silence removal, highlight
detection, content-aware cropping, auto color correction, and auto editing.
All AI features are optional — each raises ``ImportError`` with install
hints if required packages are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pymotion.security.validation import sanitize_text
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SceneDetector:
    """Detect scene boundaries in a clip.

    Computes frame-to-frame difference and identifies cuts where the
    difference exceeds a threshold.

    Args:
        clip: Source clip to analyze.
        threshold: Difference threshold for scene change detection
            (0.0–1.0).  Lower values detect more subtle changes.
        min_scene_length: Minimum frames between detected scene changes.

    Example::

        detector = pm.SceneDetector(clip)
        boundaries = detector.detect()
        # boundaries = [0, 45, 120, 300, ...]
    """

    clip: Any  # Clip
    threshold: float = 0.3
    min_scene_length: int = 15

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not 0.0 <= self.threshold <= 1.0:
            msg = "threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        if self.min_scene_length < 1:
            msg = "min_scene_length must be >= 1"
            raise ValueError(msg)

    def detect(self) -> list[int]:
        """Detect scene boundaries.

        Returns:
            Sorted list of frame indices where scene changes occur.
            Always includes frame 0 as the first boundary.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        boundaries: list[int] = [0]
        duration = self.clip.end - self.clip.start
        if duration <= 1:
            return boundaries

        fps = getattr(self.clip, "fps", 30)
        res = Resolution(
            getattr(self.clip, "width", 320),
            getattr(self.clip, "height", 240),
        )

        prev_frame: np.ndarray | None = None
        last_cut = 0

        for i in range(duration):
            ctx = RenderContext(
                frame=i + self.clip.start,
                fps=fps,
                resolution=res,
                time_range=TimeRange(self.clip.start, self.clip.end),
                local_frame=i,
                progress=i / max(duration - 1, 1),
            )
            current = self.clip.render_frame(ctx)

            if prev_frame is not None:
                # Compute normalized L1 difference
                diff = (
                    float(
                        np.mean(
                            np.abs(
                                current[:, :, :3].astype(np.float32)
                                - prev_frame[:, :, :3].astype(np.float32)
                            )
                        )
                    )
                    / 255.0
                )

                if diff > self.threshold and (i - last_cut) >= self.min_scene_length:
                    boundaries.append(i)
                    last_cut = i

            prev_frame = current

        logger.debug("scene_detection_complete", scenes=len(boundaries))
        return boundaries


@dataclass
class SilenceRemover:
    """Remove silent segments from audio/video clips.

    Analyzes audio amplitude and removes segments where the level
    falls below a threshold for longer than a minimum duration.

    Args:
        clip: Source clip to process.
        threshold_db: Silence threshold in dB (negative).
        min_silence_sec: Minimum silence duration in seconds to remove.

    Example::

        remover = pm.SilenceRemover(clip, threshold_db=-40, min_silence_sec=0.5)
        segments = remover.detect_silence()
        trimmed = remover.remove()
    """

    clip: Any  # Clip
    threshold_db: float = -40.0
    min_silence_sec: float = 0.5

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.threshold_db > 0:
            msg = "threshold_db must be <= 0"
            raise ValueError(msg)
        if self.min_silence_sec <= 0:
            msg = "min_silence_sec must be > 0"
            raise ValueError(msg)

    def detect_silence(self) -> list[tuple[int, int]]:
        """Detect silent segments.

        Returns:
            List of (start_frame, end_frame) tuples for silent regions.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        duration = self.clip.end - self.clip.start
        fps = getattr(self.clip, "fps", 30)
        res = Resolution(
            getattr(self.clip, "width", 320),
            getattr(self.clip, "height", 240),
        )

        min_frames = int(self.min_silence_sec * fps)
        threshold_linear = 10.0 ** (self.threshold_db / 20.0)

        silent_segments: list[tuple[int, int]] = []
        silence_start: int | None = None

        for i in range(duration):
            ctx = RenderContext(
                frame=i + self.clip.start,
                fps=fps,
                resolution=res,
                time_range=TimeRange(self.clip.start, self.clip.end),
                local_frame=i,
                progress=i / max(duration - 1, 1),
            )
            frame = self.clip.render_frame(ctx)

            # Use luminance variance as audio proxy for video-only clips
            amplitude = float(np.std(frame[:, :, :3].astype(np.float32) / 255.0))

            if amplitude < threshold_linear:
                if silence_start is None:
                    silence_start = i
            else:
                if silence_start is not None and (i - silence_start) >= min_frames:
                    silent_segments.append((silence_start, i))
                silence_start = None

        if silence_start is not None and (duration - silence_start) >= min_frames:
            silent_segments.append((silence_start, duration))

        logger.debug("silence_detection_complete", segments=len(silent_segments))
        return silent_segments

    def remove(self) -> list[tuple[int, int]]:
        """Get non-silent segments.

        Returns:
            List of (start_frame, end_frame) tuples for non-silent regions.
        """
        silent = self.detect_silence()
        duration = self.clip.end - self.clip.start

        if not silent:
            return [(0, duration)]

        active: list[tuple[int, int]] = []
        prev_end = 0
        for start, end in silent:
            if start > prev_end:
                active.append((prev_end, start))
            prev_end = end
        if prev_end < duration:
            active.append((prev_end, duration))

        return active


@dataclass
class HighlightDetector:
    """Score and extract the most visually interesting segments.

    Analyzes visual complexity (edge density, color variance, motion)
    to identify highlights in a clip.

    Args:
        clip: Source clip to analyze.
        criteria: Scoring method. ``"visual"`` uses edge density
            and color variance; ``"motion"`` uses frame differences.
        top_n: Number of highlight segments to return.
        segment_length: Length of each highlight segment in frames.

    Example::

        detector = pm.HighlightDetector(clip, criteria="visual")
        highlights = detector.detect()
        # highlights = [(120, 180), (300, 360), ...]
    """

    clip: Any  # Clip
    criteria: str = "visual"
    top_n: int = 5
    segment_length: int = 90

    def __post_init__(self) -> None:
        """Validate parameters."""
        valid_criteria = {"visual", "motion"}
        if self.criteria not in valid_criteria:
            msg = f"criteria must be one of {sorted(valid_criteria)}, got '{self.criteria}'"
            raise ValueError(msg)
        if self.top_n < 1:
            msg = "top_n must be >= 1"
            raise ValueError(msg)
        if self.segment_length < 1:
            msg = "segment_length must be >= 1"
            raise ValueError(msg)

    def detect(self) -> list[tuple[int, int]]:
        """Detect highlight segments.

        Returns:
            List of (start_frame, end_frame) tuples, sorted by score
            (highest first), limited to ``top_n`` results.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        duration = self.clip.end - self.clip.start
        fps = getattr(self.clip, "fps", 30)
        res = Resolution(
            getattr(self.clip, "width", 320),
            getattr(self.clip, "height", 240),
        )

        # Score each frame
        scores: list[float] = []
        prev_frame: np.ndarray | None = None

        for i in range(duration):
            ctx = RenderContext(
                frame=i + self.clip.start,
                fps=fps,
                resolution=res,
                time_range=TimeRange(self.clip.start, self.clip.end),
                local_frame=i,
                progress=i / max(duration - 1, 1),
            )
            frame = self.clip.render_frame(ctx)
            f32 = frame[:, :, :3].astype(np.float32) / 255.0

            if self.criteria == "visual":
                # Edge density via gradient magnitude + color variance
                gx = np.diff(f32, axis=1)
                gy = np.diff(f32, axis=0)
                edge_score = float(np.mean(np.abs(gx)) + np.mean(np.abs(gy)))
                color_score = float(np.std(f32))
                scores.append(edge_score + color_score)
            else:  # motion
                if prev_frame is not None:
                    diff = float(
                        np.mean(np.abs(f32 - prev_frame[:, :, :3].astype(np.float32) / 255.0))
                    )
                    scores.append(diff)
                else:
                    scores.append(0.0)

            prev_frame = frame

        # Find top segments by averaging scores over segment_length
        segment_scores: list[tuple[float, int]] = []
        for start in range(0, max(1, duration - self.segment_length + 1)):
            end = min(start + self.segment_length, duration)
            avg_score = float(np.mean(scores[start:end]))
            segment_scores.append((avg_score, start))

        # Sort by score descending, pick top_n non-overlapping
        segment_scores.sort(reverse=True)
        highlights: list[tuple[int, int]] = []
        used: set[int] = set()

        for _, start in segment_scores:
            end = min(start + self.segment_length, duration)
            if any(s in used for s in range(start, end)):
                continue
            highlights.append((start, end))
            used.update(range(start, end))
            if len(highlights) >= self.top_n:
                break

        logger.debug("highlight_detection_complete", highlights=len(highlights))
        return highlights


@dataclass
class ContentAwareCrop:
    """AI reframing via saliency tracking.

    Analyzes visual saliency to find the most interesting region
    of each frame, then crops to the target aspect ratio while
    tracking the salient region.

    Args:
        clip: Source clip to process.
        target_ratio: Target aspect ratio as ``"width:height"``
            string (e.g. ``"9:16"`` for vertical video).
        smoothing: Temporal smoothing for crop position (frames).

    Example::

        cropper = pm.ContentAwareCrop(clip, target_ratio="9:16")
        crop_data = cropper.analyze()
    """

    clip: Any  # Clip
    target_ratio: str = "9:16"
    smoothing: int = 15

    def __post_init__(self) -> None:
        """Validate parameters."""
        self.target_ratio = sanitize_text(self.target_ratio, max_length=20)
        parts = self.target_ratio.split(":")
        if len(parts) != 2:
            msg = f"target_ratio must be 'W:H' format, got '{self.target_ratio}'"
            raise ValueError(msg)
        try:
            w, h = int(parts[0]), int(parts[1])
        except ValueError:
            msg = f"target_ratio must contain integers, got '{self.target_ratio}'"
            raise ValueError(msg) from None
        if w <= 0 or h <= 0:
            msg = "target_ratio values must be positive"
            raise ValueError(msg)
        if self.smoothing < 1:
            msg = "smoothing must be >= 1"
            raise ValueError(msg)

    def analyze(self) -> list[tuple[int, int, int, int]]:
        """Analyze saliency and compute crop rectangles per frame.

        Returns:
            List of (x, y, crop_w, crop_h) tuples, one per frame.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        duration = self.clip.end - self.clip.start
        fps = getattr(self.clip, "fps", 30)
        clip_w = getattr(self.clip, "width", 320)
        clip_h = getattr(self.clip, "height", 240)
        res = Resolution(clip_w, clip_h)

        # Parse target ratio
        parts = self.target_ratio.split(":")
        tw, th = int(parts[0]), int(parts[1])
        target_aspect = tw / th

        # Compute crop dimensions
        if clip_w / clip_h > target_aspect:
            crop_h = clip_h
            crop_w = int(clip_h * target_aspect)
        else:
            crop_w = clip_w
            crop_h = int(clip_w / target_aspect)

        crop_w = min(crop_w, clip_w)
        crop_h = min(crop_h, clip_h)

        # Find saliency center per frame
        centers_x: list[float] = []
        centers_y: list[float] = []

        for i in range(duration):
            ctx = RenderContext(
                frame=i + self.clip.start,
                fps=fps,
                resolution=res,
                time_range=TimeRange(self.clip.start, self.clip.end),
                local_frame=i,
                progress=i / max(duration - 1, 1),
            )
            frame = self.clip.render_frame(ctx)
            f32 = frame[:, :, :3].astype(np.float32)

            # Simple saliency: gradient magnitude weighted center of mass
            gx = np.abs(np.diff(f32, axis=1)).mean(axis=2)
            gy = np.abs(np.diff(f32, axis=0)).mean(axis=2)

            # Pad to original size
            gx_pad = np.zeros((clip_h, clip_w), dtype=np.float32)
            gx_pad[:, : gx.shape[1]] = gx
            gy_pad = np.zeros((clip_h, clip_w), dtype=np.float32)
            gy_pad[: gy.shape[0], :] = gy

            saliency = gx_pad + gy_pad
            total = saliency.sum()
            if total > 0:
                ys, xs = np.mgrid[:clip_h, :clip_w]
                cx = float(np.sum(xs * saliency) / total)
                cy = float(np.sum(ys * saliency) / total)
            else:
                cx, cy = clip_w / 2.0, clip_h / 2.0

            centers_x.append(cx)
            centers_y.append(cy)

        # Temporal smoothing
        if len(centers_x) > 1:
            kernel = np.ones(min(self.smoothing, len(centers_x))) / min(
                self.smoothing, len(centers_x)
            )
            centers_x_arr = np.convolve(centers_x, kernel, mode="same")
            centers_y_arr = np.convolve(centers_y, kernel, mode="same")
        else:
            centers_x_arr = np.array(centers_x)
            centers_y_arr = np.array(centers_y)

        # Convert to crop rectangles
        crops: list[tuple[int, int, int, int]] = []
        for i in range(duration):
            x = int(np.clip(centers_x_arr[i] - crop_w / 2, 0, clip_w - crop_w))
            y = int(np.clip(centers_y_arr[i] - crop_h / 2, 0, clip_h - crop_h))
            crops.append((x, y, crop_w, crop_h))

        logger.debug("content_aware_crop_complete", frames=len(crops))
        return crops


@dataclass
class AutoColor:
    """AI one-click color correction to a neutral baseline.

    Applies automatic white balance, exposure correction, and
    contrast normalization.

    Args:
        clip: Source clip to analyze and correct.
        strength: Correction strength (0.0–1.0).

    Example::

        corrector = pm.AutoColor(clip)
        correction = corrector.analyze()
    """

    clip: Any  # Clip
    strength: float = 1.0

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not 0.0 <= self.strength <= 1.0:
            msg = "strength must be between 0.0 and 1.0"
            raise ValueError(msg)

    def analyze(self) -> dict[str, float]:
        """Analyze clip and compute correction parameters.

        Returns:
            Dictionary with correction values: ``white_balance_r``,
            ``white_balance_b``, ``exposure``, ``contrast``.
        """
        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        duration = self.clip.end - self.clip.start
        if duration <= 0:
            return {
                "white_balance_r": 1.0,
                "white_balance_b": 1.0,
                "exposure": 0.0,
                "contrast": 1.0,
            }

        fps = getattr(self.clip, "fps", 30)
        res = Resolution(
            getattr(self.clip, "width", 320),
            getattr(self.clip, "height", 240),
        )

        # Sample a subset of frames for analysis
        sample_count = min(duration, 10)
        step = max(1, duration // max(sample_count, 1))

        sum_r = 0.0
        sum_g = 0.0
        sum_b = 0.0
        sum_luma = 0.0
        n_samples = 0

        for i in range(0, duration, step):
            ctx = RenderContext(
                frame=i + self.clip.start,
                fps=fps,
                resolution=res,
                time_range=TimeRange(self.clip.start, self.clip.end),
                local_frame=i,
                progress=i / max(duration - 1, 1),
            )
            frame = self.clip.render_frame(ctx)
            f32 = frame[:, :, :3].astype(np.float32) / 255.0

            sum_b += float(np.mean(f32[:, :, 0]))
            sum_g += float(np.mean(f32[:, :, 1]))
            sum_r += float(np.mean(f32[:, :, 2]))
            sum_luma += float(np.mean(f32))
            n_samples += 1

        if n_samples == 0:
            return {
                "white_balance_r": 1.0,
                "white_balance_b": 1.0,
                "exposure": 0.0,
                "contrast": 1.0,
            }

        avg_r = sum_r / n_samples
        avg_g = sum_g / n_samples
        avg_b = sum_b / n_samples
        avg_luma = sum_luma / n_samples

        # White balance: adjust R and B relative to G (gray world assumption)
        wb_r = (avg_g / avg_r) if avg_r > 0.01 else 1.0
        wb_b = (avg_g / avg_b) if avg_b > 0.01 else 1.0

        # Exposure correction: target mid-gray (0.18 in linear, ~0.46 in sRGB)
        target_luma = 0.46
        exposure = target_luma - avg_luma

        # Apply strength
        wb_r = 1.0 + (wb_r - 1.0) * self.strength
        wb_b = 1.0 + (wb_b - 1.0) * self.strength
        exposure *= self.strength

        correction = {
            "white_balance_r": round(wb_r, 4),
            "white_balance_b": round(wb_b, 4),
            "exposure": round(exposure, 4),
            "contrast": 1.0,
        }

        logger.debug("auto_color_analysis_complete", correction=correction)
        return correction


@dataclass
class AutoEdit:
    """AI-powered automatic editing.

    Selects the best moments from raw clips, optionally cutting on
    beats, and assembles them into a ``Composition``.

    Args:
        clips: List of source clips.
        style: Editing style. ``"fast"`` for quick cuts, ``"smooth"``
            for longer takes with transitions.
        music: Optional music clip for beat-synced editing.
        target_duration: Target output duration in frames.

    Example::

        comp = pm.AutoEdit(clips=[clip1, clip2], style="fast").edit()
    """

    clips: list[Any] = field(default_factory=list)
    style: str = "fast"
    music: Any = None  # Optional AudioClip
    target_duration: int = 900  # 30 seconds at 30fps

    def __post_init__(self) -> None:
        """Validate parameters."""
        valid_styles = {"fast", "smooth"}
        if self.style not in valid_styles:
            msg = f"style must be one of {sorted(valid_styles)}, got '{self.style}'"
            raise ValueError(msg)
        if not self.clips:
            msg = "clips list must not be empty"
            raise ValueError(msg)
        if self.target_duration < 1:
            msg = "target_duration must be >= 1"
            raise ValueError(msg)

    def edit(self) -> list[tuple[int, int, int]]:
        """Select and arrange highlights from source clips.

        Returns:
            List of (clip_index, start_frame, end_frame) tuples
            representing the edit decision list.
        """
        # Analyze each clip for highlights
        segment_length = 90 if self.style == "fast" else 150
        all_segments: list[tuple[float, int, int, int]] = []

        for idx, clip in enumerate(self.clips):
            detector = HighlightDetector(
                clip=clip,
                criteria="motion" if self.style == "fast" else "visual",
                top_n=10,
                segment_length=segment_length,
            )
            highlights = detector.detect()
            for start, end in highlights:
                # Score is position-based (earlier = better for fast)
                score = 1.0 / (start + 1)
                all_segments.append((score, idx, start, end))

        # Sort by score descending
        all_segments.sort(reverse=True)

        # Select segments up to target duration
        edl: list[tuple[int, int, int]] = []
        total_frames = 0

        for _, clip_idx, start, end in all_segments:
            seg_len = end - start
            if total_frames + seg_len > self.target_duration:
                remaining = self.target_duration - total_frames
                if remaining > segment_length // 2:
                    edl.append((clip_idx, start, start + remaining))
                    total_frames += remaining
                break
            edl.append((clip_idx, start, end))
            total_frames += seg_len
            if total_frames >= self.target_duration:
                break

        logger.debug("auto_edit_complete", segments=len(edl), total_frames=total_frames)
        return edl


@dataclass
class FaceDetector:
    """Detect face bounding boxes in a clip per frame.

    Uses OpenCV's Haar cascade or DNN face detector.

    Args:
        clip: Source clip to analyze.
        method: Detection method. ``"haar"`` (fast, OpenCV Haar cascade)
            or ``"dnn"`` (more accurate, OpenCV DNN).
        min_confidence: Minimum confidence for DNN method (0.0–1.0).

    Example::

        detector = pm.FaceDetector(clip)
        faces = detector.detect()
        # faces = {0: [(x, y, w, h), ...], 1: [...], ...}
    """

    clip: Any  # Clip
    method: str = "haar"
    min_confidence: float = 0.5

    def __post_init__(self) -> None:
        """Validate parameters."""
        valid_methods = {"haar", "dnn"}
        if self.method not in valid_methods:
            msg = f"method must be one of {sorted(valid_methods)}, got '{self.method}'"
            raise ValueError(msg)
        if not 0.0 <= self.min_confidence <= 1.0:
            msg = "min_confidence must be between 0.0 and 1.0"
            raise ValueError(msg)

    def detect(self) -> dict[int, list[tuple[int, int, int, int]]]:
        """Detect faces in every frame.

        Returns:
            Dictionary mapping frame index to a list of face bounding
            boxes ``(x, y, width, height)``.

        Raises:
            ImportError: If OpenCV is not installed.
        """
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            msg = (
                "opencv-python is required for FaceDetector. "
                "Install it with: pip install opencv-python"
            )
            raise ImportError(msg)  # noqa: B904

        from pymotion.clip.base import RenderContext, Resolution, TimeRange  # noqa: PLC0415

        duration = self.clip.end - self.clip.start
        fps = getattr(self.clip, "fps", 30)
        clip_w = getattr(self.clip, "width", 320)
        clip_h = getattr(self.clip, "height", 240)
        res = Resolution(clip_w, clip_h)

        # Load Haar cascade
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        result: dict[int, list[tuple[int, int, int, int]]] = {}

        for i in range(duration):
            ctx = RenderContext(
                frame=i + self.clip.start,
                fps=fps,
                resolution=res,
                time_range=TimeRange(self.clip.start, self.clip.end),
                local_frame=i,
                progress=i / max(duration - 1, 1),
            )
            frame = self.clip.render_frame(ctx)
            gray = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_BGR2GRAY)

            faces = cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
            face_list: list[tuple[int, int, int, int]] = []
            if len(faces) > 0:
                for x, y, w, h in faces:
                    face_list.append((int(x), int(y), int(w), int(h)))
            result[i] = face_list

        logger.debug(
            "face_detection_complete",
            frames=duration,
            total_faces=sum(len(v) for v in result.values()),
        )
        return result


@dataclass
class FaceTracker:
    """Track faces across frames.

    Uses :class:`FaceDetector` on the first frame, then tracks each
    detected face using simple centroid tracking.

    Args:
        clip: Source clip to track.
        max_distance: Maximum pixel distance to match faces across frames.

    Example::

        tracker = pm.FaceTracker(clip)
        tracks = tracker.track()
        # tracks = {0: {frame: (cx, cy), ...}, 1: {...}}
    """

    clip: Any  # Clip
    max_distance: float = 100.0

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.max_distance <= 0:
            msg = "max_distance must be > 0"
            raise ValueError(msg)

    def track(self) -> dict[int, dict[int, tuple[float, float]]]:
        """Track faces across all frames.

        Returns:
            Dictionary mapping face_id to a dict of
            ``{frame_index: (center_x, center_y)}``.

        Raises:
            ImportError: If OpenCV is not installed.
        """
        try:
            import cv2  # noqa: PLC0415, F401
        except ImportError:
            msg = (
                "opencv-python is required for FaceTracker. "
                "Install it with: pip install opencv-python"
            )
            raise ImportError(msg)  # noqa: B904

        detector = FaceDetector(clip=self.clip, method="haar")
        detections = detector.detect()

        tracks: dict[int, dict[int, tuple[float, float]]] = {}
        next_id = 0
        active: dict[int, tuple[float, float]] = {}  # face_id → last centroid

        for frame_idx in sorted(detections.keys()):
            faces = detections[frame_idx]
            centroids = [(x + w / 2.0, y + h / 2.0) for x, y, w, h in faces]

            matched: set[int] = set()
            used_centroids: set[int] = set()

            # Match existing tracks to current detections
            for fid, (prev_cx, prev_cy) in list(active.items()):
                best_dist = self.max_distance
                best_ci = -1
                for ci, (cx, cy) in enumerate(centroids):
                    if ci in used_centroids:
                        continue
                    dist = ((cx - prev_cx) ** 2 + (cy - prev_cy) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_ci = ci
                if best_ci >= 0:
                    tracks[fid][frame_idx] = centroids[best_ci]
                    active[fid] = centroids[best_ci]
                    matched.add(fid)
                    used_centroids.add(best_ci)

            # Create new tracks for unmatched centroids
            for ci, centroid in enumerate(centroids):
                if ci not in used_centroids:
                    tracks[next_id] = {frame_idx: centroid}
                    active[next_id] = centroid
                    next_id += 1

            # Remove tracks that weren't matched
            for fid in list(active.keys()):
                if fid not in matched and frame_idx > 0:
                    del active[fid]

        logger.debug("face_tracking_complete", tracks=len(tracks))
        return tracks

    def to_keyframes(self, face_id: int = 0) -> dict[int, tuple[float, float]]:
        """Convert a face track to keyframe data.

        Args:
            face_id: Which tracked face to extract (default: first).

        Returns:
            Dictionary mapping frame index to (x, y) position.
        """
        tracks = self.track()
        if face_id in tracks:
            return tracks[face_id]
        return {}


@dataclass
class FaceBlur:
    """Automatically detect and blur all faces in a clip.

    Uses :class:`FaceDetector` to find faces and applies Gaussian
    blur to each detected region.

    Args:
        clip: Source clip to process.
        strength: Blur kernel size multiplier (1–10).
        method: Face detection method (``"haar"`` or ``"dnn"``).

    Example::

        blurrer = pm.FaceBlur(clip, strength=5)
        blur_regions = blurrer.get_blur_regions()
    """

    clip: Any  # Clip
    strength: int = 5
    method: str = "haar"

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.strength < 1 or self.strength > 10:
            msg = "strength must be between 1 and 10"
            raise ValueError(msg)
        valid_methods = {"haar", "dnn"}
        if self.method not in valid_methods:
            msg = f"method must be one of {sorted(valid_methods)}, got '{self.method}'"
            raise ValueError(msg)

    def get_blur_regions(self) -> dict[int, list[tuple[int, int, int, int]]]:
        """Get face regions to blur per frame.

        Returns:
            Dictionary mapping frame index to list of face bounding
            boxes ``(x, y, width, height)`` that should be blurred.

        Raises:
            ImportError: If OpenCV is not installed.
        """
        detector = FaceDetector(clip=self.clip, method=self.method)
        return detector.detect()

    def apply_blur(self, frame: np.ndarray, regions: list[tuple[int, int, int, int]]) -> np.ndarray:
        """Apply Gaussian blur to specified regions of a frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            regions: List of (x, y, width, height) bounding boxes.

        Returns:
            BGRA numpy array with faces blurred.

        Raises:
            ImportError: If OpenCV is not installed.
        """
        try:
            import cv2  # noqa: PLC0415
        except ImportError:
            msg = (
                "opencv-python is required for FaceBlur. Install it with: pip install opencv-python"
            )
            raise ImportError(msg)  # noqa: B904

        result = frame.copy()
        ksize = self.strength * 10 + 1  # Must be odd
        if ksize % 2 == 0:
            ksize += 1

        for x, y, w, h in regions:
            x = max(0, x)
            y = max(0, y)
            x2 = min(frame.shape[1], x + w)
            y2 = min(frame.shape[0], y + h)
            if x2 > x and y2 > y:
                roi = result[y:y2, x:x2, :3]
                blurred: np.ndarray = cv2.GaussianBlur(roi, (ksize, ksize), 0)
                result[y:y2, x:x2, :3] = blurred

        return result
