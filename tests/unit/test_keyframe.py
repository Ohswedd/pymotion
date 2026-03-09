"""Unit tests for pymotion.animation.keyframe — Keyframe, KeyframeTrack."""

from __future__ import annotations

import pytest

from pymotion.animation.keyframe import Keyframe, KeyframeTrack
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2


class TestKeyframe:
    """Test Keyframe dataclass."""

    def test_create(self) -> None:
        kf = Keyframe(frame=0, value=0.0)
        assert kf.frame == 0
        assert kf.value == 0.0
        assert kf.easing == "linear"

    def test_with_easing(self) -> None:
        kf = Keyframe(frame=10, value=1.0, easing="ease_in_quad")
        assert kf.easing == "ease_in_quad"


class TestKeyframeTrack:
    """Test KeyframeTrack interpolation."""

    def test_empty_track_raises(self) -> None:
        track = KeyframeTrack()
        with pytest.raises(ValueError, match="no keyframes"):
            track.value_at(0)

    def test_before_first_keyframe(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=10, value=1.0),
            ]
        )
        assert track.value_at(0) == 1.0

    def test_after_last_keyframe(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=10, value=1.0),
            ]
        )
        assert track.value_at(20) == 1.0

    def test_linear_interpolation_midpoint(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=10, value=10.0),
            ]
        )
        result = track.value_at(5)
        assert isinstance(result, float)
        assert abs(result - 5.0) < 0.01

    def test_at_exact_keyframe(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=10, value=10.0),
            ]
        )
        result = track.value_at(0)
        assert result == 0.0
        result = track.value_at(10)
        assert result == 10.0

    def test_eased_interpolation(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0, easing="ease_in_quad"),
                Keyframe(frame=10, value=10.0),
            ]
        )
        result = track.value_at(5)
        assert isinstance(result, float)
        # ease_in_quad(0.5) = 0.25, so value should be 2.5
        assert abs(result - 2.5) < 0.01

    def test_color_interpolation(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=Color(0.0, 0.0, 0.0)),
                Keyframe(frame=10, value=Color(1.0, 1.0, 1.0)),
            ]
        )
        result = track.value_at(5)
        assert isinstance(result, Color)
        # OKLCH interpolation: perceptually uniform midpoint differs from linear 0.5
        # The midpoint between black and white in OKLCH lands around 0.39 in sRGB
        assert 0.0 < result.r < 1.0
        assert abs(result.r - result.g) < 0.01  # achromatic stays neutral

    def test_vec2_interpolation(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=Vec2(0.0, 0.0)),
                Keyframe(frame=10, value=Vec2(10.0, 20.0)),
            ]
        )
        result = track.value_at(5)
        assert isinstance(result, Vec2)
        assert abs(result.x - 5.0) < 0.01
        assert abs(result.y - 10.0) < 0.01

    def test_add_keyframe(self) -> None:
        track = KeyframeTrack()
        track.add(Keyframe(frame=10, value=1.0))
        track.add(Keyframe(frame=0, value=0.0))
        # Should be sorted
        assert track.keyframes[0].frame == 0
        assert track.keyframes[1].frame == 10

    def test_multiple_segments(self) -> None:
        track = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=10, value=10.0),
                Keyframe(frame=20, value=0.0),
            ]
        )
        result = track.value_at(15)
        assert isinstance(result, float)
        assert abs(result - 5.0) < 0.01
