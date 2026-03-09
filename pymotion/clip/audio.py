"""AudioClip — audio sources for multi-track mixing.

Provides the AudioClip class for loading, trimming, and manipulating
audio files within a composition.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import numpy as np

from pymotion.security.validation import validate_path
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

_FFMPEG_BIN: str | None = shutil.which("ffmpeg")


def _get_ffmpeg() -> str:
    """Get the ffmpeg binary path."""
    if _FFMPEG_BIN is None:
        msg = "ffmpeg not found on PATH."
        raise RuntimeError(msg)
    return _FFMPEG_BIN


@dataclass
class AudioClip:
    """An audio clip for use in compositions.

    Loads audio from file using FFmpeg and provides trim, fade,
    volume, and loop operations. Designed for use with AudioMixer.

    Args:
        source: Path to the audio file.
        volume: Linear volume multiplier.
        pan: Stereo pan (-1.0 = left, 0.0 = center, 1.0 = right).
        start_frame: Frame at which this clip starts in the timeline.
    """

    source: Path = field(default_factory=lambda: Path(""))
    volume: float = 1.0
    pan: float = 0.0
    start_frame: int = 0
    _trim_start_sec: float = 0.0
    _trim_end_sec: float | None = None
    _fade_in_sec: float = 0.0
    _fade_in_curve: str = "linear"
    _fade_out_sec: float = 0.0
    _fade_out_curve: str = "linear"
    _loop_count: int = 1
    _samples: np.ndarray | None = field(default=None, repr=False)
    _sample_rate: int = 48000

    def __init__(
        self,
        source: str | Path,
        *,
        volume: float = 1.0,
        pan: float = 0.0,
        sample_rate: int = 48000,
        base_dirs: list[Path] | None = None,
    ) -> None:
        """Initialize an AudioClip.

        Args:
            source: Path to the audio file.
            volume: Linear volume multiplier.
            pan: Stereo pan position.
            sample_rate: Target sample rate for decoding.
            base_dirs: Allowed directories for path validation.

        Raises:
            FileNotFoundError: If the source file doesn't exist.
        """
        source_path = Path(source)
        if base_dirs:
            source_path = validate_path(source_path, base_dirs)
        else:
            source_path = source_path.resolve()
            if not source_path.exists():
                msg = f"Audio file not found: {source_path}"
                raise FileNotFoundError(msg)

        self.source = source_path
        self.volume = volume
        self.pan = pan
        self.start_frame = 0
        self._trim_start_sec = 0.0
        self._trim_end_sec = None
        self._fade_in_sec = 0.0
        self._fade_in_curve = "linear"
        self._fade_out_sec = 0.0
        self._fade_out_curve = "linear"
        self._loop_count = 1
        self._samples = None
        self._sample_rate = sample_rate

        logger.debug("audio_clip_init", source=str(source_path))

    def trim(self, start_sec: float, end_sec: float | None = None) -> Self:
        """Set trim points for the audio.

        Args:
            start_sec: Start time in seconds.
            end_sec: End time in seconds (None = to end).

        Returns:
            Self for method chaining.
        """
        self._trim_start_sec = start_sec
        self._trim_end_sec = end_sec
        self._samples = None  # Invalidate cache
        return self

    def fade_in(self, duration_sec: float, curve: str = "linear") -> Self:
        """Apply a fade-in effect.

        Args:
            duration_sec: Fade duration in seconds.
            curve: Easing curve name for the fade.

        Returns:
            Self for method chaining.
        """
        self._fade_in_sec = duration_sec
        self._fade_in_curve = curve
        self._samples = None
        return self

    def fade_out(self, duration_sec: float, curve: str = "linear") -> Self:
        """Apply a fade-out effect.

        Args:
            duration_sec: Fade duration in seconds.
            curve: Easing curve name for the fade.

        Returns:
            Self for method chaining.
        """
        self._fade_out_sec = duration_sec
        self._fade_out_curve = curve
        self._samples = None
        return self

    def loop(self, count: int = -1) -> Self:
        """Set loop count.

        Args:
            count: Number of loops (-1 = infinite to fill duration).

        Returns:
            Self for method chaining.
        """
        self._loop_count = count
        self._samples = None
        return self

    def at(self, frame: int) -> Self:
        """Set the start frame in the timeline.

        Args:
            frame: Frame number at which this audio starts.

        Returns:
            Self for method chaining.
        """
        self.start_frame = frame
        return self

    def at_seconds(self, seconds: float, fps: int = 30) -> Self:
        """Set the start time in seconds.

        Args:
            seconds: Start time in seconds.
            fps: Frames per second for conversion.

        Returns:
            Self for method chaining.
        """
        self.start_frame = round(seconds * fps)
        return self

    def get_samples(self) -> np.ndarray:
        """Decode and return the processed audio samples.

        Applies trim, fade, volume, and loop operations.

        Returns:
            Float64 audio samples of shape (n_samples, 2) for stereo.
        """
        if self._samples is not None:
            return self._samples

        raw = self._decode_audio()
        processed = self._apply_effects(raw)
        self._samples = processed
        return processed

    def _decode_audio(self) -> np.ndarray:
        """Decode audio file using FFmpeg.

        Returns:
            Float64 audio samples, shape (n_samples, 2).
        """
        ffmpeg = _get_ffmpeg()

        cmd = [
            ffmpeg,
            "-v",
            "quiet",
        ]

        if self._trim_start_sec > 0:
            cmd.extend(["-ss", str(self._trim_start_sec)])

        cmd.extend(["-i", str(self.source)])

        if self._trim_end_sec is not None:
            duration = self._trim_end_sec - self._trim_start_sec
            cmd.extend(["-t", str(duration)])

        cmd.extend(
            [
                "-f",
                "f64le",
                "-acodec",
                "pcm_f64le",
                "-ac",
                "2",
                "-ar",
                str(self._sample_rate),
                "pipe:1",
            ]
        )

        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                shell=False,
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and len(result.stdout) > 0:
                samples = np.frombuffer(result.stdout, dtype=np.float64)
                return samples.reshape(-1, 2)
        except subprocess.SubprocessError:
            logger.warning("audio_decode_failed", source=str(self.source))

        return np.zeros((0, 2), dtype=np.float64)

    def _apply_effects(self, samples: np.ndarray) -> np.ndarray:
        """Apply volume, fade, pan, and loop to decoded samples.

        Args:
            samples: Raw decoded samples (n_samples, 2).

        Returns:
            Processed samples.
        """
        if len(samples) == 0:
            return samples

        # Apply volume
        result = samples * self.volume

        # Apply fade in
        if self._fade_in_sec > 0:
            fade_samples = int(self._fade_in_sec * self._sample_rate)
            fade_samples = min(fade_samples, len(result))
            if fade_samples > 0:
                ramp = np.linspace(0.0, 1.0, fade_samples, dtype=np.float64)
                result[:fade_samples] *= ramp[:, np.newaxis]

        # Apply fade out
        if self._fade_out_sec > 0:
            fade_samples = int(self._fade_out_sec * self._sample_rate)
            fade_samples = min(fade_samples, len(result))
            if fade_samples > 0:
                ramp = np.linspace(1.0, 0.0, fade_samples, dtype=np.float64)
                result[-fade_samples:] *= ramp[:, np.newaxis]

        # Apply pan (constant-power panning)
        if self.pan != 0.0 and result.shape[1] >= 2:
            angle = (self.pan + 1.0) * np.pi / 4  # 0 to pi/2
            left_gain = np.cos(angle)
            right_gain = np.sin(angle)
            result[:, 0] *= left_gain
            result[:, 1] *= right_gain

        # Apply loop
        if self._loop_count != 1 and len(result) > 0:
            if self._loop_count == -1:
                # Will be handled by the mixer when clip duration is set
                pass
            elif self._loop_count > 1:
                result = np.tile(result, (self._loop_count, 1))

        return result

    @property
    def sample_rate(self) -> int:
        """Audio sample rate."""
        return self._sample_rate
