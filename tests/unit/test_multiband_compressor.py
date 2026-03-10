"""Tests for MultibandCompressor audio effect."""

from __future__ import annotations

import numpy as np

from pymotion.audio.effects import MultibandCompressor


class TestMultibandCompressor:
    """Tests for MultibandCompressor."""

    def test_default_init(self) -> None:
        """Default parameters are set correctly."""
        comp = MultibandCompressor()
        assert comp.crossover_freqs == (200.0, 1000.0, 5000.0)
        assert len(comp.thresholds_db) == 4
        assert len(comp.ratios) == 4
        assert len(comp.attack_ms) == 4
        assert len(comp.release_ms) == 4
        assert len(comp.makeup_gain_db) == 4

    def test_passthrough_silence(self) -> None:
        """Silent audio should remain silent."""
        comp = MultibandCompressor()
        samples = np.zeros((1000, 2), dtype=np.float64)
        result = comp.apply(samples, 48000)
        np.testing.assert_allclose(result, 0.0, atol=1e-10)

    def test_empty_input(self) -> None:
        """Empty input returns empty output."""
        comp = MultibandCompressor()
        samples = np.zeros((0, 2), dtype=np.float64)
        result = comp.apply(samples, 48000)
        assert len(result) == 0

    def test_output_shape_stereo(self) -> None:
        """Output shape matches input for stereo."""
        comp = MultibandCompressor()
        samples = np.random.default_rng(42).uniform(-0.5, 0.5, (4800, 2))
        result = comp.apply(samples, 48000)
        assert result.shape == samples.shape

    def test_output_shape_mono(self) -> None:
        """Output shape matches input for mono."""
        comp = MultibandCompressor()
        samples = np.random.default_rng(42).uniform(-0.5, 0.5, 4800)
        result = comp.apply(samples, 48000)
        assert result.shape == samples.shape

    def test_compression_reduces_peaks(self) -> None:
        """Loud signals above threshold should be attenuated."""
        comp = MultibandCompressor(
            thresholds_db=(-10.0, -10.0, -10.0, -10.0),
            ratios=(8.0, 8.0, 8.0, 8.0),
        )
        # Generate a loud sine wave
        t = np.arange(4800, dtype=np.float64) / 48000
        loud = np.sin(2 * np.pi * 440 * t) * 0.9  # ~-0.9 dB
        loud_stereo = np.column_stack([loud, loud])
        result = comp.apply(loud_stereo, 48000)
        # Peak should be lower than input
        assert np.max(np.abs(result)) < np.max(np.abs(loud_stereo))

    def test_quiet_signal_passes_through(self) -> None:
        """Quiet signals below threshold should be minimally affected."""
        comp = MultibandCompressor(
            thresholds_db=(-6.0, -6.0, -6.0, -6.0),
            ratios=(4.0, 4.0, 4.0, 4.0),
        )
        # Very quiet signal (well below all thresholds)
        t = np.arange(4800, dtype=np.float64) / 48000
        quiet = np.sin(2 * np.pi * 440 * t) * 0.01  # ~ -40 dB
        quiet_stereo = np.column_stack([quiet, quiet])
        result = comp.apply(quiet_stereo, 48000)
        # Should be close to the original (within tolerance for filter phase)
        rms_in = np.sqrt(np.mean(quiet_stereo**2))
        rms_out = np.sqrt(np.mean(result**2))
        assert abs(rms_out - rms_in) / rms_in < 0.3

    def test_custom_crossover_freqs(self) -> None:
        """Custom crossover frequencies are accepted and used."""
        comp = MultibandCompressor(crossover_freqs=(100.0, 500.0, 3000.0))
        samples = np.random.default_rng(42).uniform(-0.5, 0.5, (4800, 2))
        result = comp.apply(samples, 48000)
        assert result.shape == samples.shape

    def test_makeup_gain(self) -> None:
        """Makeup gain boosts the output level."""
        # No compression (very low thresholds won't trigger on quiet signal)
        comp_no_gain = MultibandCompressor(
            thresholds_db=(0.0, 0.0, 0.0, 0.0),
            ratios=(1.0, 1.0, 1.0, 1.0),
            makeup_gain_db=(0.0, 0.0, 0.0, 0.0),
        )
        comp_with_gain = MultibandCompressor(
            thresholds_db=(0.0, 0.0, 0.0, 0.0),
            ratios=(1.0, 1.0, 1.0, 1.0),
            makeup_gain_db=(6.0, 6.0, 6.0, 6.0),
        )
        t = np.arange(4800, dtype=np.float64) / 48000
        signal = np.sin(2 * np.pi * 440 * t) * 0.1
        stereo = np.column_stack([signal, signal])

        result_no = comp_no_gain.apply(stereo, 48000)
        result_gain = comp_with_gain.apply(stereo, 48000)

        rms_no = np.sqrt(np.mean(result_no**2))
        rms_gain = np.sqrt(np.mean(result_gain**2))
        # With 6dB makeup, output should be roughly 2x louder
        assert rms_gain > rms_no * 1.5

    def test_dtype_preserved(self) -> None:
        """Output dtype matches input dtype."""
        comp = MultibandCompressor()
        for dtype in [np.float32, np.float64]:
            samples = np.zeros((100, 2), dtype=dtype)
            result = comp.apply(samples, 48000)
            assert result.dtype == dtype

    def test_band_splitting_preserves_signal(self) -> None:
        """Splitting and recombining without compression preserves energy."""
        comp = MultibandCompressor(
            thresholds_db=(0.0, 0.0, 0.0, 0.0),  # High thresholds
            ratios=(1.0, 1.0, 1.0, 1.0),  # No compression
        )
        rng = np.random.default_rng(42)
        samples = rng.uniform(-0.3, 0.3, (4800, 2))
        result = comp.apply(samples, 48000)
        # RMS should be similar (filters will cause some small deviation)
        rms_in = np.sqrt(np.mean(samples**2))
        rms_out = np.sqrt(np.mean(result**2))
        assert abs(rms_out - rms_in) / rms_in < 0.5
