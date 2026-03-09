"""Type-aware interpolation for float, Color, Vec2, and Vec3 values.

Handles interpolation between different types used in animations.
Float values use numeric lerp, Color uses linear interpolation in
RGBA space, and Vec2/Vec3 use component-wise lerp.
"""

from __future__ import annotations

from pymotion.utils.color import Color
from pymotion.utils.math import Vec2, Vec3, lerp, lerp_vec2, lerp_vec3

AnimatableValue = float | Color | Vec2 | Vec3


def interpolate(a: AnimatableValue, b: AnimatableValue, t: float) -> AnimatableValue:
    """Interpolate between two values based on their types.

    Args:
        a: Start value.
        b: End value (must be same type as a).
        t: Interpolation factor (0.0 = a, 1.0 = b).

    Returns:
        Interpolated value of the same type.

    Raises:
        TypeError: If the values have different types or unsupported types.
    """
    if isinstance(a, float) and isinstance(b, float):
        return lerp(a, b, t)

    if isinstance(a, int) and isinstance(b, int):
        return lerp(float(a), float(b), t)

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return lerp(float(a), float(b), t)

    if isinstance(a, Color) and isinstance(b, Color):
        return _interpolate_color(a, b, t)

    if isinstance(a, Vec2) and isinstance(b, Vec2):
        return lerp_vec2(a, b, t)

    if isinstance(a, Vec3) and isinstance(b, Vec3):
        return lerp_vec3(a, b, t)

    msg = f"Cannot interpolate between {type(a).__name__} and {type(b).__name__}"
    raise TypeError(msg)


def _interpolate_color(a: Color, b: Color, t: float) -> Color:
    """Interpolate between two colors in RGBA space.

    Args:
        a: Start color.
        b: End color.
        t: Interpolation factor (0.0 = a, 1.0 = b).

    Returns:
        Interpolated Color.
    """
    return Color(
        r=lerp(a.r, b.r, t),
        g=lerp(a.g, b.g, t),
        b=lerp(a.b, b.b, t),
        a=lerp(a.a, b.a, t),
    )
