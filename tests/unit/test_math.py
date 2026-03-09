"""Unit tests for pymotion.utils.math — Vec2, Vec3, clamp, lerp."""

from __future__ import annotations

from pymotion.utils.math import Vec2, Vec3, clamp, cubic_bezier_point, lerp, lerp_vec2, lerp_vec3


class TestVec2:
    """Test Vec2 operations."""

    def test_add(self) -> None:
        a = Vec2(1.0, 2.0)
        b = Vec2(3.0, 4.0)
        result = a + b
        assert result == Vec2(4.0, 6.0)

    def test_sub(self) -> None:
        a = Vec2(5.0, 3.0)
        b = Vec2(2.0, 1.0)
        result = a - b
        assert result == Vec2(3.0, 2.0)

    def test_mul(self) -> None:
        v = Vec2(2.0, 3.0)
        result = v * 2.0
        assert result == Vec2(4.0, 6.0)

    def test_rmul(self) -> None:
        v = Vec2(2.0, 3.0)
        result = 2.0 * v
        assert result == Vec2(4.0, 6.0)

    def test_length(self) -> None:
        v = Vec2(3.0, 4.0)
        assert abs(v.length() - 5.0) < 1e-10

    def test_as_tuple(self) -> None:
        v = Vec2(1.0, 2.0)
        assert v.as_tuple() == (1.0, 2.0)

    def test_frozen(self) -> None:
        v = Vec2(1.0, 2.0)
        try:
            v.x = 5.0  # type: ignore[misc]
            raise AssertionError("Should not be able to set attribute")
        except AttributeError:
            pass


class TestVec3:
    """Test Vec3 operations."""

    def test_add(self) -> None:
        a = Vec3(1.0, 2.0, 3.0)
        b = Vec3(4.0, 5.0, 6.0)
        result = a + b
        assert result == Vec3(5.0, 7.0, 9.0)

    def test_sub(self) -> None:
        a = Vec3(5.0, 3.0, 1.0)
        b = Vec3(2.0, 1.0, 0.0)
        result = a - b
        assert result == Vec3(3.0, 2.0, 1.0)

    def test_mul(self) -> None:
        v = Vec3(1.0, 2.0, 3.0)
        result = v * 3.0
        assert result == Vec3(3.0, 6.0, 9.0)

    def test_length(self) -> None:
        v = Vec3(1.0, 2.0, 2.0)
        assert abs(v.length() - 3.0) < 1e-10

    def test_as_tuple(self) -> None:
        v = Vec3(1.0, 2.0, 3.0)
        assert v.as_tuple() == (1.0, 2.0, 3.0)

    def test_neg(self) -> None:
        v = Vec3(1.0, -2.0, 3.0)
        result = -v
        assert result == Vec3(-1.0, 2.0, -3.0)

    def test_normalize(self) -> None:
        v = Vec3(3.0, 0.0, 0.0)
        n = v.normalize()
        assert abs(n.x - 1.0) < 1e-10
        assert abs(n.y) < 1e-10
        assert abs(n.length() - 1.0) < 1e-10

    def test_normalize_zero_vector(self) -> None:
        v = Vec3(0.0, 0.0, 0.0)
        n = v.normalize()
        assert n == Vec3(0.0, 0.0, 0.0)

    def test_dot(self) -> None:
        a = Vec3(1.0, 2.0, 3.0)
        b = Vec3(4.0, 5.0, 6.0)
        assert abs(a.dot(b) - 32.0) < 1e-10

    def test_dot_perpendicular(self) -> None:
        a = Vec3(1.0, 0.0, 0.0)
        b = Vec3(0.0, 1.0, 0.0)
        assert abs(a.dot(b)) < 1e-10

    def test_cross(self) -> None:
        x = Vec3(1.0, 0.0, 0.0)
        y = Vec3(0.0, 1.0, 0.0)
        z = x.cross(y)
        assert abs(z.x) < 1e-10
        assert abs(z.y) < 1e-10
        assert abs(z.z - 1.0) < 1e-10

    def test_cross_anticommutative(self) -> None:
        a = Vec3(1.0, 2.0, 3.0)
        b = Vec3(4.0, 5.0, 6.0)
        ab = a.cross(b)
        ba = b.cross(a)
        assert abs(ab.x + ba.x) < 1e-10
        assert abs(ab.y + ba.y) < 1e-10
        assert abs(ab.z + ba.z) < 1e-10


class TestClamp:
    """Test clamp function."""

    def test_within_range(self) -> None:
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_min(self) -> None:
        assert clamp(-1.0, 0.0, 1.0) == 0.0

    def test_above_max(self) -> None:
        assert clamp(2.0, 0.0, 1.0) == 1.0

    def test_at_boundaries(self) -> None:
        assert clamp(0.0, 0.0, 1.0) == 0.0
        assert clamp(1.0, 0.0, 1.0) == 1.0


class TestLerp:
    """Test lerp function."""

    def test_at_zero(self) -> None:
        assert lerp(0.0, 10.0, 0.0) == 0.0

    def test_at_one(self) -> None:
        assert lerp(0.0, 10.0, 1.0) == 10.0

    def test_at_half(self) -> None:
        assert lerp(0.0, 10.0, 0.5) == 5.0

    def test_lerp_vec2(self) -> None:
        a = Vec2(0.0, 0.0)
        b = Vec2(10.0, 20.0)
        result = lerp_vec2(a, b, 0.5)
        assert result == Vec2(5.0, 10.0)

    def test_lerp_vec3(self) -> None:
        a = Vec3(0.0, 0.0, 0.0)
        b = Vec3(10.0, 20.0, 30.0)
        result = lerp_vec3(a, b, 0.5)
        assert result == Vec3(5.0, 10.0, 15.0)


class TestBezier:
    """Test cubic Bezier evaluation."""

    def test_at_zero(self) -> None:
        result = cubic_bezier_point(0.0, 0.0, 1.0, 2.0, 3.0)
        assert abs(result - 0.0) < 1e-10

    def test_at_one(self) -> None:
        result = cubic_bezier_point(1.0, 0.0, 1.0, 2.0, 3.0)
        assert abs(result - 3.0) < 1e-10

    def test_linear(self) -> None:
        # Control points on a line: should be linear
        result = cubic_bezier_point(0.5, 0.0, 1.0, 2.0, 3.0)
        assert abs(result - 1.5) < 1e-10
