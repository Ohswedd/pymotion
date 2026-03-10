"""Audio DSP effects via pedalboard.

Provides audio effect wrappers around the pedalboard library for
common audio processing operations including EQ, dynamics,
reverb, delay, pitch shifting, noise reduction, filtering, and
crossfade utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

#: Supported crossfade curve types.
CrossfadeType = Literal["linear", "equal_power", "s_curve"]


def _import_pedalboard() -> Any:
    """Lazy import for pedalboard."""
    import pedalboard  # noqa: PLC0415

    return pedalboard


def _process_audio(plugin: Any, samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Run a pedalboard plugin on audio samples.

    Args:
        plugin: A pedalboard plugin instance.
        samples: Audio samples, shape (n_samples, channels).
        sample_rate: Sample rate in Hz.

    Returns:
        Processed audio samples.
    """
    audio = samples.astype(np.float32)
    if audio.ndim == 2:
        audio = audio.T
    elif audio.ndim == 1:
        audio = audio.reshape(1, -1)

    processed: np.ndarray = plugin(audio, sample_rate)

    if processed.ndim == 2:
        processed = processed.T
    return processed.astype(samples.dtype)


@dataclass
class EQBand:
    """A single band of an equalizer.

    Args:
        frequency: Center frequency in Hz.
        gain_db: Gain in decibels.
        q: Q factor (bandwidth).
        band_type: Type of filter ("peak", "low_shelf", "high_shelf").
    """

    frequency: float = 1000.0
    gain_db: float = 0.0
    q: float = 1.0
    band_type: str = "peak"


@dataclass
class EQ:
    """Parametric equalizer effect.

    Applies multi-band EQ using pedalboard's PeakFilter,
    LowShelfFilter, and HighShelfFilter.

    Args:
        bands: List of EQ bands to apply.
    """

    bands: list[EQBand] = field(default_factory=list)

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply EQ to audio samples.

        Args:
            samples: Float32 audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        if len(self.bands) == 0:
            return samples

        pb = _import_pedalboard()
        plugins: list[Any] = []
        for band in self.bands:
            if band.band_type == "low_shelf":
                plugins.append(
                    pb.LowShelfFilter(
                        cutoff_frequency_hz=band.frequency,
                        gain_db=band.gain_db,
                        q=band.q,
                    )
                )
            elif band.band_type == "high_shelf":
                plugins.append(
                    pb.HighShelfFilter(
                        cutoff_frequency_hz=band.frequency,
                        gain_db=band.gain_db,
                        q=band.q,
                    )
                )
            else:
                plugins.append(
                    pb.PeakFilter(
                        cutoff_frequency_hz=band.frequency,
                        gain_db=band.gain_db,
                        q=band.q,
                    )
                )

        board: Any = pb.Pedalboard(plugins)
        return _process_audio(board, samples, sample_rate)


@dataclass
class Compressor:
    """Dynamic range compressor effect.

    Args:
        threshold_db: Threshold in decibels.
        ratio: Compression ratio (e.g., 4.0 = 4:1).
        attack_ms: Attack time in milliseconds.
        release_ms: Release time in milliseconds.
    """

    threshold_db: float = -20.0
    ratio: float = 4.0
    attack_ms: float = 10.0
    release_ms: float = 100.0

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply compression to audio samples.

        Args:
            samples: Float32 audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Compressed audio samples.
        """
        pb = _import_pedalboard()
        comp: Any = pb.Compressor(
            threshold_db=self.threshold_db,
            ratio=self.ratio,
            attack_ms=self.attack_ms,
            release_ms=self.release_ms,
        )
        return _process_audio(comp, samples, sample_rate)


@dataclass
class Limiter:
    """Brickwall limiter effect.

    Args:
        threshold_db: Threshold in decibels.
        release_ms: Release time in milliseconds.
    """

    threshold_db: float = -1.0
    release_ms: float = 100.0

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply limiting to audio samples.

        Args:
            samples: Float32 audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Limited audio samples.
        """
        pb = _import_pedalboard()
        lim: Any = pb.Limiter(
            threshold_db=self.threshold_db,
            release_ms=self.release_ms,
        )
        return _process_audio(lim, samples, sample_rate)


@dataclass
class Reverb:
    """Reverb effect.

    Adds spatial reverberation to audio using a simple algorithmic reverb.

    Args:
        room_size: Size of the virtual room (0.0 to 1.0).
        damping: High-frequency damping (0.0 to 1.0).
        wet_level: Wet signal level (0.0 to 1.0).
        dry_level: Dry signal level (0.0 to 1.0).
    """

    room_size: float = 0.5
    damping: float = 0.5
    wet_level: float = 0.33
    dry_level: float = 0.4

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply reverb to audio samples.

        Args:
            samples: Audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        pb = _import_pedalboard()
        reverb: Any = pb.Reverb(
            room_size=self.room_size,
            damping=self.damping,
            wet_level=self.wet_level,
            dry_level=self.dry_level,
        )
        return _process_audio(reverb, samples, sample_rate)


