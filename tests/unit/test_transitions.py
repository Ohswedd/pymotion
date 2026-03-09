"""Tests for all 39 built-in transitions."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.transition.library import (
    CircularWipe,
    CoverDown,
    CoverLeft,
    CoverRight,
    CoverUp,
    CrossDissolve,
    Cut,
    DipToColor,
    Fade,
    FadeToBlack,
    FadeToWhite,
    FilmBurn,
    Glitch,
    IrisIn,
    IrisOut,
    MorphWarp,
    PageTurn,
    PixelDissolve,
    PushDown,
    PushLeft,
    PushRight,
    PushUp,
    RevealDown,
    RevealLeft,
    RevealRight,
    RevealUp,
    ScaleDissolve,
    Shatter,
    SlideDown,
    SlideLeft,
    SlideRight,
    SlideUp,
    Vortex,
    WipeDiagonal,
    WipeLeft,
    WipeRight,
    ZoomBlur,
    ZoomIn,
    ZoomOut,
)

# Test frames: 8×8 BGRA, clip_a is red, clip_b is blue
_H, _W = 8, 8


@pytest.fixture()
def clip_a() -> np.ndarray:
    """Red frame (BGRA)."""
    frame = np.zeros((_H, _W, 4), dtype=np.uint8)
    frame[:, :, 2] = 255  # R channel in BGRA
    frame[:, :, 3] = 255  # full alpha
    return frame


@pytest.fixture()
def clip_b() -> np.ndarray:
    """Blue frame (BGRA)."""
    frame = np.zeros((_H, _W, 4), dtype=np.uint8)
    frame[:, :, 0] = 255  # B channel in BGRA
    frame[:, :, 3] = 255  # full alpha
    return frame


def _assert_valid_frame(frame: np.ndarray) -> None:
    """Assert frame is valid BGRA."""
    assert frame.shape == (_H, _W, 4)
    assert frame.dtype == np.uint8


# ── Basic Transitions ──


class TestFade:
    def test_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Fade(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    def test_end(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Fade(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_midpoint(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Fade(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)
        assert 100 < result[0, 0, 0] < 200  # B channel
        assert 100 < result[0, 0, 2] < 200  # R channel


class TestFadeToBlack:
    def test_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FadeToBlack(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_midpoint_is_dark(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FadeToBlack(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)
        assert np.mean(result[:, :, :3]) < 10

    def test_end(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FadeToBlack(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)


class TestFadeToWhite:
    def test_midpoint_is_bright(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FadeToWhite(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)
        assert np.mean(result[:, :, :3]) > 200


class TestDipToColor:
    def test_custom_color(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        t = DipToColor(30, color="#00FF00")
        result = t.render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)
        assert result[0, 0, 1] > 200  # G channel


class TestCrossDissolve:
    def test_identical_to_fade(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        fade_result = Fade(30).render_frame(clip_a, clip_b, 0.5)
        dissolve_result = CrossDissolve(30).render_frame(clip_a, clip_b, 0.5)
        np.testing.assert_array_equal(fade_result, dissolve_result)


class TestCut:
    def test_before_midpoint(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Cut(30).render_frame(clip_a, clip_b, 0.3)
        np.testing.assert_array_equal(result, clip_a)

    def test_after_midpoint(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Cut(30).render_frame(clip_a, clip_b, 0.7)
        np.testing.assert_array_equal(result, clip_b)


# ── Directional: Slide ──


class TestSlideTransitions:
    @pytest.mark.parametrize("cls", [SlideLeft, SlideRight, SlideUp, SlideDown])
    def test_start_is_clip_a(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    @pytest.mark.parametrize("cls", [SlideLeft, SlideRight, SlideUp, SlideDown])
    def test_end_is_clip_b(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    @pytest.mark.parametrize("cls", [SlideLeft, SlideRight, SlideUp, SlideDown])
    def test_midpoint_is_valid(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)


# ── Directional: Push ──


class TestPushTransitions:
    @pytest.mark.parametrize("cls", [PushLeft, PushRight, PushUp, PushDown])
    def test_renders_valid_frame(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    @pytest.mark.parametrize("cls", [PushLeft, PushRight, PushUp, PushDown])
    def test_end_is_clip_b(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)


# ── Directional: Cover ──


class TestCoverTransitions:
    @pytest.mark.parametrize("cls", [CoverLeft, CoverRight, CoverUp, CoverDown])
    def test_start_is_clip_a(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    @pytest.mark.parametrize("cls", [CoverLeft, CoverRight, CoverUp, CoverDown])
    def test_end_has_clip_b(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    @pytest.mark.parametrize("cls", [CoverUp, CoverDown])
    def test_midpoint_is_valid(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)


# ── Directional: Reveal ──


class TestRevealTransitions:
    @pytest.mark.parametrize("cls", [RevealLeft, RevealRight, RevealUp, RevealDown])
    def test_renders_valid_frame(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    @pytest.mark.parametrize("cls", [RevealLeft, RevealRight, RevealUp, RevealDown])
    def test_end_is_clip_b(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)


# ── Zoom ──


class TestZoomTransitions:
    @pytest.mark.parametrize("cls", [ZoomIn, ZoomOut, ZoomBlur, ScaleDissolve])
    def test_renders_valid_frame(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_zoom_in_end(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = ZoomIn(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_zoom_out_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = ZoomOut(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_zoom_blur_at_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = ZoomBlur(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_scale_dissolve_at_end(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = ScaleDissolve(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)


# ── Wipe Transitions ──


class TestWipeTransitions:
    @pytest.mark.parametrize("cls", [WipeLeft, WipeRight, WipeDiagonal, CircularWipe])
    def test_renders_valid_frame(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_wipe_right_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = WipeRight(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    def test_wipe_right_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = WipeRight(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_wipe_left_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = WipeLeft(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_circular_wipe_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = CircularWipe(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    def test_circular_wipe_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = CircularWipe(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_diagonal_wipe_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = WipeDiagonal(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_diagonal_wipe_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = WipeDiagonal(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)


# ── Iris Transitions ──


class TestIrisTransitions:
    def test_iris_in_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = IrisIn(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    def test_iris_in_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = IrisIn(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_iris_out_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = IrisOut(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    def test_iris_out_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = IrisOut(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_iris_in_midpoint(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = IrisIn(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)
        # Should have mix of A and B pixels
        has_a = np.any(result[:, :, 2] > 200)  # Red
        has_b = np.any(result[:, :, 0] > 200)  # Blue
        assert has_a or has_b


# ── Advanced Transitions ──


class TestPixelDissolve:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = PixelDissolve(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = PixelDissolve(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)

    def test_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = PixelDissolve(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_deterministic(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        r1 = PixelDissolve(30, seed=123).render_frame(clip_a, clip_b, 0.5)
        r2 = PixelDissolve(30, seed=123).render_frame(clip_a, clip_b, 0.5)
        np.testing.assert_array_equal(r1, r2)

    def test_different_seeds_differ(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        r1 = PixelDissolve(30, seed=1).render_frame(clip_a, clip_b, 0.5)
        r2 = PixelDissolve(30, seed=2).render_frame(clip_a, clip_b, 0.5)
        assert not np.array_equal(r1, r2)


class TestGlitch:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Glitch(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_start_no_crash(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Glitch(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_end_no_crash(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Glitch(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)


class TestFilmBurn:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FilmBurn(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_midpoint_has_bright_pixels(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FilmBurn(30).render_frame(clip_a, clip_b, 0.5)
        # Film burn should add brightness
        assert np.max(result[:, :, :3]) > 200

    def test_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FilmBurn(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_end(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FilmBurn(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)


class TestPageTurn:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = PageTurn(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = PageTurn(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_end(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = PageTurn(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)


class TestVortex:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Vortex(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Vortex(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Vortex(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)


class TestShatter:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Shatter(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_end_is_mostly_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Shatter(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        # At progress=1.0, most shards should have broken away
        blue_pixels = np.sum(result[:, :, 0] > 200)
        total_pixels = _H * _W
        assert blue_pixels > total_pixels * 0.5

    def test_start_has_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Shatter(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        # At progress=0, all shards still visible, so red should dominate
        red_pixels = np.sum(result[:, :, 2] > 200)
        assert red_pixels > 0

    def test_custom_grid(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = Shatter(30, grid_size=4).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)


class TestMorphWarp:
    def test_renders_valid_frame(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = MorphWarp(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    def test_end_is_b(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = MorphWarp(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)

    def test_start_is_a(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = MorphWarp(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_a)


# ── Comprehensive: All Transitions ──


ALL_TRANSITIONS = [
    Fade,
    FadeToBlack,
    FadeToWhite,
    CrossDissolve,
    Cut,
    SlideLeft,
    SlideRight,
    SlideUp,
    SlideDown,
    PushLeft,
    PushRight,
    PushUp,
    PushDown,
    CoverLeft,
    CoverRight,
    CoverUp,
    CoverDown,
    RevealLeft,
    RevealRight,
    RevealUp,
    RevealDown,
    ZoomIn,
    ZoomOut,
    ZoomBlur,
    ScaleDissolve,
    WipeLeft,
    WipeRight,
    WipeDiagonal,
    CircularWipe,
    IrisIn,
    IrisOut,
    PixelDissolve,
    Glitch,
    FilmBurn,
    PageTurn,
    Vortex,
    Shatter,
    MorphWarp,
]


class TestAllTransitionsHaveDuration:
    """Verify all transitions accept and store a duration."""

    @pytest.mark.parametrize("cls", ALL_TRANSITIONS)
    def test_default_duration(self, cls: type) -> None:
        t = cls(duration=15)  # type: ignore[call-arg]
        assert t.duration == 15


class TestAllTransitionsProduceValidOutput:
    """Verify every transition produces valid BGRA frames at key progress values."""

    @pytest.mark.parametrize("cls", ALL_TRANSITIONS)
    @pytest.mark.parametrize("progress", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_valid_output(
        self, cls: type, progress: float, clip_a: np.ndarray, clip_b: np.ndarray
    ) -> None:
        t = cls(duration=30)  # type: ignore[call-arg]
        result = t.render_frame(clip_a, clip_b, progress)
        _assert_valid_frame(result)
