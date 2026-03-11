"""Tests for pymotion.design.motion — easing presets and duration constants."""

from __future__ import annotations

import pytest

from pymotion.design.motion import (
    ENTER,
    EXIT,
    FAST,
    INSTANT,
    NORMAL,
    SLOW,
    STAGGER,
    STATE_CHANGE,
    ease_in_out_quart,
    ease_in_quart,
    ease_out_quart,
    get_motion_easing,
    spring_bounce,
    spring_reveal,
    spring_ui,
)


class TestEasingFunctions:
    def test_ease_out_quart_endpoints(self) -> None:
        assert ease_out_quart(0.0) == 0.0
        assert ease_out_quart(1.0) == 1.0

    def test_ease_in_quart_endpoints(self) -> None:
        assert ease_in_quart(0.0) == 0.0
        assert ease_in_quart(1.0) == 1.0

    def test_ease_in_out_quart_endpoints(self) -> None:
        assert ease_in_out_quart(0.0) == 0.0
        assert ease_in_out_quart(1.0) == 1.0

    def test_ease_out_quart_fast_start(self) -> None:
        # ease_out should be > 0.5 at t=0.5 (fast start)
        assert ease_out_quart(0.5) > 0.5

    def test_ease_in_quart_slow_start(self) -> None:
        # ease_in should be < 0.5 at t=0.5 (slow start)
        assert ease_in_quart(0.5) < 0.5

    def test_ease_in_out_quart_symmetric(self) -> None:
        # At t=0.5, ease_in_out should be close to 0.5
        val = ease_in_out_quart(0.5)
        assert abs(val - 0.5) < 0.15

    def test_ease_out_quart_monotonic(self) -> None:
        prev = 0.0
        for i in range(1, 101):
            t = i / 100.0
            val = ease_out_quart(t)
            assert val >= prev - 1e-6
            prev = val


class TestSpringFunctions:
    def test_spring_ui_endpoints(self) -> None:
        assert spring_ui(0.0) == 0.0
        assert spring_ui(1.0) == 1.0

    def test_spring_reveal_endpoints(self) -> None:
        assert spring_reveal(0.0) == 0.0
        assert spring_reveal(1.0) == 1.0

    def test_spring_bounce_endpoints(self) -> None:
        assert spring_bounce(0.0) == 0.0
        assert spring_bounce(1.0) == 1.0

    def test_spring_ui_reaches_target(self) -> None:
        # At t=0.8 should be close to 1.0
        assert abs(spring_ui(0.8) - 1.0) < 0.1

    def test_spring_bounce_overshoots(self) -> None:
        # Spring bounce should overshoot at some point
        max_val = max(spring_bounce(i / 100.0) for i in range(101))
        assert max_val > 1.0

    def test_spring_reveal_settles(self) -> None:
        assert abs(spring_reveal(0.9) - 1.0) < 0.1


class TestDurationPresets:
    def test_instant_is_zero(self) -> None:
        assert INSTANT == 0

    def test_fast(self) -> None:
        assert FAST == 9

    def test_normal(self) -> None:
        assert NORMAL == 15

    def test_slow(self) -> None:
        assert SLOW == 24

    def test_stagger(self) -> None:
        assert STAGGER == 4

    def test_ordering(self) -> None:
        assert INSTANT < STAGGER < FAST < NORMAL < SLOW


class TestMotionPresets:
    def test_enter_preset(self) -> None:
        assert ENTER.duration == NORMAL
        assert ENTER.easing_name == "ease_out_quart"

    def test_exit_preset(self) -> None:
        assert EXIT.duration == FAST
        assert EXIT.easing_name == "ease_in_quart"

    def test_state_change_preset(self) -> None:
        assert STATE_CHANGE.duration == NORMAL
        assert STATE_CHANGE.easing_name == "ease_in_out_quart"

    def test_exit_faster_than_enter(self) -> None:
        assert EXIT.duration < ENTER.duration


class TestGetMotionEasing:
    def test_get_valid_easing(self) -> None:
        fn = get_motion_easing("ease_out_quart")
        assert callable(fn)

    def test_get_invalid_easing(self) -> None:
        with pytest.raises(ValueError, match="Unknown motion easing"):
            get_motion_easing("invalid")

    def test_all_named_easings(self) -> None:
        for name in (
            "ease_out_quart",
            "ease_in_quart",
            "ease_in_out_quart",
            "spring_ui",
            "spring_reveal",
            "spring_bounce",
        ):
            fn = get_motion_easing(name)
            assert callable(fn)