@dataclass
class Delay:
    """Delay effect.

    Adds an echo/delay effect to audio.

    Args:
        delay_seconds: Delay time in seconds.
        feedback: Feedback amount (0.0 to 1.0).
        mix: Wet/dry mix (0.0 = dry, 1.0 = wet).
    """

    delay_seconds: float = 0.25
    feedback: float = 0.3
    mix: float = 0.5

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply delay to audio samples.

        Args:
            samples: Audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        pb = _import_pedalboard()
        delay: Any = pb.Delay(
            delay_seconds=self.delay_seconds,
            feedback=self.feedback,
            mix=self.mix,
        )
        return _process_audio(delay, samples, sample_rate)


@dataclass
class PitchShift:
    """Pitch shift effect.

    Shifts the pitch of audio without changing tempo.

    Args:
        semitones: Number of semitones to shift (positive = up, negative = down).
    """

    semitones: float = 0.0

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply pitch shift to audio samples.

        Args:
            samples: Audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        pb = _import_pedalboard()
        shift: Any = pb.PitchShift(semitones=self.semitones)
        return _process_audio(shift, samples, sample_rate)


@dataclass
class NoiseReduction:
    """Noise reduction effect.

    Applies a noise gate to reduce background noise.

    Args:
        threshold_db: Gate threshold in decibels.
        ratio: Reduction ratio.
        attack_ms: Attack time in milliseconds.
        release_ms: Release time in milliseconds.
    """

    threshold_db: float = -40.0
    ratio: float = 10.0
    attack_ms: float = 1.0
    release_ms: float = 100.0

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply noise reduction to audio samples.

        Args:
            samples: Audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        pb = _import_pedalboard()
        gate: Any = pb.NoiseGate(
            threshold_db=self.threshold_db,
            ratio=self.ratio,
            attack_ms=self.attack_ms,
            release_ms=self.release_ms,
        )
        return _process_audio(gate, samples, sample_rate)


@dataclass
class LowPassFilter:
    """Low-pass filter effect.

    Passes frequencies below the cutoff and attenuates higher frequencies.

    Args:
        cutoff_hz: Cutoff frequency in Hz.
    """

    cutoff_hz: float = 5000.0

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply low-pass filter to audio samples.

        Args:
            samples: Audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        pb = _import_pedalboard()
        lpf: Any = pb.LowpassFilter(cutoff_frequency_hz=self.cutoff_hz)
        return _process_audio(lpf, samples, sample_rate)


