"""VideoClip — embed existing video files into a composition.

Uses FFmpeg subprocess for decoding video files. Supports trim, loop,
speed change, and reverse operations.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.security.validation import validate_path
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

# Locate ffmpeg/ffprobe once at import time
_FFMPEG_BIN: str | None = shutil.which("ffmpeg")
_FFPROBE_BIN: str | None = shutil.which("ffprobe")


def _get_ffmpeg() -> str:
    """Get the validated ffmpeg binary path.

    Returns:
        Path to ffmpeg binary.

    Raises:
        RuntimeError: If ffmpeg is not found.
    """
    if _FFMPEG_BIN is None:
        msg = "ffmpeg not found on PATH. Install ffmpeg to use VideoClip."
        raise RuntimeError(msg)
    return _FFMPEG_BIN


def _get_ffprobe() -> str:
    """Get the validated ffprobe binary path.

    Returns:
        Path to ffprobe binary.

    Raises:
        RuntimeError: If ffprobe is not found.
    """
    if _FFPROBE_BIN is None:
        msg = "ffprobe not found on PATH. Install ffmpeg to use VideoClip."
        raise RuntimeError(msg)
    return _FFPROBE_BIN


@dataclass
class VideoClip(Clip):
    """A clip that embeds an existing video file.

    Decodes video frames from a source file using FFmpeg subprocess.
    Supports trimming, looping, speed changes, and reverse playback.

    Args:
        source: Path to the video file.
        trim_start: Start time in seconds for trimming.
        trim_end: End time in seconds for trimming (None = to end).
        _speed_factor: Playback speed multiplier (1.0 = normal).
        reverse: Whether to play in reverse.
        loop: Number of times to loop (-1 = infinite to fill duration).
    """

    source: Path = field(default_factory=lambda: Path(""))
    trim_start: float = 0.0
    trim_end: float | None = None
    _speed_factor: float = 1.0
    _reverse: bool = False
    loop: int = 1
    _source_fps: float = 0.0
    _source_duration: float = 0.0
    _frame_cache: dict[int, np.ndarray] = field(default_factory=dict, repr=False)

    def __init__(
        self,
        source: str | Path,
        *,
        trim_start: float = 0.0,
        trim_end: float | None = None,
        speed_factor: float = 1.0,
        reverse: bool = False,
        loop: int = 1,
        base_dirs: list[Path] | None = None,
    ) -> None:
        """Initialize a VideoClip.

        Args:
            source: Path to the video file.
            trim_start: Start time in seconds for trimming.
            trim_end: End time in seconds for trimming (None = to end).
            speed_factor: Playback speed multiplier.
            reverse: Whether to play in reverse.
            loop: Number of times to loop (-1 = infinite).
            base_dirs: Allowed directories for path validation.

        Raises:
            FileNotFoundError: If the source file doesn't exist.
            ValueError: If the file is not a valid video.
        """
        super().__init__()

        source_path = Path(source)
        if base_dirs:
            source_path = validate_path(source_path, base_dirs)
        else:
            source_path = source_path.resolve()
            if not source_path.exists():
                msg = f"Video file not found: {source_path}"
                raise FileNotFoundError(msg)

        self.source = source_path
        self.trim_start = trim_start
        self.trim_end = trim_end
        self._speed_factor = speed_factor
        self._reverse = reverse
        self.loop = loop
        self._frame_cache = {}

        # Probe video metadata
        self._source_fps, self._source_duration = self._probe_video()
        logger.debug(
            "video_clip_init",
            source=str(source_path),
            fps=self._source_fps,
            duration=self._source_duration,
        )

    def _probe_video(self) -> tuple[float, float]:
        """Probe video file for fps and duration.

        Returns:
            Tuple of (fps, duration_seconds).
        """
        ffprobe = _get_ffprobe()
        try:
            result = subprocess.run(  # noqa: S603
                [
                    ffprobe,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_streams",
                    "-select_streams",
                    "v:0",
                    str(self.source),
                ],
                shell=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            import json

            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]

            # Parse fps from r_frame_rate (e.g., "30/1")
            fps_str = stream.get("r_frame_rate", "30/1")
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0

            duration = float(stream.get("duration", "0"))
            return fps, duration
        except (subprocess.SubprocessError, ValueError, KeyError):
            logger.warning("video_probe_failed", source=str(self.source))
            return 30.0, 0.0

    def set_trim(self, start: float, end: float | None = None) -> Self:
        """Set trim points.

        Args:
            start: Start time in seconds.
            end: End time in seconds (None = to end).

        Returns:
            Self for method chaining.
        """
        self.trim_start = start
        self.trim_end = end
        self._frame_cache.clear()
        return self

    def set_speed(self, speed: float) -> Self:
        """Set playback speed.

        Args:
            speed: Speed multiplier (1.0 = normal, 2.0 = double speed).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If speed is not positive.
        """
        if speed <= 0:
            msg = f"Speed must be positive, got {speed}"
            raise ValueError(msg)
        self._speed_factor = speed
        self._frame_cache.clear()
        return self

    def set_reverse(self, reverse: bool = True) -> Self:
        """Set reverse playback.

        Args:
            reverse: Whether to play in reverse.

        Returns:
            Self for method chaining.
        """
        self._reverse = reverse
        self._frame_cache.clear()
        return self

    def set_loop(self, count: int = -1) -> Self:
        """Set loop count.

        Args:
            count: Number of loops (-1 = infinite to fill duration).

        Returns:
            Self for method chaining.
        """
        self.loop = count
        self._frame_cache.clear()
        return self

    @property
    def source_fps(self) -> float:
        """Source video frame rate."""
        return self._source_fps

    @property
    def source_duration(self) -> float:
        """Source video duration in seconds."""
        return self._source_duration

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a frame by extracting it from the source video.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of the decoded frame.
        """
        if ctx.local_frame in self._frame_cache:
            return self._frame_cache[ctx.local_frame]

        # Calculate source time for this frame
        source_time = self._calc_source_time(ctx)
        frame = self._extract_frame(source_time, ctx.resolution.width, ctx.resolution.height)

        self._frame_cache[ctx.local_frame] = frame
        return frame

    def _calc_source_time(self, ctx: RenderContext) -> float:
        """Calculate source video timestamp for the given render context.

        Args:
            ctx: Render context.

        Returns:
            Source video time in seconds.
        """
        # Time within the clip
        clip_time = ctx.local_frame / ctx.fps
        # Apply speed
        source_time = clip_time * self._speed_factor + self.trim_start

        # Calculate effective duration
        effective_end = self.trim_end if self.trim_end else self._source_duration
        clip_duration = effective_end - self.trim_start

        if clip_duration > 0:
            # Handle looping
            if self.loop != 1:
                source_time = self.trim_start + ((source_time - self.trim_start) % clip_duration)

            # Handle reverse
            if self._reverse:
                source_time = effective_end - (source_time - self.trim_start)

            # Clamp
            source_time = max(self.trim_start, min(source_time, effective_end))

        return source_time

    def _extract_frame(self, time_sec: float, width: int, height: int) -> np.ndarray:
        """Extract a single frame from the video at the given timestamp.

        Args:
            time_sec: Timestamp in seconds.
            width: Target frame width.
            height: Target frame height.

        Returns:
            BGRA numpy array.
        """
        ffmpeg = _get_ffmpeg()
        try:
            result = subprocess.run(  # noqa: S603
                [
                    ffmpeg,
                    "-ss",
                    str(time_sec),
                    "-i",
                    str(self.source),
                    "-vframes",
                    "1",
                    "-s",
                    f"{width}x{height}",
                    "-pix_fmt",
                    "bgra",
                    "-f",
                    "rawvideo",
                    "-v",
                    "quiet",
                    "pipe:1",
                ],
                shell=False,
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and len(result.stdout) == width * height * 4:
                return np.frombuffer(result.stdout, dtype=np.uint8).reshape(height, width, 4)
        except subprocess.SubprocessError:
            logger.warning("frame_extract_failed", time=time_sec, source=str(self.source))

        # Return black frame on failure
        return np.zeros((height, width, 4), dtype=np.uint8)
