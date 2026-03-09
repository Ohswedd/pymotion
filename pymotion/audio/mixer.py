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

            mix += track_buf * track_state.volume

        # Normalize and convert to int32
        max_val = 2 ** (self.bit_depth - 1) - 1
        mix = np.clip(mix, -1.0, 1.0) * max_val

        # Interleave channels
        result: np.ndarray = mix.astype(np.int32).flatten()
        return result


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
    clips: list[AudioClipData] = field(default_factory=list)


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