@dataclass
class HighPassFilter:
    """High-pass filter effect.

    Passes frequencies above the cutoff and attenuates lower frequencies.

    Args:
        cutoff_hz: Cutoff frequency in Hz.
    """

    cutoff_hz: float = 200.0

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply high-pass filter to audio samples.

        Args:
            samples: Audio samples, shape (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        pb = _import_pedalboard()
        hpf: Any = pb.HighpassFilter(cutoff_frequency_hz=self.cutoff_hz)
        return _process_audio(hpf, samples, sample_rate)


@dataclass
class MultibandCompressor:
    """4-band multiband compressor.

    Splits the audio into 4 frequency bands at configurable crossover
    frequencies, applies independent compression to each band, then
    recombines. Pure NumPy implementation — no external dependencies.

    Args:
        crossover_freqs: Three crossover frequencies in Hz separating the
                         4 bands (low, low-mid, high-mid, high).
                         Default: ``(200.0, 1000.0, 5000.0)``.
        thresholds_db: Per-band threshold in dB.
                       Default: ``(-20.0, -18.0, -16.0, -14.0)``.
        ratios: Per-band compression ratio.
                Default: ``(4.0, 3.0, 3.0, 2.0)``.
        attack_ms: Per-band attack time in milliseconds.
                   Default: ``(10.0, 8.0, 5.0, 3.0)``.
        release_ms: Per-band release time in milliseconds.
                    Default: ``(100.0, 80.0, 60.0, 50.0)``.
        makeup_gain_db: Per-band makeup gain in dB.
                        Default: ``(0.0, 0.0, 0.0, 0.0)``.
    """

    crossover_freqs: tuple[float, float, float] = (200.0, 1000.0, 5000.0)
    thresholds_db: tuple[float, float, float, float] = (-20.0, -18.0, -16.0, -14.0)
    ratios: tuple[float, float, float, float] = (4.0, 3.0, 3.0, 2.0)
    attack_ms: tuple[float, float, float, float] = (10.0, 8.0, 5.0, 3.0)
    release_ms: tuple[float, float, float, float] = (100.0, 80.0, 60.0, 50.0)
    makeup_gain_db: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def apply(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply multiband compression to audio samples.

        Args:
            samples: Audio samples, shape ``(n_samples,)`` for mono or
                     ``(n_samples, channels)`` for multi-channel.
                     Values in [-1.0, 1.0].
            sample_rate: Sample rate in Hz.

        Returns:
            Compressed audio samples with same shape and dtype.
        """
        if len(samples) == 0:
            return samples

        # Work in 2D
        was_1d = samples.ndim == 1
        if was_1d:
            work = samples[:, np.newaxis].astype(np.float64)
        else:
            work = samples.astype(np.float64)

        # Split into 4 bands using Butterworth-style biquad filters
        bands = self._split_bands(work, sample_rate)

        # Compress each band
        compressed: list[np.ndarray] = []
        for i, band in enumerate(bands):
            c = self._compress_band(
                band,
                sample_rate,
                self.thresholds_db[i],
                self.ratios[i],
                self.attack_ms[i],
                self.release_ms[i],
                self.makeup_gain_db[i],
            )
            compressed.append(c)

        # Recombine bands
        combined: np.ndarray = np.sum(compressed, axis=0)

        if was_1d:
            combined = combined[:, 0]

        out: np.ndarray = combined.astype(samples.dtype)
        return out

    def _split_bands(self, samples: np.ndarray, sample_rate: int) -> list[np.ndarray]:
        """Split audio into 4 frequency bands using cascaded biquad filters.

        Args:
            samples: Audio samples (n_samples, channels).
            sample_rate: Sample rate in Hz.

        Returns:
            List of 4 band arrays.
        """
        f1, f2, f3 = self.crossover_freqs

        # Band 0: low-pass at f1
        band0 = self._biquad_lowpass(samples, f1, sample_rate)
        # Band 1: high-pass at f1, low-pass at f2
        hp1 = self._biquad_highpass(samples, f1, sample_rate)
        band1 = self._biquad_lowpass(hp1, f2, sample_rate)
        # Band 2: high-pass at f2, low-pass at f3
        hp2 = self._biquad_highpass(samples, f2, sample_rate)
        band2 = self._biquad_lowpass(hp2, f3, sample_rate)
        # Band 3: high-pass at f3
        band3 = self._biquad_highpass(samples, f3, sample_rate)

        return [band0, band1, band2, band3]

    @staticmethod
    def _biquad_lowpass(samples: np.ndarray, cutoff: float, sample_rate: int) -> np.ndarray:
        """Apply a 2nd-order Butterworth low-pass biquad filter.

        Args:
            samples: Input samples (n_samples, channels).
            cutoff: Cutoff frequency in Hz.
            sample_rate: Sample rate in Hz.

        Returns:
            Filtered samples.
        """
        w0 = 2.0 * np.pi * cutoff / sample_rate
        alpha = np.sin(w0) / (2.0 * np.sqrt(2.0))  # Q = sqrt(2)/2 for Butterworth
        cos_w0 = np.cos(w0)

        b0 = (1.0 - cos_w0) / 2.0
        b1 = 1.0 - cos_w0
        b2 = b0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return MultibandCompressor._apply_biquad(
            samples, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
        )

    @staticmethod
    def _biquad_highpass(samples: np.ndarray, cutoff: float, sample_rate: int) -> np.ndarray:
        """Apply a 2nd-order Butterworth high-pass biquad filter.

        Args:
            samples: Input samples (n_samples, channels).
            cutoff: Cutoff frequency in Hz.
            sample_rate: Sample rate in Hz.

        Returns:
            Filtered samples.
        """
        w0 = 2.0 * np.pi * cutoff / sample_rate
        alpha = np.sin(w0) / (2.0 * np.sqrt(2.0))
        cos_w0 = np.cos(w0)

        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = b0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return MultibandCompressor._apply_biquad(
            samples, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
        )

    @staticmethod
    def _apply_biquad(
        samples: np.ndarray,
        b0: float,
        b1: float,
        b2: float,
        a1: float,
        a2: float,
    ) -> np.ndarray:
        """Apply a biquad filter to multi-channel samples.

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

    @staticmethod
    def _compress_band(
        band: np.ndarray,
        sample_rate: int,
        threshold_db: float,
        ratio: float,
        attack_ms: float,
        release_ms: float,
        makeup_db: float,
    ) -> np.ndarray:
        """Apply single-band compression with envelope follower.

        Args:
            band: Audio band samples (n_samples, channels).
            sample_rate: Sample rate in Hz.
            threshold_db: Threshold in dB.
            ratio: Compression ratio.
            attack_ms: Attack time in ms.
            release_ms: Release time in ms.
            makeup_db: Makeup gain in dB.

        Returns:
            Compressed band samples.
        """
        # Compute RMS envelope across channels
        rms = np.sqrt(np.mean(band**2, axis=1) + 1e-10)
        rms_db = 20.0 * np.log10(rms + 1e-10)

        # Compute gain reduction
        over = rms_db - threshold_db
        over = np.maximum(over, 0.0)
        gain_reduction_db = over * (1.0 - 1.0 / ratio)

        # Smooth with envelope follower
        attack_coeff = np.exp(-1.0 / (attack_ms * 0.001 * sample_rate))
        release_coeff = np.exp(-1.0 / (release_ms * 0.001 * sample_rate))

        smoothed = np.zeros_like(gain_reduction_db)
        prev = 0.0
        for i in range(len(gain_reduction_db)):
            if gain_reduction_db[i] > prev:
                prev = attack_coeff * prev + (1.0 - attack_coeff) * gain_reduction_db[i]
            else:
                prev = release_coeff * prev + (1.0 - release_coeff) * gain_reduction_db[i]
            smoothed[i] = prev

        # Apply gain
        gain = 10.0 ** ((-smoothed + makeup_db) / 20.0)
        result: np.ndarray = band * gain[:, np.newaxis]
        return result


def audio_crossfade(
    clip_a: np.ndarray,
    clip_b: np.ndarray,
    crossfade_samples: int,
    curve: CrossfadeType = "linear",
) -> np.ndarray:
    """Crossfade between two audio clips at the boundary.

    Overlaps the tail of ``clip_a`` with the head of ``clip_b`` for the
    specified number of samples, blending with the chosen curve.

    Args:
        clip_a: First audio clip samples, shape ``(n, channels)`` or
                ``(n,)`` for mono.
        clip_b: Second audio clip samples, same channel count as clip_a.
        crossfade_samples: Number of samples over which to crossfade.
        curve: Crossfade curve type:
            - ``"linear"``: Linear crossfade (gain ramps linearly).
            - ``"equal_power"``: Equal-power crossfade (constant loudness
              through the transition).
            - ``"s_curve"``: Smooth S-curve (slow start/end, fast middle).

    Returns:
        Concatenated audio array with crossfade applied.

    Raises:
        ValueError: If crossfade_samples exceeds either clip length,
                    or channel counts don't match.
    """
    if clip_a.ndim != clip_b.ndim:
        msg = f"clip_a ndim ({clip_a.ndim}) must match clip_b ndim ({clip_b.ndim})"
        raise ValueError(msg)

    if clip_a.ndim == 2 and clip_b.ndim == 2 and clip_a.shape[1] != clip_b.shape[1]:
        msg = f"Channel count mismatch: clip_a has {clip_a.shape[1]}, clip_b has {clip_b.shape[1]}"
        raise ValueError(msg)

    len_a = len(clip_a)
    len_b = len(clip_b)

    if crossfade_samples <= 0:
        # No crossfade — just concatenate
        return np.concatenate([clip_a, clip_b])

    if crossfade_samples > len_a:
        msg = f"crossfade_samples ({crossfade_samples}) exceeds clip_a length ({len_a})"
        raise ValueError(msg)
    if crossfade_samples > len_b:
        msg = f"crossfade_samples ({crossfade_samples}) exceeds clip_b length ({len_b})"
        raise ValueError(msg)

    # Build fade curves
    t = np.linspace(0.0, 1.0, crossfade_samples, dtype=np.float64)

    if curve == "equal_power":
        fade_out = np.cos(t * np.pi / 2.0)
        fade_in = np.sin(t * np.pi / 2.0)
    elif curve == "s_curve":
        # Smoothstep: 3t² - 2t³
        s = t * t * (3.0 - 2.0 * t)
        fade_out = 1.0 - s
        fade_in = s
    else:  # linear
        fade_out = 1.0 - t
        fade_in = t

    # Reshape for broadcasting with multi-channel audio
    if clip_a.ndim == 2:
        fade_out = fade_out[:, np.newaxis]
        fade_in = fade_in[:, np.newaxis]

    # Non-overlapping segments
    head_a = clip_a[: len_a - crossfade_samples]
    tail_a = clip_a[len_a - crossfade_samples :]
    head_b = clip_b[:crossfade_samples]
    tail_b = clip_b[crossfade_samples:]

    # Crossfaded overlap
    overlap = tail_a * fade_out + head_b * fade_in

    result: np.ndarray = np.concatenate([head_a, overlap, tail_b])
    logger.debug(
        "audio_crossfade_applied",
        curve=curve,
        crossfade_samples=crossfade_samples,
        result_length=len(result),
    )
    return result
