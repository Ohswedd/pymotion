"""Tests for color science — ACES, HDR, color matching, scopes."""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.color_science import (
    HDR10_PRESET,
    HLG_PRESET,
    ColorMatch,
    HistogramClip,
    HSLSecondary,
    ParadeScopeClip,
    VectorscopeClip,
    WaveformScopeClip,
    _hlg_oetf,
    _linear_to_srgb,
    _pq_eotf_inv,
    _srgb_to_linear,
    aces_to_srgb,
    srgb_to_aces,
)


def _ctx(w: int = 64, h: int = 64, fps: int = 30) -> RenderContext:
    return RenderContext(
        frame=0,
        fps=fps,
        resolution=Resolution(width=w, height=h),
        time_range=TimeRange(start=0, end=fps),
        local_frame=0,
        progress=0.0,
    )


def _solid_frame(r: int, g: int, b: int, w: int = 16, h: int = 16) -> np.ndarray:
    """Create a solid BGRA frame."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[:, :, 0] = b
    frame[:, :, 1] = g
    frame[:, :, 2] = r
    frame[:, :, 3] = 255
    return frame


class TestSRGBLinearConversion:
    def test_roundtrip(self) -> None:
        vals = np.array([0.0, 0.01, 0.04045, 0.5, 1.0])
        linear = _srgb_to_linear(vals)
        back = _linear_to_srgb(linear)
        np.testing.assert_allclose(back, vals, atol=1e-6)

    def test_black_stays_black(self) -> None:
        result = _srgb_to_linear(np.array([0.0]))
        assert result[0] == 0.0

    def test_white_stays_white(self) -> None:
        result = _srgb_to_linear(np.array([1.0]))
        np.testing.assert_allclose(result[0], 1.0, atol=1e-6)

    def test_linear_to_srgb_clips(self) -> None:
        result = _linear_to_srgb(np.array([-0.1, 1.5]))
        assert result[0] >= 0.0
        assert result[1] <= 1.0


class TestACESConversion:
    def test_srgb_to_aces_shape(self) -> None:
        frame = _solid_frame(128, 128, 128)
        aces = srgb_to_aces(frame)
        assert aces.shape == (16, 16, 3)
        assert aces.dtype == np.float64

    def test_black_to_aces(self) -> None:
        frame = _solid_frame(0, 0, 0)
        aces = srgb_to_aces(frame)
        np.testing.assert_allclose(aces, 0.0, atol=1e-6)

    def test_aces_roundtrip(self) -> None:
        frame = _solid_frame(100, 150, 200)
        aces = srgb_to_aces(frame)
        back = aces_to_srgb(aces)
        assert back.shape == (16, 16, 4)
        assert back.dtype == np.uint8
        assert back[:, :, 3].min() == 255  # Alpha preserved

    def test_aces_to_srgb_output_range(self) -> None:
        frame = _solid_frame(255, 255, 255)
        aces = srgb_to_aces(frame)
        back = aces_to_srgb(aces)
        # All values should be valid uint8
        assert back.min() >= 0
        assert back.max() <= 255


class TestHDRTransferFunctions:
    def test_pq_zero(self) -> None:
        result = _pq_eotf_inv(np.array([0.0]))
        np.testing.assert_allclose(result[0], 0.0, atol=1e-6)

    def test_pq_range(self) -> None:
        vals = np.linspace(0, 1, 11)
        result = _pq_eotf_inv(vals)
        assert result.min() >= 0.0
        assert result.max() <= 1.0
        # Should be monotonically non-decreasing
        assert np.all(np.diff(result) >= -1e-10)

    def test_hlg_zero(self) -> None:
        result = _hlg_oetf(np.array([0.0]))
        np.testing.assert_allclose(result[0], 0.0, atol=1e-6)

    def test_hlg_range(self) -> None:
        vals = np.linspace(0, 1, 11)
        result = _hlg_oetf(vals)
        assert result.min() >= 0.0
        assert result.max() <= 1.0 + 1e-6
        # Monotonically non-decreasing
        assert np.all(np.diff(result) >= -1e-10)

    def test_hdr10_preset(self) -> None:
        assert HDR10_PRESET["transfer"] == "pq"
        assert HDR10_PRESET["primaries"] == "bt2020"

    def test_hlg_preset(self) -> None:
        assert HLG_PRESET["transfer"] == "hlg"


class TestColorMatch:
    def test_no_reference_passthrough(self) -> None:
        effect = ColorMatch()
        frame = _solid_frame(128, 128, 128)
        result = effect.apply(frame, _ctx())
        np.testing.assert_array_equal(result, frame)

    def test_match_shifts_color(self) -> None:
        src = _solid_frame(100, 100, 100, w=32, h=32)
        ref = _solid_frame(200, 50, 50, w=32, h=32)
        effect = ColorMatch(reference_frame=ref)
        result = effect.apply(src, _ctx())
        assert result.shape == src.shape
        assert result.dtype == np.uint8
        # Red channel should shift toward reference
        assert result[:, :, 2].mean() != src[:, :, 2].mean()

    def test_alpha_preserved(self) -> None:
        src = _solid_frame(100, 100, 100)
        src[:, :, 3] = 200
        ref = _solid_frame(200, 200, 200)
        effect = ColorMatch(reference_frame=ref)
        result = effect.apply(src, _ctx())
        np.testing.assert_array_equal(result[:, :, 3], 200)


class TestHSLSecondary:
    def test_identity(self) -> None:
        """No adjustments = approximately unchanged."""
        effect = HSLSecondary()
        frame = _solid_frame(128, 64, 32)
        result = effect.apply(frame, _ctx())
        # Allow ±1 for float rounding through HSL conversion
        np.testing.assert_allclose(
            result[:, :, :3].astype(float),
            frame[:, :, :3].astype(float),
            atol=2,
        )

    def test_hue_shift(self) -> None:
        effect = HSLSecondary(
            hue_range=(0.0, 360.0),
            hue_shift=180.0,
        )
        frame = _solid_frame(255, 0, 0)  # Pure red
        result = effect.apply(frame, _ctx())
        # Should change significantly
        assert not np.array_equal(result[:, :, :3], frame[:, :, :3])

    def test_narrow_range_selection(self) -> None:
        """Only affects pixels in the target hue range."""
        # Red-only frame
        frame = _solid_frame(255, 0, 0)
        # Only select green hue (120 degrees) — red should be unaffected
        effect = HSLSecondary(
            hue_range=(100.0, 140.0),
            saturation_scale=0.0,
        )
        result = effect.apply(frame, _ctx())
        # Allow ±2 for float rounding through HSL conversion
        np.testing.assert_allclose(
            result[:, :, :3].astype(float),
            frame[:, :, :3].astype(float),
            atol=2,
        )

    def test_wrapping_hue_range(self) -> None:
        """Hue range wrapping around 360/0 boundary."""
        effect = HSLSecondary(
            hue_range=(350.0, 10.0),  # Wraps around
            saturation_scale=0.5,
        )
        frame = _solid_frame(255, 0, 0)  # Red ≈ 0°
        result = effect.apply(frame, _ctx())
        assert result.dtype == np.uint8

    def test_alpha_preserved(self) -> None:
        frame = _solid_frame(200, 100, 50)
        frame[:, :, 3] = 180
        effect = HSLSecondary(hue_shift=90.0)
        result = effect.apply(frame, _ctx())
        np.testing.assert_array_equal(result[:, :, 3], 180)

    def test_rgb_to_hsl_roundtrip(self) -> None:
        rgb = np.random.default_rng(42).random((8, 8, 3))
        hsl = HSLSecondary._rgb_to_hsl(rgb)
        back = HSLSecondary._hsl_to_rgb(hsl)
        np.testing.assert_allclose(back, rgb, atol=1e-10)


class TestWaveformScopeClip:
    def test_empty_source(self) -> None:
        clip = WaveformScopeClip()
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)
        assert frame.dtype == np.uint8

    def test_renders_with_source(self) -> None:
        src = _solid_frame(128, 128, 128, w=32, h=32)
        clip = WaveformScopeClip(source_frame=src)
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)
        # Should have some non-black pixels (the trace)
        assert frame[:, :, 1].max() > 0  # Green channel from trace


class TestVectorscopeClip:
    def test_empty_source(self) -> None:
        clip = VectorscopeClip()
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)

    def test_renders_with_source(self) -> None:
        src = _solid_frame(200, 50, 50, w=32, h=32)
        clip = VectorscopeClip(source_frame=src)
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)


class TestHistogramClip:
    def test_empty_source(self) -> None:
        clip = HistogramClip()
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)

    def test_rgb_channels(self) -> None:
        src = _solid_frame(255, 128, 64, w=32, h=32)
        clip = HistogramClip(source_frame=src, channels="rgb")
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)

    def test_luma_channel(self) -> None:
        src = _solid_frame(128, 128, 128, w=32, h=32)
        clip = HistogramClip(source_frame=src, channels="luma")
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)

    def test_single_channel(self) -> None:
        src = _solid_frame(200, 100, 50, w=32, h=32)
        clip = HistogramClip(source_frame=src, channels="r")
        frame = clip.render_frame(_ctx(w=64, h=64))
        assert frame.shape == (64, 64, 4)


class TestParadeScopeClip:
    def test_empty_source(self) -> None:
        clip = ParadeScopeClip()
        frame = clip.render_frame(_ctx(w=96, h=64))
        assert frame.shape == (64, 96, 4)

    def test_renders_with_source(self) -> None:
        src = _solid_frame(200, 100, 50, w=32, h=32)
        clip = ParadeScopeClip(source_frame=src)
        frame = clip.render_frame(_ctx(w=96, h=64))
        assert frame.shape == (64, 96, 4)
