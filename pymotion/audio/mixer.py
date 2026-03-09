"""AudioMixer — multi-track audio mixing engine.

Provides mixing of multiple AudioClip instances across named tracks,
with per-track volume control and final render to interleaved samples.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AudioMixer:
    """Multi-track audio mixer.

    Mixes multiple audio clips across named tracks with per-track volume.
    Renders to interleaved int32 samples at the configured sample rate.

    Args:
        sample_rate: Sample rate in Hz.
        bit_depth: Bit depth for output samples.
        channels: Number of audio channels (1=mono, 2=stereo).
    """

    sample_rate: int = 48000
    bit_depth: int = 24
    channels: int = 2
    _tracks: dict[str, _TrackState] = field(default_factory=dict, repr=False)
    _duration_samples: int = 0

    def add(
        self,
        *clips: AudioClipData,
        track: str = "default",
    ) -> None:
        """Add audio clips to a named track.

        Args:
            *clips: AudioClipData instances to add.
            track: Name of the track to add to.
        """
        if track not in self._tracks:
            self._tracks[track] = _TrackState(name=track)

        for clip in clips:
            self._tracks[track].clips.append(clip)
            end_sample = clip.start_sample + len(clip.samples)
            if end_sample > self._duration_samples:
                self._duration_samples = end_sample

        logger.debug(
            "audio_clips_added",
            track=track,
            count=len(clips),
            total_duration_samples=self._duration_samples,
        )

    def set_volume(self, track: str, volume: float) -> None:
        """Set the volume for a track.

        Args:
            track: Track name.
            volume: Linear volume multiplier (0.0 = silent, 1.0 = unity).

        Raises:
            ValueError: If the track doesn't exist.
        """
        if track not in self._tracks:
            msg = f"Track '{track}' not found. Available: {list(self._tracks.keys())}"
            raise ValueError(msg)
        self._tracks[track].volume = volume

    def set_volume_keyframes(self, track: str, keyframes: list[tuple[int, float]]) -> None:
        """Set volume automation keyframes for a track.

        Args:
            track: Track name.
            keyframes: List of (sample_index, volume) tuples.
                       Volume is linearly interpolated between keyframes.

        Raises:
            ValueError: If the track doesn't exist.
        """
        if track not in self._tracks:
            msg = f"Track '{track}' not found. Available: {list(self._tracks.keys())}"
            raise ValueError(msg)
        self._tracks[track].volume_keyframes = sorted(keyframes, key=lambda k: k[0])

    def set_pan(self, track: str, pan: float) -> None:
        """Set the pan position for a stereo track.

        Args:
            track: Track name.
            pan: Pan position (-1.0 = full left, 0.0 = center, 1.0 = full right).

        Raises:
            ValueError: If the track doesn't exist.
        """
        if track not in self._tracks:
            msg = f"Track '{track}' not found. Available: {list(self._tracks.keys())}"
            raise ValueError(msg)
        self._tracks[track].pan = max(-1.0, min(1.0, pan))

    def set_pan_keyframes(self, track: str, keyframes: list[tuple[int, float]]) -> None:
        """Set pan automation keyframes for a track.

        Args:
            track: Track name.
            keyframes: List of (sample_index, pan) tuples.
                       Pan is linearly interpolated between keyframes.

        Raises:
            ValueError: If the track doesn't exist.
        """
        if track not in self._tracks:
            msg = f"Track '{track}' not found. Available: {list(self._tracks.keys())}"
            raise ValueError(msg)
        self._tracks[track].pan_keyframes = sorted(keyframes, key=lambda k: k[0])

    def render(self) -> np.ndarray:
        """Mix all tracks and render to interleaved samples.

        Returns:
            Interleaved int32 numpy array of shape (n_samples * channels,).
            Empty array if no clips have been added.
        """
        if self._duration_samples == 0:
            return np.zeros(0, dtype=np.int32)

        # Mix buffer in float64 for headroom
        mix = np.zeros((self._duration_samples, self.channels), dtype=np.float64)

        for track_state in self._tracks.values():
            track_buf = np.zeros_like(mix)
            for clip in track_state.clips:
                start = clip.start_sample
                end = start + len(clip.samples)
                if end > self._duration_samples:
                    end = self._duration_samples
                    clipped = clip.samples[: end - start]
                else:
                    clipped = clip.samples

                if clipped.ndim == 1:
                    # Mono → duplicate to all channels
                    for ch in range(self.channels):
                        track_buf[start:end, ch] += clipped
                else:
                    channels_to_mix = min(clipped.shape[1], self.channels)
                    track_buf[start:end, :channels_to_mix] += clipped[:, :channels_to_mix]

            # Apply volume automation or static volume
            if track_state.volume_keyframes:
                vol_curve = self._interpolate_keyframes(
                    track_state.volume_keyframes, self._duration_samples
                )
                for ch in range(self.channels):
                    track_buf[:, ch] *= vol_curve
            else:
                track_buf *= track_state.volume

            # Apply pan (stereo only, skip if center and no keyframes)
            if self.channels == 2 and (track_state.pan_keyframes or track_state.pan != 0.0):
                if track_state.pan_keyframes:
                    pan_curve = self._interpolate_keyframes(
                        track_state.pan_keyframes, self._duration_samples
                    )
                else:
                    pan_curve = np.full(self._duration_samples, track_state.pan, dtype=np.float64)
                # Equal-power pan: left = cos(pan_angle), right = sin(pan_angle)
                pan_angle = (pan_curve + 1.0) * (np.pi / 4.0)  # Map [-1,1] to [0, pi/2]
                track_buf[:, 0] *= np.cos(pan_angle)
                track_buf[:, 1] *= np.sin(pan_angle)

            mix += track_buf

        logger.debug("audio_mix_rendered", duration_samples=self._duration_samples)

        # Normalize and convert to int32
        max_val = 2 ** (self.bit_depth - 1) - 1
        mix = np.clip(mix, -1.0, 1.0) * max_val

        # Interleave channels
        result: np.ndarray = mix.astype(np.int32).flatten()
        return result

    @staticmethod
    def _interpolate_keyframes(keyframes: list[tuple[int, float]], n_samples: int) -> np.ndarray:
        """Linearly interpolate keyframe values over sample range.

        Args:
            keyframes: Sorted list of (sample_index, value) tuples.
            n_samples: Total number of samples.

        Returns:
            Float64 array of interpolated values.
        """
        if not keyframes:
            return np.ones(n_samples, dtype=np.float64)

        xs = np.array([k[0] for k in keyframes], dtype=np.float64)
        ys = np.array([k[1] for k in keyframes], dtype=np.float64)
        samples = np.arange(n_samples, dtype=np.float64)
        return np.interp(samples, xs, ys).astype(np.float64)


@dataclass
class _TrackState:
    """Internal state for an audio track.

    Args:
        name: Track name.
        volume: Track volume multiplier.
        clips: List of audio clip data on this track.
    """

    name: str
    volume: float = 1.0
    pan: float = 0.0
    clips: list[AudioClipData] = field(default_factory=list)
    volume_keyframes: list[tuple[int, float]] = field(default_factory=list)
    pan_keyframes: list[tuple[int, float]] = field(default_factory=list)


@dataclass
class AudioClipData:
    """Raw audio data for mixing.

    This is the internal representation used by the mixer. AudioClip
    instances convert themselves to this format before mixing.

    Args:
        samples: Float64 audio samples, shape (n_samples,) for mono
                 or (n_samples, channels) for multi-channel.
                 Values should be in [-1.0, 1.0].
        start_sample: Starting sample index in the mix timeline.
        sample_rate: Sample rate of this audio data.
    """

    samples: np.ndarray
    start_sample: int = 0
    sample_rate: int = 48000
