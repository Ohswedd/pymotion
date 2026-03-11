"""AudioMixer — multi-track audio mixing engine.

Provides mixing of multiple AudioClip instances across named tracks,
with per-track volume control, surround channel routing, and final
render to interleaved samples.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

#: Type alias for the keyframe interpolation callable.
_InterpolateKeyframesFn = Callable[[list[tuple[int, float]], int], np.ndarray]


class SurroundChannel(IntEnum):
    """Standard channel indices for surround sound layouts.

    Defines the 5.1 surround channel order used throughout PyMotion.
    Follows the SMPTE/ITU standard channel ordering.

    Attributes:
        L: Front left channel (index 0).
        R: Front right channel (index 1).
        C: Center channel (index 2).
        LFE: Low-frequency effects / subwoofer channel (index 3).
        LS: Left surround / rear left channel (index 4).
        RS: Right surround / rear right channel (index 5).
    """

    L = 0
    R = 1
    C = 2
    LFE = 3
    LS = 4
    RS = 5


class ChannelLayout(IntEnum):
    """Standard channel layout presets.

    Attributes:
        MONO: Single channel (1).
        STEREO: Left and right channels (2).
        SURROUND_51: 5.1 surround — L, R, C, LFE, Ls, Rs (6).
    """

    MONO = 1
    STEREO = 2
    SURROUND_51 = 6


#: Channel name to index mapping for 5.1 surround.
SURROUND_51_CHANNELS: dict[str, int] = {
    "L": SurroundChannel.L,
    "R": SurroundChannel.R,
    "C": SurroundChannel.C,
    "LFE": SurroundChannel.LFE,
    "Ls": SurroundChannel.LS,
    "Rs": SurroundChannel.RS,
}

#: Channel name to index mapping for stereo.
STEREO_CHANNELS: dict[str, int] = {
    "L": 0,
    "R": 1,
}


@dataclass
class AudioBus:
    """A submix bus that aggregates tracks before the master bus.

    Buses allow grouping related tracks (e.g. dialogue, music, sfx)
    with shared volume and pan control. All buses feed into the
    master bus during rendering.

    Args:
        name: Bus name (e.g. ``"dialogue"``, ``"music"``, ``"sfx"``).
        volume: Bus volume multiplier (0.0–1.0).
        pan: Stereo pan position (-1.0 left, 0.0 center, 1.0 right).
        tracks: Track names assigned to this bus.
    """

    name: str
    volume: float = 1.0
    pan: float = 0.0
    tracks: list[str] = field(default_factory=list)
    volume_keyframes: list[tuple[int, float]] = field(default_factory=list)
    pan_keyframes: list[tuple[int, float]] = field(default_factory=list)
    routing: dict[int, float] | None = None


@dataclass
class AudioMixer:
    """Multi-track audio mixer with bus routing.

    Mixes multiple audio clips across named tracks with per-track volume.
    Optionally groups tracks into named buses (submixes) that feed into
    a master bus. Renders to interleaved int32 samples at the configured
    sample rate.

    Args:
        sample_rate: Sample rate in Hz.
        bit_depth: Bit depth for output samples.
        channels: Number of audio channels (1=mono, 2=stereo, 6=5.1).
    """

    sample_rate: int = 48000
    bit_depth: int = 24
    channels: int = 2
    _tracks: dict[str, _TrackState] = field(default_factory=dict, repr=False)
    _buses: dict[str, AudioBus] = field(default_factory=dict, repr=False)
    _duration_samples: int = 0
    _target_lufs: float | None = field(default=None, repr=False)
    _sidechains: list[tuple[str, str, float, float, float, float]] = field(
        default_factory=list, repr=False
    )

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

    def set_routing(
        self,
        track: str,
        routing: dict[int | str | SurroundChannel, float],
    ) -> None:
        """Set channel routing for a track.

        Routes the track's audio to specific output channels with gain
        control. When routing is set, pan is ignored and audio is sent
        directly to the specified channels.

        For 5.1 surround (channels=6), use ``SurroundChannel`` enum values
        or string names (``"L"``, ``"R"``, ``"C"``, ``"LFE"``, ``"Ls"``,
        ``"Rs"``) as keys:

        .. code-block:: python

            mixer = AudioMixer(channels=6)
            mixer.add(dialogue, track="dialogue")
            mixer.set_routing("dialogue", {"C": 1.0, "LFE": 0.3})

        Args:
            track: Track name.
            routing: Mapping of channel index/name/enum to gain (0.0–1.0).
                     Keys can be ``int``, ``str`` channel names, or
                     ``SurroundChannel`` enum values.

        Raises:
            ValueError: If the track doesn't exist or a channel name is
                        invalid or a channel index is out of range.
        """
        if track not in self._tracks:
            msg = f"Track '{track}' not found. Available: {list(self._tracks.keys())}"
            raise ValueError(msg)

        resolved: dict[int, float] = {}
        channel_names = SURROUND_51_CHANNELS if self.channels == 6 else STEREO_CHANNELS

        for key, gain in routing.items():
            if isinstance(key, str):
                if key not in channel_names:
                    valid = ", ".join(sorted(channel_names.keys()))
                    msg = f"Unknown channel name '{key}'. Valid names: {valid}"
                    raise ValueError(msg)
                resolved[channel_names[key]] = float(gain)
            else:
                idx = int(key)
                if idx < 0 or idx >= self.channels:
                    msg = f"Channel index {idx} out of range for {self.channels}-channel mixer"
                    raise ValueError(msg)
                resolved[idx] = float(gain)

        self._tracks[track].routing = resolved
        logger.debug(
            "channel_routing_set",
            track=track,
            routing=resolved,
        )

    def create_bus(self, name: str, *, volume: float = 1.0, pan: float = 0.0) -> None:
        """Create a named submix bus.

        Buses group tracks into submixes that feed into the master bus.
        Tracks assigned to a bus have their output mixed through the bus
        before reaching the master. Tracks not assigned to any bus mix
        directly into the master.

        Args:
            name: Unique bus name (e.g. ``"dialogue"``, ``"music"``).
            volume: Bus volume multiplier (0.0 = silent, 1.0 = unity).
            pan: Stereo pan position (-1.0 left, 0.0 center, 1.0 right).

        Raises:
            ValueError: If a bus with this name already exists.
        """
        if name in self._buses:
            msg = f"Bus '{name}' already exists"
            raise ValueError(msg)
        self._buses[name] = AudioBus(name=name, volume=volume, pan=pan)
        logger.debug("audio_bus_created", bus=name)

    def assign_track_to_bus(self, track: str, bus: str) -> None:
        """Assign a track to a submix bus.

        Args:
            track: Track name.
            bus: Bus name.

        Raises:
            ValueError: If the track or bus doesn't exist.
        """
        if track not in self._tracks:
            msg = f"Track '{track}' not found. Available: {list(self._tracks.keys())}"
            raise ValueError(msg)
        if bus not in self._buses:
            msg = f"Bus '{bus}' not found. Available: {list(self._buses.keys())}"
            raise ValueError(msg)
        if track not in self._buses[bus].tracks:
            self._buses[bus].tracks.append(track)
        logger.debug("track_assigned_to_bus", track=track, bus=bus)

    def set_bus_volume(self, bus: str, volume: float) -> None:
        """Set the volume for a bus.

        Args:
            bus: Bus name.
            volume: Linear volume multiplier (0.0 = silent, 1.0 = unity).

        Raises:
            ValueError: If the bus doesn't exist.
        """
        if bus not in self._buses:
            msg = f"Bus '{bus}' not found. Available: {list(self._buses.keys())}"
            raise ValueError(msg)
        self._buses[bus].volume = volume

    def set_bus_volume_keyframes(self, bus: str, keyframes: list[tuple[int, float]]) -> None:
        """Set volume automation keyframes for a bus.

        Args:
            bus: Bus name.
            keyframes: List of (sample_index, volume) tuples.

        Raises:
            ValueError: If the bus doesn't exist.
        """
        if bus not in self._buses:
            msg = f"Bus '{bus}' not found. Available: {list(self._buses.keys())}"
            raise ValueError(msg)
        self._buses[bus].volume_keyframes = sorted(keyframes, key=lambda k: k[0])

    def set_bus_pan(self, bus: str, pan: float) -> None:
        """Set the pan position for a bus.

        Args:
            bus: Bus name.
            pan: Pan position (-1.0 = full left, 0.0 = center, 1.0 = full right).

        Raises:
            ValueError: If the bus doesn't exist.
        """
        if bus not in self._buses:
            msg = f"Bus '{bus}' not found. Available: {list(self._buses.keys())}"
            raise ValueError(msg)
        self._buses[bus].pan = max(-1.0, min(1.0, pan))

    def set_bus_pan_keyframes(self, bus: str, keyframes: list[tuple[int, float]]) -> None:
        """Set pan automation keyframes for a bus.

        Args:
            bus: Bus name.
            keyframes: List of (sample_index, pan) tuples.
                       Pan is linearly interpolated between keyframes.

        Raises:
            ValueError: If the bus doesn't exist.
        """
        if bus not in self._buses:
            msg = f"Bus '{bus}' not found. Available: {list(self._buses.keys())}"
            raise ValueError(msg)
        self._buses[bus].pan_keyframes = sorted(keyframes, key=lambda k: k[0])

    def set_bus_routing(
        self,
        bus: str,
        routing: dict[int | str | SurroundChannel, float],
    ) -> None:
        """Set channel routing for a bus.

        Routes the bus output to specific output channels. Same interface
        as ``set_routing()`` for tracks.

        Args:
            bus: Bus name.
            routing: Mapping of channel index/name/enum to gain.

        Raises:
            ValueError: If the bus doesn't exist or a channel is invalid.
        """
        if bus not in self._buses:
            msg = f"Bus '{bus}' not found. Available: {list(self._buses.keys())}"
            raise ValueError(msg)

        resolved: dict[int, float] = {}
        channel_names = SURROUND_51_CHANNELS if self.channels == 6 else STEREO_CHANNELS

        for key, gain in routing.items():
            if isinstance(key, str):
                if key not in channel_names:
                    valid = ", ".join(sorted(channel_names.keys()))
                    msg = f"Unknown channel name '{key}'. Valid names: {valid}"
                    raise ValueError(msg)
                resolved[channel_names[key]] = float(gain)
            else:
                idx = int(key)
                if idx < 0 or idx >= self.channels:
                    msg = f"Channel index {idx} out of range for {self.channels}-channel mixer"
                    raise ValueError(msg)
                resolved[idx] = float(gain)

        self._buses[bus].routing = resolved

    def _get_bus_for_track(self, track_name: str) -> AudioBus | None:
        """Find the bus a track is assigned to, if any.

        Args:
            track_name: Track name.

        Returns:
            The AudioBus or None if the track is not assigned to any bus.
        """
        for bus in self._buses.values():
            if track_name in bus.tracks:
                return bus
        return None

    def _render_track(self, track_state: _TrackState) -> np.ndarray:
        """Render a single track to a float64 buffer.

        Args:
            track_state: The track to render.

        Returns:
            Float64 array of shape (duration_samples, channels).
        """
        track_buf = np.zeros((self._duration_samples, self.channels), dtype=np.float64)
        for clip in track_state.clips:
            start = clip.start_sample
            end = start + len(clip.samples)
            if end > self._duration_samples:
                end = self._duration_samples
                clipped = clip.samples[: end - start]
            else:
                clipped = clip.samples

            if clipped.ndim == 1:
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

        # Apply channel routing or pan
        if track_state.routing is not None:
            routed = np.zeros_like(track_buf)
            for ch_idx, gain in track_state.routing.items():
                if ch_idx < self.channels:
                    routed[:, ch_idx] += track_buf.mean(axis=1) * gain
            track_buf = routed
        elif self.channels == 2 and (track_state.pan_keyframes or track_state.pan != 0.0):
            if track_state.pan_keyframes:
                pan_curve = self._interpolate_keyframes(
                    track_state.pan_keyframes, self._duration_samples
                )
            else:
                pan_curve = np.full(self._duration_samples, track_state.pan, dtype=np.float64)
            pan_angle = (pan_curve + 1.0) * (np.pi / 4.0)
            track_buf[:, 0] *= np.cos(pan_angle)
            track_buf[:, 1] *= np.sin(pan_angle)

        return track_buf

    @staticmethod
    def _apply_bus_processing(
        bus_buf: np.ndarray,
        bus: AudioBus,
        n_samples: int,
        n_channels: int,
        interpolate_fn: _InterpolateKeyframesFn,
    ) -> np.ndarray:
        """Apply bus-level volume, pan, and routing.

        Args:
            bus_buf: The accumulated bus buffer.
            bus: The bus to process.
            n_samples: Total number of samples.
            n_channels: Number of output channels.
            interpolate_fn: Keyframe interpolation function.

        Returns:
            Processed bus buffer.
        """
        # Bus volume
        if bus.volume_keyframes:
            vol_curve = interpolate_fn(bus.volume_keyframes, n_samples)
            for ch in range(n_channels):
                bus_buf[:, ch] *= vol_curve
        else:
            bus_buf *= bus.volume

        # Bus routing
        if bus.routing is not None:
            routed = np.zeros_like(bus_buf)
            for ch_idx, gain in bus.routing.items():
                if ch_idx < n_channels:
                    routed[:, ch_idx] += bus_buf.mean(axis=1) * gain
            bus_buf = routed
        elif n_channels == 2 and (bus.pan_keyframes or bus.pan != 0.0):
            if bus.pan_keyframes:
                pan_curve = interpolate_fn(bus.pan_keyframes, n_samples)
            else:
                pan_curve = np.full(n_samples, bus.pan, dtype=np.float64)
            pan_angle = (pan_curve + 1.0) * (np.pi / 4.0)
            bus_buf[:, 0] *= np.cos(pan_angle)
            bus_buf[:, 1] *= np.sin(pan_angle)

        return bus_buf

    def normalize(self, target_lufs: float = -14.0) -> None:
        """Set loudness normalization target for the final mix.

        When set, the rendered output is measured and a linear gain is
        applied so the integrated loudness matches the target LUFS value.
        Common targets:

        - ``-14`` for streaming (Spotify, YouTube, Apple Music)
        - ``-23`` for broadcast (EBU R128)
        - ``-16`` for podcasts

        Args:
            target_lufs: Target integrated loudness in LUFS (Loudness
                         Units relative to Full Scale).
        """
        self._target_lufs = target_lufs
        logger.debug("normalization_set", target_lufs=target_lufs)

    def sidechain(
        self,
        sidechain_track: str,
        target_track: str,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 10.0,
        release_ms: float = 100.0,
    ) -> None:
        """Set up sidechain compression — reduce target track volume based on sidechain track level.

        When the sidechain track exceeds the threshold, the target track's
        volume is reduced by the specified ratio. Common use: duck music
        under dialogue.

        Args:
            sidechain_track: Name of the track whose level triggers compression.
            target_track: Name of the track to compress.
            threshold_db: Level in dB above which compression activates.
            ratio: Compression ratio (e.g. 4.0 means 4:1).
            attack_ms: Time in ms for compressor to engage.
            release_ms: Time in ms for compressor to disengage.

        Raises:
            ValueError: If either track name is unknown.
        """
        if sidechain_track not in self._tracks:
            msg = f"Unknown sidechain track '{sidechain_track}'. Add it first with add()."
            raise ValueError(msg)
        if target_track not in self._tracks:
            msg = f"Unknown target track '{target_track}'. Add it first with add()."
            raise ValueError(msg)
        self._sidechains.append(
            (sidechain_track, target_track, threshold_db, ratio, attack_ms, release_ms)
        )
        logger.debug(
            "sidechain_set",
            sidechain=sidechain_track,
            target=target_track,
            threshold_db=threshold_db,
            ratio=ratio,
        )

    def _apply_sidechain(
        self,
        target_buf: np.ndarray,
        sidechain_buf: np.ndarray,
        threshold_db: float,
        ratio: float,
        attack_ms: float,
        release_ms: float,
    ) -> np.ndarray:
        """Apply sidechain compression to target buffer.

        Args:
            target_buf: Audio to compress, shape (n_samples, channels).
            sidechain_buf: Sidechain source, shape (n_samples, channels).
            threshold_db: Threshold in dB.
            ratio: Compression ratio.
            attack_ms: Attack time in ms.
            release_ms: Release time in ms.

        Returns:
            Compressed target buffer.
        """
        # Compute envelope of sidechain signal (RMS per sample with smoothing)
        sc_mono = np.mean(np.abs(sidechain_buf), axis=1)
        # Convert to dB
        sc_db = 20.0 * np.log10(np.maximum(sc_mono, 1e-10))

        # Compute gain reduction
        over = np.maximum(sc_db - threshold_db, 0.0)
        gain_reduction_db = over * (1.0 - 1.0 / max(ratio, 1.001))
        gain_linear = 10.0 ** (-gain_reduction_db / 20.0)

        # Apply attack/release smoothing
        attack_coeff = np.exp(-1.0 / max(1.0, attack_ms * self.sample_rate / 1000.0))
        release_coeff = np.exp(-1.0 / max(1.0, release_ms * self.sample_rate / 1000.0))

        smoothed = np.ones_like(gain_linear)
        for i in range(1, len(smoothed)):
            if gain_linear[i] < smoothed[i - 1]:
                smoothed[i] = attack_coeff * smoothed[i - 1] + (1.0 - attack_coeff) * gain_linear[i]
            else:
                smoothed[i] = (
                    release_coeff * smoothed[i - 1] + (1.0 - release_coeff) * gain_linear[i]
                )

        out: np.ndarray = target_buf * smoothed[:, np.newaxis]
        return out

    @staticmethod
    def _measure_lufs(samples: np.ndarray, sample_rate: int) -> float:
        """Measure integrated LUFS of audio using ITU-R BS.1770 simplified.

        Applies K-weighting (pre-filter + RLB filter) then measures the
        mean square level across all channels with channel weighting.

        Args:
            samples: Float64 audio, shape ``(n_samples, channels)``.
            sample_rate: Sample rate in Hz.

        Returns:
            Integrated loudness in LUFS.
        """
        if len(samples) == 0:
            return -70.0

        # Simplified K-weighting: high-shelf boost + high-pass
        # Stage 1: Pre-filter (high-shelf +4dB at ~1681 Hz)
        # Stage 2: RLB weighting (high-pass ~38 Hz)
        # For simplicity, use biquad coefficients for 48kHz
        # (close enough for other rates in practice)
        weighted = samples.copy()

        # Stage 1: Pre-filter (second-order high-shelf)
        if sample_rate >= 44100:
            # Coefficients for ~48kHz (ITU-R BS.1770-4)
            f0 = 1681.974450955533
            q = 0.7071752369554196
            db_gain = 3.999843853973347
            w0 = 2.0 * np.pi * f0 / sample_rate
            a_val = 10.0 ** (db_gain / 40.0)
            alpha = np.sin(w0) / (2.0 * q)
            cos_w0 = np.cos(w0)

            b0 = a_val * ((a_val + 1) + (a_val - 1) * cos_w0 + 2 * np.sqrt(a_val) * alpha)
            b1 = -2 * a_val * ((a_val - 1) + (a_val + 1) * cos_w0)
            b2 = a_val * ((a_val + 1) + (a_val - 1) * cos_w0 - 2 * np.sqrt(a_val) * alpha)
            a0 = (a_val + 1) - (a_val - 1) * cos_w0 + 2 * np.sqrt(a_val) * alpha
            a1 = 2 * ((a_val - 1) - (a_val + 1) * cos_w0)
            a2 = (a_val + 1) - (a_val - 1) * cos_w0 - 2 * np.sqrt(a_val) * alpha

            weighted = AudioMixer._apply_biquad_filter(
                weighted, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
            )

            # Stage 2: High-pass ~38 Hz (RLB weighting)
            f0_hp = 38.13547087602444
            q_hp = 0.5003270373238773
            w0_hp = 2.0 * np.pi * f0_hp / sample_rate
            alpha_hp = np.sin(w0_hp) / (2.0 * q_hp)
            cos_w0_hp = np.cos(w0_hp)

            b0_h = (1.0 + cos_w0_hp) / 2.0
            b1_h = -(1.0 + cos_w0_hp)
            b2_h = b0_h
            a0_h = 1.0 + alpha_hp
            a1_h = -2.0 * cos_w0_hp
            a2_h = 1.0 - alpha_hp

            weighted = AudioMixer._apply_biquad_filter(
                weighted, b0_h / a0_h, b1_h / a0_h, b2_h / a0_h, a1_h / a0_h, a2_h / a0_h
            )

        # Channel weighting (ITU-R BS.1770): surround channels get +1.5 dB
        n_ch = weighted.shape[1]
        weights = np.ones(n_ch, dtype=np.float64)
        if n_ch >= 6:
            # Ls and Rs channels get +1.5 dB weighting
            weights[4] = 10.0 ** (1.5 / 10.0)
            weights[5] = 10.0 ** (1.5 / 10.0)
            weights[3] = 0.0  # LFE excluded from loudness measurement

        # Mean square per channel, weighted sum
        ms = np.mean(weighted**2, axis=0)
        total = float(np.sum(ms * weights))

        if total <= 0:
            return -70.0

        lufs: float = -0.691 + 10.0 * np.log10(total)
        return lufs

    @staticmethod
    def _apply_biquad_filter(
        samples: np.ndarray,
        b0: float,
        b1: float,
        b2: float,
        a1: float,
        a2: float,
    ) -> np.ndarray:
        """Apply biquad filter to multi-channel audio.

        Args:
            samples: Input (n_samples, channels).
            b0, b1, b2: Feed-forward coefficients.
            a1, a2: Feed-back coefficients.

        Returns:
            Filtered samples.
        """
        n_samples, n_channels = samples.shape
        out = np.zeros_like(samples)
        for ch in range(n_channels):
            x = samples[:, ch]
            y = out[:, ch]
            x1 = 0.0
            x2 = 0.0
            y1 = 0.0
            y2 = 0.0
            for n in range(n_samples):
                y[n] = b0 * x[n] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
                x2 = x1
                x1 = x[n]
                y2 = y1
                y1 = y[n]
        return out

    def render(self) -> np.ndarray:
        """Mix all tracks and render to interleaved samples.

        Tracks assigned to buses are mixed through their bus (submix)
        before reaching the master. Tracks not on any bus mix directly
        into the master.

        Returns:
            Interleaved int32 numpy array of shape (n_samples * channels,).
            Empty array if no clips have been added.
        """
        if self._duration_samples == 0:
            return np.zeros(0, dtype=np.int32)

        mix = np.zeros((self._duration_samples, self.channels), dtype=np.float64)

        # Collect track names assigned to buses
        bused_tracks: set[str] = set()
        for bus in self._buses.values():
            bused_tracks.update(bus.tracks)

        # Pre-render tracks for sidechain processing
        rendered_tracks: dict[str, np.ndarray] = {}
        sidechain_targets: set[str] = set()
        for sc_track, tgt_track, *_ in self._sidechains:
            sidechain_targets.add(tgt_track)
            if sc_track not in rendered_tracks and sc_track in self._tracks:
                rendered_tracks[sc_track] = self._render_track(self._tracks[sc_track])
            if tgt_track not in rendered_tracks and tgt_track in self._tracks:
                rendered_tracks[tgt_track] = self._render_track(self._tracks[tgt_track])

        # Apply sidechain compression
        for sc_track, tgt_track, thresh, ratio, attack, release in self._sidechains:
            if sc_track in rendered_tracks and tgt_track in rendered_tracks:
                rendered_tracks[tgt_track] = self._apply_sidechain(
                    rendered_tracks[tgt_track],
                    rendered_tracks[sc_track],
                    thresh,
                    ratio,
                    attack,
                    release,
                )

        # Render tracks not on any bus directly into master
        for name, track_state in self._tracks.items():
            if name not in bused_tracks:
                if name in rendered_tracks:
                    mix += rendered_tracks[name]
                else:
                    mix += self._render_track(track_state)

        # Render bus submixes
        for bus in self._buses.values():
            bus_buf = np.zeros((self._duration_samples, self.channels), dtype=np.float64)
            for track_name in bus.tracks:
                if track_name in self._tracks:
                    bus_buf += self._render_track(self._tracks[track_name])

            bus_buf = self._apply_bus_processing(
                bus_buf,
                bus,
                self._duration_samples,
                self.channels,
                self._interpolate_keyframes,
            )
            mix += bus_buf

        logger.debug("audio_mix_rendered", duration_samples=self._duration_samples)

        # Apply LUFS normalization if requested
        if self._target_lufs is not None:
            current_lufs = self._measure_lufs(mix, self.sample_rate)
            if current_lufs > -70.0:
                gain_db = self._target_lufs - current_lufs
                gain_linear = 10.0 ** (gain_db / 20.0)
                mix = mix * gain_linear
                logger.debug(
                    "lufs_normalized",
                    current_lufs=round(current_lufs, 1),
                    target_lufs=self._target_lufs,
                    gain_db=round(gain_db, 1),
                )

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
    routing: dict[int, float] | None = None


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
