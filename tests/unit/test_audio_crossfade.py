"""Tests for audio crossfade functions."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.audio.effects import audio_crossfade


class TestAudioCrossfade:
    """Tests for audio_crossfade()."""

    def test_linear_crossfade_mono(self) -> None:
        """Linear crossfade between two mono clips."""
        a = np.ones(100, dtype=np.float64)
        b = np.ones(100, dtype=np.float64) * 0.5
        result = audio_crossfade(a, b, crossfade_samples=20, curve="linear")
        # Total length: 100 + 100 - 20 = 180
        assert len(result) == 180
        # Head of a (first 80 samples) unchanged
        np.testing.assert_allclose(result[:80], 1.0)
        # Tail of b (last 80 samples) unchanged
        np.testing.assert_allclose(result[100:], 0.5)

    def test_linear_crossfade_midpoint(self) -> None:
        """At midpoint, linear crossfade should average the two signals."""
        a = np.ones(100, dtype=np.float64) * 1.0
        b = np.ones(100, dtype=np.float64) * 0.0
        result = audio_crossfade(a, b, crossfade_samples=20, curve="linear")
        # Midpoint of the overlap region
        mid = result[90]  # sample 80 + 10 (midpoint of 20-sample fade)
        assert abs(mid - 0.5) < 0.05

    def test_equal_power_crossfade_mono(self) -> None:
        """Equal-power crossfade maintains constant loudness."""
        a = np.ones(100, dtype=np.float64)
        b = np.ones(100, dtype=np.float64)
        result = audio_crossfade(a, b, crossfade_samples=20, curve="equal_power")
        assert len(result) == 180
        # In the overlap region, fade_out² + fade_in² ≈ 1 (energy preserving)
        # So with both signals at 1.0: cos(t·π/2) + sin(t·π/2) ≈ sqrt(2) at mid
        overlap = result[80:100]
        # Should stay close to 1.0 (not dip like linear)
        assert overlap.min() >= 0.95

    def test_s_curve_crossfade_mono(self) -> None:
        """S-curve crossfade transitions smoothly."""
        a = np.ones(100, dtype=np.float64) * 1.0
        b = np.ones(100, dtype=np.float64) * 0.0
        result = audio_crossfade(a, b, crossfade_samples=40, curve="s_curve")
        assert len(result) == 160
        # Overlap region is result[60:100] (head_a=60 samples, overlap=40)
        # At midpoint of overlap: smoothstep(0.5) = 0.5
        overlap_start = 60
        mid_idx = overlap_start + 20
        assert abs(result[mid_idx] - 0.5) < 0.05
        # Near the start of fade: still close to 1.0 (slow start)
        assert result[overlap_start + 2] > 0.9
        # Near the end of fade: close to 0.0 (slow end)
        assert result[overlap_start + 38] < 0.1

    def test_stereo_crossfade(self) -> None:
        """Crossfade works with stereo (n, 2) arrays."""
        a = np.ones((100, 2), dtype=np.float64) * 0.8
        b = np.ones((100, 2), dtype=np.float64) * 0.2
        result = audio_crossfade(a, b, crossfade_samples=20, curve="linear")
        assert result.shape == (180, 2)
        # Head unchanged
        np.testing.assert_allclose(result[:80], 0.8)
        # Tail unchanged
        np.testing.assert_allclose(result[100:], 0.2)

    def test_multichannel_crossfade(self) -> None:
        """Crossfade works with 6-channel (5.1) audio."""
        a = np.ones((100, 6), dtype=np.float64) * 0.6
        b = np.ones((100, 6), dtype=np.float64) * 0.4
        result = audio_crossfade(a, b, crossfade_samples=10, curve="equal_power")
        assert result.shape == (190, 6)

    def test_zero_crossfade_samples(self) -> None:
        """Zero crossfade samples just concatenates."""
        a = np.ones(50, dtype=np.float64)
        b = np.ones(30, dtype=np.float64) * 0.5
        result = audio_crossfade(a, b, crossfade_samples=0)
        assert len(result) == 80
        np.testing.assert_allclose(result[:50], 1.0)
        np.testing.assert_allclose(result[50:], 0.5)

    def test_full_overlap_crossfade(self) -> None:
        """Crossfade can span the entire shorter clip."""
        a = np.ones(50, dtype=np.float64)
        b = np.ones(50, dtype=np.float64) * 0.5
        result = audio_crossfade(a, b, crossfade_samples=50, curve="linear")
        assert len(result) == 50  # Full overlap

    def test_crossfade_exceeds_clip_a_raises(self) -> None:
        """Crossfade longer than clip_a should raise."""
        a = np.ones(10, dtype=np.float64)
        b = np.ones(100, dtype=np.float64)
        with pytest.raises(ValueError, match="exceeds clip_a"):
            audio_crossfade(a, b, crossfade_samples=20)

    def test_crossfade_exceeds_clip_b_raises(self) -> None:
        """Crossfade longer than clip_b should raise."""
        a = np.ones(100, dtype=np.float64)
        b = np.ones(10, dtype=np.float64)
        with pytest.raises(ValueError, match="exceeds clip_b"):
            audio_crossfade(a, b, crossfade_samples=20)

    def test_ndim_mismatch_raises(self) -> None:
        """Mismatched ndim between clips should raise."""
        a = np.ones(100, dtype=np.float64)
        b = np.ones((100, 2), dtype=np.float64)
        with pytest.raises(ValueError, match="ndim"):
            audio_crossfade(a, b, crossfade_samples=10)

    def test_channel_count_mismatch_raises(self) -> None:
        """Different channel counts should raise."""
        a = np.ones((100, 2), dtype=np.float64)
        b = np.ones((100, 6), dtype=np.float64)
        with pytest.raises(ValueError, match="Channel count"):
            audio_crossfade(a, b, crossfade_samples=10)

    def test_all_curve_types_accepted(self) -> None:
        """All three curve types should work without error."""
        a = np.ones(50, dtype=np.float64)
        b = np.ones(50, dtype=np.float64)
        for curve in ("linear", "equal_power", "s_curve"):
            result = audio_crossfade(a, b, crossfade_samples=10, curve=curve)  # type: ignore[arg-type]
            assert len(result) == 90
