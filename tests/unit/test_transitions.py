"""Tests for all 20 built-in transitions."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.transition.library import (
    CoverLeft,
    CoverRight,
    CrossDissolve,
    Cut,
    DipToColor,
    Fade,
    FadeToBlack,
    FadeToWhite,
    PushDown,
    PushLeft,
    PushRight,
    PushUp,
    RevealLeft,
    RevealRight,
    SlideDown,
    SlideLeft,
    SlideRight,
    SlideUp,
    ZoomIn,
    ZoomOut,
)

# Test frames: 4×4 BGRA, clip_a is red, clip_b is blue
_H, _W = 4, 4


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
        # Midpoint should be between A and B
        assert 100 < result[0, 0, 0] < 200  # B channel
        assert 100 < result[0, 0, 2] < 200  # R channel


class TestFadeToBlack:
    def test_start(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FadeToBlack(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    def test_midpoint_is_dark(self, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = FadeToBlack(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)
        # At midpoint, should be fully black
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
        # At midpoint, should be the dip color (green)
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


class TestSlideTransitions:
    @pytest.mark.parametrize("cls", [SlideLeft, SlideRight, SlideUp, SlideDown])
    def test_start_is_clip_a(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)
        # At progress=0, should be mostly clip A
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


class TestCoverTransitions:
    @pytest.mark.parametrize("cls", [CoverLeft, CoverRight])
    def test_start_is_clip_a(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.0)
        _assert_valid_frame(result)

    @pytest.mark.parametrize("cls", [CoverLeft, CoverRight])
    def test_end_has_clip_b(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        # Should be clip B at the end
        np.testing.assert_array_equal(result, clip_b)


class TestRevealTransitions:
    @pytest.mark.parametrize("cls", [RevealLeft, RevealRight])
    def test_renders_valid_frame(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 0.5)
        _assert_valid_frame(result)

    @pytest.mark.parametrize("cls", [RevealLeft, RevealRight])
    def test_end_is_clip_b(self, cls: type, clip_a: np.ndarray, clip_b: np.ndarray) -> None:
        result = cls(30).render_frame(clip_a, clip_b, 1.0)
        _assert_valid_frame(result)
        np.testing.assert_array_equal(result, clip_b)


class TestZoomTransitions:
    @pytest.mark.parametrize("cls", [ZoomIn, ZoomOut])
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


class TestAllTransitionsHaveDuration:
    """Verify all transitions accept and store a duration."""

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
        RevealLeft,
        RevealRight,
        ZoomIn,
        ZoomOut,
    ]

    @pytest.mark.parametrize("cls", ALL_TRANSITIONS)
    def test_default_duration(self, cls: type) -> None:
        if cls == DipToColor:
            t = cls(30)  # type: ignore[call-arg]
        else:
            t = cls(duration=15)  # type: ignore[call-arg]
        assert t.duration == 15 or t.duration == 30
