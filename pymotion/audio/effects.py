"""Audio DSP effects via pedalboard.

Provides audio effect wrappers around the pedalboard library for
common audio processing operations including EQ, dynamics,
reverb, delay, pitch shifting, noise reduction, and filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


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
