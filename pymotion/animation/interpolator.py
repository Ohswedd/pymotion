"""Type-aware interpolation for float, Color, Vec2, and Vec3 values.

Handles interpolation between different types used in animations.
Float values use numeric lerp, Color uses interpolation in OKLCH
color space (perceptually uniform), and Vec2/Vec3 use component-wise lerp.
"""

from __future__ import annotations

import math

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
        return _interpolate_color_oklch(a, b, t)

    if isinstance(a, Vec2) and isinstance(b, Vec2):
        return lerp_vec2(a, b, t)

    if isinstance(a, Vec3) and isinstance(b, Vec3):
        return lerp_vec3(a, b, t)

    msg = f"Cannot interpolate between {type(a).__name__} and {type(b).__name__}"
    raise TypeError(msg)


def _interpolate_color_oklch(a: Color, b: Color, t: float) -> Color:
    """Interpolate between two colors in OKLCH color space.

    OKLCH provides perceptually uniform interpolation, avoiding the
    muddy desaturated midpoints that occur in sRGB interpolation.

    Args:
        a: Start color.
        b: End color.
        t: Interpolation factor (0.0 = a, 1.0 = b).

    Returns:
        Interpolated Color.
    """
    l1, c1, h1 = _srgb_to_oklch(a.r, a.g, a.b)
    l2, c2, h2 = _srgb_to_oklch(b.r, b.g, b.b)

    # Handle hue interpolation via shortest arc
    if c1 < 1e-8:
        h1 = h2  # achromatic, use target hue
    if c2 < 1e-8:
        h2 = h1  # achromatic, use source hue

    dh = h2 - h1
    if dh > 180.0:
        dh -= 360.0
    elif dh < -180.0:
        dh += 360.0

    l_interp = lerp(l1, l2, t)
    c_interp = lerp(c1, c2, t)
    h_interp = h1 + dh * t

    r, g, bl = _oklch_to_srgb(l_interp, c_interp, h_interp)
    alpha = lerp(a.a, b.a, t)

    return Color(
        r=max(0.0, min(1.0, r)),
        g=max(0.0, min(1.0, g)),
        b=max(0.0, min(1.0, bl)),
        a=max(0.0, min(1.0, alpha)),
    )


def _srgb_to_linear(c: float) -> float:
    """Convert sRGB component to linear."""
    if c <= 0.04045:
        return c / 12.92
    return float(((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: float) -> float:
    """Convert linear component to sRGB."""
    if c <= 0.0031308:
        return c * 12.92
    return float(1.055 * (c ** (1.0 / 2.4)) - 0.055)


def _srgb_to_oklch(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert sRGB (0-1) to OKLCH (L, C, H).

    Args:
        r: Red (0-1).
        g: Green (0-1).
        b: Blue (0-1).

    Returns:
        Tuple of (L, C, H) where L is [0,1], C is [0,~0.4], H is degrees [0,360).
    """
    # sRGB → linear
    rl = _srgb_to_linear(r)
    gl = _srgb_to_linear(g)
    bl = _srgb_to_linear(b)

    # Linear sRGB → LMS (via OKLab matrix)
    l_ = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl
    m_ = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl
    s_ = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl

    # Cube root
    l_cr = math.copysign(abs(l_) ** (1 / 3), l_) if l_ != 0 else 0.0
    m_cr = math.copysign(abs(m_) ** (1 / 3), m_) if m_ != 0 else 0.0
    s_cr = math.copysign(abs(s_) ** (1 / 3), s_) if s_ != 0 else 0.0

    # LMS → OKLab
    ok_l = 0.2104542553 * l_cr + 0.7936177850 * m_cr - 0.0040720468 * s_cr
    ok_a = 1.9779984951 * l_cr - 2.4285922050 * m_cr + 0.4505937099 * s_cr
    ok_b = 0.0259040371 * l_cr + 0.7827717662 * m_cr - 0.8086757660 * s_cr

    # OKLab → OKLCH
    c = math.sqrt(ok_a * ok_a + ok_b * ok_b)
    h = math.degrees(math.atan2(ok_b, ok_a)) % 360.0

    return ok_l, c, h


def _oklch_to_srgb(lum: float, c: float, h: float) -> tuple[float, float, float]:
    """Convert OKLCH to sRGB (0-1).

    Args:
        lum: Lightness (0-1).
        c: Chroma.
        h: Hue in degrees.

    Returns:
        Tuple of (r, g, b) in sRGB space (0-1, may need clamping).
    """
    h_rad = math.radians(h)
    ok_a = c * math.cos(h_rad)
    ok_b = c * math.sin(h_rad)

    # OKLab → LMS (cube root)
    l_cr = lum + 0.3963377774 * ok_a + 0.2158037573 * ok_b
    m_cr = lum - 0.1055613458 * ok_a - 0.0638541728 * ok_b
    s_cr = lum - 0.0894841775 * ok_a - 1.2914855480 * ok_b

    # Undo cube root
    l_ = l_cr * l_cr * l_cr
    m_ = m_cr * m_cr * m_cr
    s_ = s_cr * s_cr * s_cr

    # LMS → linear sRGB
    rl = +4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    gl = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bl = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_

    # Linear → sRGB
    r = _linear_to_srgb(max(0.0, rl))
    g = _linear_to_srgb(max(0.0, gl))
    b = _linear_to_srgb(max(0.0, bl))

    return r, g, b
