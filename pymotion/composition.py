"""Composition and Track — the root objects for video generation.

A Composition is the root object that owns the resolution, fps, duration,
and all tracks. Tracks hold clips in z-order (last added = top).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pymotion.clip.base import BlendMode, Clip, RenderContext, Resolution, TimeRange
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset
from pymotion.render.compositor import composite_layers
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


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

        # Composite all layers
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
