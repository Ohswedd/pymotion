"""Tests for tone mapping functions in the color pipeline."""

from __future__ import annotations

import numpy as np

from pymotion.render.color_pipeline import (
    apply_color_pipeline,
    tone_map_aces,
    tone_map_filmic,
    tone_map_reinhard,
)


def _make_frame(value: int = 200) -> np.ndarray:
    """Create a test BGRA frame with a uniform color."""
    frame = np.full((48, 64, 4), value, dtype=np.uint8)
    frame[:, :, 3] = 255
    return frame


class TestToneMapACES:
    """Tests for ACES tone mapping."""

    def test_output_shape_and_dtype(self) -> None:
        """Output preserves shape and dtype."""
        frame = _make_frame()
        result = tone_map_aces(frame)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_preserves_alpha(self) -> None:
        """Alpha channel is unchanged."""
        frame = _make_frame()
        result = tone_map_aces(frame)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])

    def test_black_stays_black(self) -> None:
        """Pure black pixels remain black."""
        frame = _make_frame(0)
        result = tone_map_aces(frame)
        assert np.all(result[:, :, :3] == 0)

    def test_modifies_midtones(self) -> None:
        """ACES curve modifies mid-range values."""
        frame = _make_frame(128)
        result = tone_map_aces(frame)
        assert not np.array_equal(result[:, :, :3], frame[:, :, :3])


class TestToneMapReinhard:
    """Tests for Reinhard tone mapping."""

    def test_output_shape_and_dtype(self) -> None:
        frame = _make_frame()
        result = tone_map_reinhard(frame)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_preserves_alpha(self) -> None:
        frame = _make_frame()
        result = tone_map_reinhard(frame)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])

    def test_compresses_highlights(self) -> None:
        """Reinhard compresses bright values."""
        frame = _make_frame(200)
        result = tone_map_reinhard(frame)
        # Reinhard: x/(1+x) where x = 200/255 ≈ 0.784
        # Result ≈ 0.784/(1+0.784) ≈ 0.440 → ~112
        assert np.all(result[:, :, :3] < frame[:, :, :3])


class TestToneMapFilmic:
    """Tests for Hable/Uncharted 2 filmic tone mapping."""

    def test_output_shape_and_dtype(self) -> None:
        frame = _make_frame()
        result = tone_map_filmic(frame)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_preserves_alpha(self) -> None:
        frame = _make_frame()
        result = tone_map_filmic(frame)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])


class TestToneMapPipeline:
    """Tests for tone mapping via apply_color_pipeline."""

    def test_aces_via_pipeline(self) -> None:
        """ACES tone map applied through the pipeline."""
        frame = _make_frame(180)
        result = apply_color_pipeline(frame, tone_map="aces")
        direct = tone_map_aces(frame)
        np.testing.assert_array_equal(result, direct)

    def test_unknown_tone_map_passthrough(self) -> None:
        """Unknown tone map name logs warning and passes through."""
        frame = _make_frame(180)
        result = apply_color_pipeline(frame, tone_map="nonexistent")
        np.testing.assert_array_equal(result, frame)

    def test_none_tone_map_passthrough(self) -> None:
        """No tone map means no transformation."""
        frame = _make_frame(180)
        result = apply_color_pipeline(frame, tone_map=None)
        np.testing.assert_array_equal(result, frame)
