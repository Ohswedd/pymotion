"""Vector math, matrix operations, Bezier curves, clamp, and lerp.

Provides Vec2, Vec3 types and common math utilities used throughout PyMotion.
"""

from __future__ import annotations

import math as _math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    """Immutable 2D vector.

    Args:
        x: X component.
        y: Y component.
    """

    x: float
    y: float

    def __add__(self, other: Vec2) -> Vec2:
        """Add two vectors component-wise."""
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        """Subtract two vectors component-wise."""
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        """Multiply vector by a scalar."""
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        """Right-multiply vector by a scalar."""
        return Vec2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        """Return the length (magnitude) of the vector."""
        return _math.sqrt(self.x**2 + self.y**2)

    def as_tuple(self) -> tuple[float, float]:
        """Return as a plain tuple.

        Returns:
            Tuple of (x, y).
        """
        return (self.x, self.y)


@dataclass(frozen=True)
class Vec3:
    """Immutable 3D vector.

    Args:
        x: X component.
        y: Y component.
        z: Z component.
    """

    x: float
    y: float
    z: float

    def __add__(self, other: Vec3) -> Vec3:
        """Add two vectors component-wise."""
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        """Subtract two vectors component-wise."""
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        """Multiply vector by a scalar."""
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vec3:
        """Right-multiply vector by a scalar."""
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self) -> float:
        """Return the length (magnitude) of the vector."""
        return _math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def as_tuple(self) -> tuple[float, float, float]:
        """Return as a plain tuple.

        Returns:
            Tuple of (x, y, z).
        """
        return (self.x, self.y, self.z)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max.

    Args:
        value: The value to clamp.
        min_val: Minimum bound.
        max_val: Maximum bound.

    Returns:
        Clamped value.
    """
    return max(min_val, min(max_val, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between two values.

    Args:
        a: Start value.
        b: End value.
        t: Interpolation factor (0.0 = a, 1.0 = b).

    Returns:
        Interpolated value.
    """
    return a + (b - a) * t


def lerp_vec2(a: Vec2, b: Vec2, t: float) -> Vec2:
    """Linear interpolation between two Vec2 values.

    Args:
        a: Start vector.
        b: End vector.
        t: Interpolation factor (0.0 = a, 1.0 = b).

    Returns:
        Interpolated Vec2.
    """
    return Vec2(lerp(a.x, b.x, t), lerp(a.y, b.y, t))


def lerp_vec3(a: Vec3, b: Vec3, t: float) -> Vec3:
    """Linear interpolation between two Vec3 values.

    Args:
        a: Start vector.
        b: End vector.
        t: Interpolation factor (0.0 = a, 1.0 = b).

    Returns:
        Interpolated Vec3.
    """
    return Vec3(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))


def cubic_bezier_point(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Evaluate a cubic Bezier curve at parameter t.

    Args:
        t: Parameter value in [0.0, 1.0].
        p0: Start control point.
        p1: First intermediate control point.
        p2: Second intermediate control point.
        p3: End control point.

    Returns:
        Value at parameter t on the cubic Bezier curve.
    """
    u = 1.0 - t
    return u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3
