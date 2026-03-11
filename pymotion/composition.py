"""Composition, Track, and CompositionClip — the root objects for video generation.

A Composition is the root object that owns the resolution, fps, duration,
and all tracks. Tracks hold clips in z-order (last added = top).

CompositionClip wraps a Composition as a Clip so it can be nested inside
another Composition (up to 10 levels deep).
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pymotion.clip.base import BlendMode, Clip, RenderContext, Resolution, TimeRange
from pymotion.effects.base import Effect
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset
from pymotion.render.compositor import composite_layers
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

_MAX_NESTING_DEPTH = 10

_DEFAULT_CACHE_MAX_FRAMES = 256


@dataclass
class Track:
    """A named sequence of clips composited in z-order.

    Args:
        name: Track name.
        clips: List of clips on this track.
        visible: Whether the track is rendered.
        opacity: Track-level opacity (0.0-1.0).
        blend_mode: Blending mode for this track.
    """

    name: str = "default"
    clips: list[Clip] = field(default_factory=list)
    visible: bool = True
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL

    def add(self, *clips: Clip) -> Track:
        """Add clips to this track.

        Args:
            *clips: One or more clips to add.

        Returns:
            Self for method chaining.
        """
        self.clips.extend(clips)
        return self


class _NestedFrameCache:
    """Thread-safe LRU cache for rendered frames shared across nesting levels.

    Frames are keyed by ``(composition_id, frame_index)`` and evicted in
    LRU order when the cache exceeds ``max_frames``.

    Args:
        max_frames: Maximum number of frames to keep in cache.
    """

    def __init__(self, max_frames: int = _DEFAULT_CACHE_MAX_FRAMES) -> None:
        self._max_frames = max_frames
        self._cache: OrderedDict[tuple[int, int], np.ndarray] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, comp_id: int, frame: int) -> np.ndarray | None:
        """Retrieve a cached frame, or ``None`` if not present.

        Args:
            comp_id: The ``id()`` of the Composition.
            frame: Frame index.

        Returns:
            Cached BGRA frame or None.
        """
        key = (comp_id, frame)
        with self._lock:
            val = self._cache.get(key)
            if val is not None:
                self._cache.move_to_end(key)
                return val.copy()
            return None

    def put(self, comp_id: int, frame: int, data: np.ndarray) -> None:
        """Store a rendered frame in the cache.

        Args:
            comp_id: The ``id()`` of the Composition.
            frame: Frame index.
            data: BGRA numpy array.
        """
        key = (comp_id, frame)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = data.copy()
            else:
                self._cache[key] = data.copy()
                if len(self._cache) > self._max_frames:
                    self._cache.popitem(last=False)

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        """Number of frames currently cached."""
        with self._lock:
            return len(self._cache)


# Module-level shared cache instance
_shared_frame_cache = _NestedFrameCache()


def get_shared_frame_cache() -> _NestedFrameCache:
    """Return the module-level shared frame cache for nested compositions.

    Returns:
        The shared ``_NestedFrameCache`` instance.
    """
    return _shared_frame_cache


class Composition:
    """Root object for a video composition.

    Owns the resolution, fps, duration, background color, and all tracks.
    Provides render() to produce the final video output.

    Args:
        width: Frame width in pixels.
        height: Frame height in pixels.
        fps: Frames per second.
        duration: Total duration in frames.
        background: Background color.
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        duration: int = 90,
        background: ColorInput = "#000000",
    ) -> None:
        """Initialize a Composition.

        Args:
            width: Frame width in pixels (must be even).
            height: Frame height in pixels (must be even).
            fps: Frames per second (24, 25, 30, 48, or 60).
            duration: Total duration in frames.
            background: Background color in any supported format.
        """
        self.resolution = Resolution(width=width, height=height)
        self.fps = fps
        self.duration = duration
        self.background = Color.parse(background)
        self.tracks: list[Track] = []
        self._default_track: Track = Track(name="default")
        self.tracks.append(self._default_track)
        self._bg_frame: np.ndarray | None = None

    def add(self, *clips: Clip) -> Composition:
        """Add clips to the default track.

        Args:
            *clips: One or more clips to add.

        Returns:
            Self for method chaining.
        """
        self._default_track.add(*clips)
        return self

    def add_track(self, track: Track) -> Composition:
        """Add a named track to the composition.

        Args:
            track: The track to add.

        Returns:
            Self for method chaining.
        """
        self.tracks.append(track)
        return self

    def _get_bg_frame(self) -> np.ndarray:
        """Get the pre-computed background frame (cached).

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        if self._bg_frame is not None:
            return self._bg_frame

        w = self.resolution.width
        h = self.resolution.height
        bg = np.zeros((h, w, 4), dtype=np.uint8)
        b_val, g_val, r_val, a_val = self.background.to_bgra_uint8()
        bg[:, :, 0] = b_val
        bg[:, :, 1] = g_val
        bg[:, :, 2] = r_val
        bg[:, :, 3] = a_val
        self._bg_frame = bg
        return bg

    def _render_frame(self, frame: int) -> np.ndarray:
        """Render a single frame of the composition.

        When an :class:`AdjustmentLayer` is encountered, all layers
        collected so far are composited onto the background, the
        adjustment layer's effects are applied to the flattened result,
        and compositing continues with the adjusted frame as the new base.

        Args:
            frame: Frame number to render.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        bg = self._get_bg_frame().copy()
        layers: list[tuple[np.ndarray, BlendMode, float]] = []

        for track in self.tracks:
            if not track.visible or track.opacity <= 0.0:
                continue
            for clip in track.clips:
                if clip.start <= frame < clip.end:
                    local_frame = frame - clip.start
                    clip_duration = clip.end - clip.start
                    progress = local_frame / max(clip_duration - 1, 1)

                    ctx = RenderContext(
                        frame=frame,
                        fps=self.fps,
                        resolution=self.resolution,
                        time_range=TimeRange(start=clip.start, end=clip.end),
                        local_frame=local_frame,
                        progress=progress,
                    )

                    if isinstance(clip, AdjustmentLayer):
                        # Flatten everything below, apply adjustment effects
                        bg = composite_layers(bg, layers)
                        layers = []
                        bg = clip.apply_effects(bg, ctx)
                        continue

                    rendered = clip.render_with_effects(ctx)
                    # Combine clip and track opacity
                    effective_opacity = clip._opacity * track.opacity
                    # Track blend mode overrides clip when non-NORMAL
                    blend = (
                        track.blend_mode
                        if track.blend_mode != BlendMode.NORMAL
                        else clip.blend_mode
                    )
                    layers.append((rendered, blend, effective_opacity))

        # Composite remaining layers
        result = composite_layers(bg, layers)

        return result

    def _frame_iterator(self, start: int = 0, end: int | None = None) -> Iterator[np.ndarray]:
        """Iterate over rendered frames.

        Args:
            start: First frame to render.
            end: Last frame (exclusive). Defaults to composition duration.

        Yields:
            BGRA numpy arrays for each frame.
        """
        if end is None:
            end = self.duration
        for frame in range(start, end):
            yield self._render_frame(frame)

    def render(
        self,
        output: str | Path,
        preset: str = "h264_1080p",
        start: int = 0,
        end: int | None = None,
    ) -> Path:
        """Render the composition to a video file.

        Args:
            output: Output file path.
            preset: Name of the output preset to use.
            start: Start frame (default: 0).
            end: End frame (default: composition duration).

        Returns:
            Path to the rendered output file.
        """
        output_path = Path(output)
        preset_config = get_preset(preset)

        if end is None:
            end = self.duration

        logger.info(
            "render_start",
            output=str(output_path),
            preset=preset,
            frames=end - start,
            resolution=f"{self.resolution.width}x{self.resolution.height}",
            fps=self.fps,
        )

        encoder = FFmpegEncoder()
        result = encoder.encode(
            frame_iter=self._frame_iterator(start, end),
            audio=None,
            output=output_path,
            preset=preset_config,
            width=self.resolution.width,
            height=self.resolution.height,
            fps=self.fps,
        )

        logger.info("render_complete", output=str(result))
        return result

    def export_frame(self, frame: int, output: str | Path) -> Path:
        """Export a single frame as a PNG image.

        Args:
            frame: Frame number to export.
            output: Output file path.

        Returns:
            Path to the exported PNG file.
        """
        from PIL import Image as PILImage

        output_path = Path(output)
        rendered = self._render_frame(frame)

        # Convert BGRA to RGBA for PIL
        rgba = rendered.copy()
        rgba[:, :, 0] = rendered[:, :, 2]  # R <- B
        rgba[:, :, 2] = rendered[:, :, 0]  # B <- R

        img = PILImage.fromarray(rgba)
        img.save(output_path)
        logger.info("frame_exported", frame=frame, output=str(output_path))
        return output_path

    def export_edl(self, path: str | Path) -> None:
        """Export the composition as a CMX 3600 EDL file.

        Only :class:`~pymotion.clip.video.VideoClip` instances produce
        source entries — other clip types are skipped.

        Args:
            path: Destination file path for the EDL.
        """
        from pymotion.clip.video import VideoClip  # noqa: PLC0415

        out = Path(path).resolve()

        lines: list[str] = []
        lines.append(f"TITLE: {out.stem}")
        lines.append(f"FCM: {'NON-DROP FRAME' if self.fps in (24, 25, 30) else 'DROP FRAME'}")
        lines.append("")

        event_num = 1
        for track in self.tracks:
            for clip in track.clips:
                if not isinstance(clip, VideoClip):
                    continue
                src_name = clip.source.stem[:8].upper().ljust(8) if clip.source.name else "AX      "
                rec_in = self._frames_to_tc(clip.start)
                rec_out = self._frames_to_tc(clip.end)
                src_in = self._frames_to_tc(0)
                src_out = self._frames_to_tc(clip.end - clip.start)

                lines.append(
                    f"{event_num:03d}  {src_name} V     C        "
                    f"{src_in} {src_out} {rec_in} {rec_out}"
                )
                if clip.source.name:
                    lines.append(f"* FROM CLIP NAME: {clip.source.name}")
                lines.append("")
                event_num += 1

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        logger.info("edl_exported", path=str(out), events=event_num - 1)

    def export_otio(self, path: str | Path) -> None:
        """Export the composition as an OpenTimelineIO file.

        Requires the ``opentimelineio`` package.

        Args:
            path: Destination file path (typically ``.otio``).

        Raises:
            ImportError: If opentimelineio is not installed.
        """
        try:
            import opentimelineio as otio  # noqa: PLC0415
        except ImportError:
            msg = (
                "opentimelineio is required for OTIO export. "
                "Install it with: pip install opentimelineio"
            )
            raise ImportError(msg)  # noqa: B904

        from pymotion.clip.video import VideoClip  # noqa: PLC0415

        out = Path(path).resolve()

        rate = float(self.fps)
        timeline = otio.schema.Timeline(name=out.stem)

        for track in self.tracks:
            otio_track = otio.schema.Track(name=track.name)
            for clip in track.clips:
                if not isinstance(clip, VideoClip):
                    # Represent non-video clips as gaps
                    gap_dur = clip.end - clip.start
                    if gap_dur > 0:
                        otio_track.append(
                            otio.schema.Gap(
                                source_range=otio.opentime.TimeRange(
                                    start_time=otio.opentime.RationalTime(0, rate),
                                    duration=otio.opentime.RationalTime(gap_dur, rate),
                                )
                            )
                        )
                    continue
                clip_dur = clip.end - clip.start
                media_ref = otio.schema.ExternalReference(
                    target_url=str(clip.source),
                )
                otio_clip = otio.schema.Clip(
                    name=clip.source.stem,
                    source_range=otio.opentime.TimeRange(
                        start_time=otio.opentime.RationalTime(0, rate),
                        duration=otio.opentime.RationalTime(clip_dur, rate),
                    ),
                    media_reference=media_ref,
                )
                otio_track.append(otio_clip)

            timeline.tracks.append(otio_track)

        out.parent.mkdir(parents=True, exist_ok=True)
        otio.adapters.write_to_file(timeline, str(out))
        logger.info("otio_exported", path=str(out))

    def _frames_to_tc(self, frames: int) -> str:
        """Convert a frame count to SMPTE timecode HH:MM:SS:FF.

        Args:
            frames: Frame count.

        Returns:
            Timecode string.
        """
        fps = self.fps
        f = frames % fps
        total_seconds = frames // fps
        s = total_seconds % 60
        m = (total_seconds // 60) % 60
        h = total_seconds // 3600
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    def to_clip(self) -> CompositionClip:
        """Convert this composition to a clip for nesting inside another.

        The returned clip renders this composition's frames on demand.
        Recursive nesting is supported up to 10 levels deep.

        Returns:
            A CompositionClip bound to this composition.

        Raises:
            ValueError: If this composition has zero duration.
        """
        if self.duration <= 0:
            msg = "Cannot convert a composition with zero duration to a clip"
            raise ValueError(msg)

        clip = CompositionClip(
            _composition=self,
        )
        clip.set_duration(self.duration)
        return clip


@dataclass
class AdjustmentLayer(Clip):
    """A layer that applies its effects to all layers below it.

    An AdjustmentLayer does not render visual content of its own.
    Instead, when the compositor encounters it, all layers composited
    so far are flattened and the adjustment layer's effects are applied
    to the result.

    Accepts the same mask and effect interfaces as any other clip.
    All effect parameters are animatable via keyframes through the
    standard :class:`RenderContext` mechanism.

    Args:
        effects: List of effects to apply to layers below.

    Example::

        from pymotion.effects.color import Brightness, Contrast

        adj = AdjustmentLayer(effects=[Brightness(value=0.3), Contrast(value=1.2)])
        adj.set_duration(60)
        comp.add(adj)
    """

    def __init__(self, effects: list[Effect] | None = None) -> None:
        """Initialize an AdjustmentLayer with optional effects.

        Args:
            effects: List of effects to apply to layers below.
        """
        super().__init__()
        if effects:
            for effect in effects:
                self.add_effect(effect)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Return a transparent frame (adjustment layers have no visual content).

        This method is not called during normal composition rendering.
        AdjustmentLayer is handled specially by
        :meth:`Composition._render_frame`.

        Args:
            ctx: The render context for this frame.

        Returns:
            Fully transparent BGRA numpy array.
        """
        return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)

    def apply_effects(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply this layer's effects to a flattened frame.

        Called by the compositor when this adjustment layer is active.
        Applies each effect in sequence, respecting the layer's opacity
        by blending between the original and effected frame.

        Args:
            frame: BGRA numpy array of the composited layers below.
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array with effects applied.
        """
        if not self._effects:
            return frame

        effected = frame.copy()
        for effect in self._effects:
            effected = effect.apply(effected, ctx)

        # Respect adjustment layer opacity: blend original and effected
        if self._opacity < 1.0:
            alpha = self._opacity
            blended = frame.astype(np.float32) * (1.0 - alpha) + effected.astype(np.float32) * alpha
            return np.clip(blended, 0, 255).astype(np.uint8)

        return effected


@dataclass
class CompositionClip(Clip):
    """A clip that renders frames from a nested Composition.

    Supports independent resolution and fps. When the nested
    composition differs from the parent, frames are scaled to fit
    the parent resolution and frame indices are remapped via the
    fps ratio.

    Nesting is recursive up to 10 levels. A shared LRU cache across
    all nesting levels avoids redundant rendering.

    Args:
        _composition: The nested Composition to render.
        _nesting_depth: Current nesting depth (auto-incremented).
        _cache: Shared frame cache across nesting levels.
    """

    _composition: Composition = field(default_factory=lambda: Composition())
    _nesting_depth: int = 0
    _cache: _NestedFrameCache = field(
        default_factory=get_shared_frame_cache,
        repr=False,
    )

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a single frame from the nested composition.

        Handles fps conversion (parent fps → child fps) and resolution
        scaling (child resolution → parent resolution). Uses the shared
        LRU cache to avoid re-rendering identical frames.

        Args:
            ctx: The render context from the parent composition.

        Returns:
            BGRA numpy array matching the parent resolution.

        Raises:
            RecursionError: If nesting depth exceeds 10 levels.
        """
        if self._nesting_depth >= _MAX_NESTING_DEPTH:
            msg = f"Maximum composition nesting depth ({_MAX_NESTING_DEPTH}) exceeded"
            raise RecursionError(msg)

        child = self._composition

        # Map parent local_frame to child frame via fps ratio
        if ctx.fps != child.fps and ctx.fps > 0:
            child_frame = int(ctx.local_frame * child.fps / ctx.fps)
        else:
            child_frame = ctx.local_frame

        # Clamp to child duration
        child_frame = max(0, min(child_frame, child.duration - 1))

        comp_id = id(child)

        # Check cache
        cached = self._cache.get(comp_id, child_frame)
        if cached is not None:
            return self._scale_to_parent(cached, ctx.resolution)

        # Propagate nesting depth to any CompositionClips in child
        self._propagate_depth(child)

        rendered = child._render_frame(child_frame)

        # Cache the rendered frame at native resolution
        self._cache.put(comp_id, child_frame, rendered)

        return self._scale_to_parent(rendered, ctx.resolution)

    def _propagate_depth(self, comp: Composition) -> None:
        """Set nesting depth on all CompositionClips within a composition.

        Args:
            comp: The composition to scan.
        """
        for track in comp.tracks:
            for clip in track.clips:
                if isinstance(clip, CompositionClip):
                    clip._nesting_depth = self._nesting_depth + 1
                    clip._cache = self._cache

    @staticmethod
    def _scale_to_parent(
        frame: np.ndarray,
        parent_res: Resolution,
    ) -> np.ndarray:
        """Scale a rendered frame to the parent composition's resolution.

        Uses area interpolation for downscaling and linear for upscaling
        via OpenCV when available, falling back to nearest-neighbor via
        numpy for simplicity.

        Args:
            frame: Source BGRA frame (H, W, 4).
            parent_res: Target resolution.

        Returns:
            Scaled BGRA numpy array matching parent_res.
        """
        src_h, src_w = frame.shape[:2]
        dst_w, dst_h = parent_res.width, parent_res.height

        if src_w == dst_w and src_h == dst_h:
            return frame

        try:
            import cv2  # noqa: PLC0415

            if dst_w < src_w or dst_h < src_h:
                interp = cv2.INTER_AREA
            else:
                interp = cv2.INTER_LINEAR
            return cv2.resize(frame, (dst_w, dst_h), interpolation=interp)  # type: ignore[no-any-return]
        except ImportError:
            pass

        # Numpy nearest-neighbor fallback
        row_idx = (np.arange(dst_h) * src_h // dst_h).clip(0, src_h - 1)
        col_idx = (np.arange(dst_w) * src_w // dst_w).clip(0, src_w - 1)
        result: np.ndarray = frame[np.ix_(row_idx, col_idx)]
        return result
