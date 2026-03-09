"""Audio DSP effects — EQ, Compressor, Limiter via pedalboard.

Provides audio effect wrappers around the pedalboard library for
common audio processing operations.
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
