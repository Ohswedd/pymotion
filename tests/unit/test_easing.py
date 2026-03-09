"""Unit tests for pymotion.animation.easing — easing functions."""

from __future__ import annotations

import pytest

from pymotion.animation.easing import (
    EASING_REGISTRY,
    ease_in_cubic,
    ease_in_out_quad,
    ease_in_quad,
    ease_out_cubic,
    ease_out_quad,
    get_easing,
    linear,
)


class TestEasingFunctions:
    """Test easing function correctness."""

    def test_linear_at_0(self) -> None:
        assert linear(0.0) == 0.0

    def test_linear_at_1(self) -> None:
        assert linear(1.0) == 1.0

    def test_linear_at_half(self) -> None:
        assert linear(0.5) == 0.5

    def test_ease_in_quad_at_0(self) -> None:
        assert ease_in_quad(0.0) == 0.0

    def test_ease_in_quad_at_1(self) -> None:
        assert ease_in_quad(1.0) == 1.0

    def test_ease_in_quad_convex(self) -> None:
        # ease_in should be below linear at midpoint
        assert ease_in_quad(0.5) < 0.5

    def test_ease_out_quad_at_0(self) -> None:
        assert ease_out_quad(0.0) == 0.0

    def test_ease_out_quad_at_1(self) -> None:
        assert ease_out_quad(1.0) == 1.0

    def test_ease_out_quad_concave(self) -> None:
        # ease_out should be above linear at midpoint
        assert ease_out_quad(0.5) > 0.5

    def test_ease_in_out_quad_endpoints(self) -> None:
        assert ease_in_out_quad(0.0) == 0.0
        assert ease_in_out_quad(1.0) == 1.0

    def test_ease_in_out_quad_midpoint(self) -> None:
        assert abs(ease_in_out_quad(0.5) - 0.5) < 1e-10

    def test_ease_in_cubic_endpoints(self) -> None:
        assert ease_in_cubic(0.0) == 0.0
        assert ease_in_cubic(1.0) == 1.0

    def test_ease_out_cubic_endpoints(self) -> None:
        assert ease_out_cubic(0.0) == 0.0
        assert abs(ease_out_cubic(1.0) - 1.0) < 1e-10


class TestEasingBoundaries:
    """Test that all easings have correct boundary values."""

    @pytest.mark.parametrize("name", list(EASING_REGISTRY.keys()))
    def test_all_start_at_zero(self, name: str) -> None:
        fn = get_easing(name)
        assert abs(fn(0.0)) < 1e-10, f"{name}(0.0) = {fn(0.0)}"

    @pytest.mark.parametrize("name", list(EASING_REGISTRY.keys()))
    def test_all_end_at_one(self, name: str) -> None:
        fn = get_easing(name)
        assert abs(fn(1.0) - 1.0) < 1e-10, f"{name}(1.0) = {fn(1.0)}"


class TestEasingRegistry:
    """Test the easing registry lookup."""

    def test_get_linear(self) -> None:
        fn = get_easing("linear")
        assert fn(0.5) == 0.5

    def test_get_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown easing"):
            get_easing("nonexistent")

    def test_registry_has_10_easings(self) -> None:
        assert len(EASING_REGISTRY) >= 10
