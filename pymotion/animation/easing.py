"""Easing functions for animation curves.

All easing functions are pure functions (t: float) -> float where t is in [0.0, 1.0].
Provides all 30 built-in easings plus spring(), cubic_bezier(), and steps() factories.
"""

from __future__ import annotations

import math
from collections.abc import Callable

EasingFn = Callable[[float], float]


def linear(t: float) -> float:
    """Linear easing — no acceleration.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        The same value t.
    """
    return t


# --- Quadratic ---


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in — accelerating from zero velocity.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out — decelerating to zero velocity.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return t * (2 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out — acceleration then deceleration.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t < 0.5:
        return 2 * t * t
    return -1 + (4 - 2 * t) * t


# --- Cubic ---


def ease_in_cubic(t: float) -> float:
    """Cubic ease-in — accelerating from zero velocity.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out — decelerating to zero velocity.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    u = t - 1
    return u * u * u + 1


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out — acceleration then deceleration.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t < 0.5:
        return 4 * t * t * t
    u = 2 * t - 2
    return (u * u * u + 2) / 2


# --- Quart ---


def ease_in_quart(t: float) -> float:
    """Quartic ease-in.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return t * t * t * t


def ease_out_quart(t: float) -> float:
    """Quartic ease-out.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    u = t - 1
    return 1 - u * u * u * u


# --- Quint ---


def ease_in_quint(t: float) -> float:
    """Quintic ease-in.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return t * t * t * t * t


def ease_out_quint(t: float) -> float:
    """Quintic ease-out.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    u = t - 1
    return u * u * u * u * u + 1


# --- Sine ---


def ease_in_sine(t: float) -> float:
    """Sinusoidal ease-in — accelerating from zero velocity.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return 1 - math.cos(t * math.pi / 2)


def ease_out_sine(t: float) -> float:
    """Sinusoidal ease-out — decelerating to zero velocity.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return math.sin(t * math.pi / 2)


def ease_in_out_sine(t: float) -> float:
    """Sinusoidal ease-in-out — acceleration then deceleration.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return -(math.cos(math.pi * t) - 1) / 2


# --- Expo ---


def ease_in_expo(t: float) -> float:
    """Exponential ease-in.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t == 0.0:
        return 0.0
    return math.pow(2, 10 * (t - 1))


def ease_out_expo(t: float) -> float:
    """Exponential ease-out.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t == 1.0:
        return 1.0
    return 1 - math.pow(2, -10 * t)


def ease_in_out_expo(t: float) -> float:
    """Exponential ease-in-out.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    if t < 0.5:
        return math.pow(2, 20 * t - 10) / 2
    return (2 - math.pow(2, -20 * t + 10)) / 2


# --- Circ ---


def ease_in_circ(t: float) -> float:
    """Circular ease-in.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return 1 - math.sqrt(1 - t * t)


def ease_out_circ(t: float) -> float:
    """Circular ease-out.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    u = t - 1
    return math.sqrt(1 - u * u)


def ease_in_out_circ(t: float) -> float:
    """Circular ease-in-out.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t < 0.5:
        return (1 - math.sqrt(1 - (2 * t) ** 2)) / 2
    return (math.sqrt(1 - (-2 * t + 2) ** 2) + 1) / 2


# --- Back ---

_BACK_C1 = 1.70158
_BACK_C2 = _BACK_C1 * 1.525
_BACK_C3 = _BACK_C1 + 1


def ease_in_back(t: float) -> float:
    """Back ease-in — slight overshoot at start.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return _BACK_C3 * t * t * t - _BACK_C1 * t * t


def ease_out_back(t: float) -> float:
    """Back ease-out — slight overshoot at end.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    u = t - 1
    return 1 + _BACK_C3 * u * u * u + _BACK_C1 * u * u


def ease_in_out_back(t: float) -> float:
    """Back ease-in-out — overshoot at both ends.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t < 0.5:
        return ((2 * t) ** 2 * ((_BACK_C2 + 1) * 2 * t - _BACK_C2)) / 2
    return ((2 * t - 2) ** 2 * ((_BACK_C2 + 1) * (t * 2 - 2) + _BACK_C2) + 2) / 2


# --- Elastic ---


def ease_in_elastic(t: float) -> float:
    """Elastic ease-in — spring-like bounce at start.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c4 = (2 * math.pi) / 3
    return -(math.pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * c4))


def ease_out_elastic(t: float) -> float:
    """Elastic ease-out — spring-like bounce at end.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c4 = (2 * math.pi) / 3
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def ease_in_out_elastic(t: float) -> float:
    """Elastic ease-in-out — spring-like bounce at both ends.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c5 = (2 * math.pi) / 4.5
    if t < 0.5:
        return -(math.pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
    return (math.pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1


# --- Bounce ---


def ease_out_bounce(t: float) -> float:
    """Bounce ease-out — bouncing at end.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def ease_in_bounce(t: float) -> float:
    """Bounce ease-in — bouncing at start.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    return 1 - ease_out_bounce(1 - t)


def ease_in_out_bounce(t: float) -> float:
    """Bounce ease-in-out — bouncing at both ends.

    Args:
        t: Progress value in [0.0, 1.0].

    Returns:
        Eased value.
    """
    if t < 0.5:
        return (1 - ease_out_bounce(1 - 2 * t)) / 2
    return (1 + ease_out_bounce(2 * t - 1)) / 2


# --- Factory Functions ---


def cubic_bezier(x1: float, y1: float, x2: float, y2: float) -> EasingFn:
    """Create a CSS-compatible cubic bezier easing function.

    The curve is defined by two control points (x1, y1) and (x2, y2).
    Start point is (0, 0) and end point is (1, 1).

    Args:
        x1: X of first control point (0.0-1.0).
        y1: Y of first control point.
        x2: X of second control point (0.0-1.0).
        y2: Y of second control point.

    Returns:
        An easing function.
    """

    def _ease(t: float) -> float:
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        # Newton-Raphson to find parameter for given x
        guess = t
        for _ in range(8):
            x = _bezier_val(guess, x1, x2) - t
            if abs(x) < 1e-7:
                break
            dx = _bezier_deriv(guess, x1, x2)
            if abs(dx) < 1e-7:
                break
            guess -= x / dx
        return _bezier_val(guess, y1, y2)

    return _ease


def _bezier_val(t: float, p1: float, p2: float) -> float:
    """Evaluate cubic bezier with endpoints 0 and 1."""
    return 3 * (1 - t) * (1 - t) * t * p1 + 3 * (1 - t) * t * t * p2 + t * t * t


def _bezier_deriv(t: float, p1: float, p2: float) -> float:
    """Derivative of cubic bezier with endpoints 0 and 1."""
    return 3 * (1 - t) * (1 - t) * p1 + 6 * (1 - t) * t * (p2 - p1) + 3 * t * t * (1 - p2)


def steps(n: int, direction: str = "end") -> EasingFn:
    """Create a stepped easing function for frame-by-frame animation.

    Args:
        n: Number of steps.
        direction: Step timing — "start" or "end".

    Returns:
        An easing function.

    Raises:
        ValueError: If n < 1 or direction is invalid.
    """
    if n < 1:
        msg = f"steps() requires n >= 1, got {n}"
        raise ValueError(msg)
    if direction not in ("start", "end"):
        msg = f"steps() direction must be 'start' or 'end', got '{direction}'"
        raise ValueError(msg)

    def _ease(t: float) -> float:
        if direction == "start":
            return min(1.0, math.ceil(t * n) / n)
        return math.floor(t * n) / n

    return _ease


# Registry of all easing functions by name
EASING_REGISTRY: dict[str, EasingFn] = {
    "linear": linear,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
    "ease_in_quart": ease_in_quart,
    "ease_out_quart": ease_out_quart,
    "ease_in_quint": ease_in_quint,
    "ease_out_quint": ease_out_quint,
    "ease_in_sine": ease_in_sine,
    "ease_out_sine": ease_out_sine,
    "ease_in_out_sine": ease_in_out_sine,
    "ease_in_expo": ease_in_expo,
    "ease_out_expo": ease_out_expo,
    "ease_in_out_expo": ease_in_out_expo,
    "ease_in_circ": ease_in_circ,
    "ease_out_circ": ease_out_circ,
    "ease_in_out_circ": ease_in_out_circ,
    "ease_in_back": ease_in_back,
    "ease_out_back": ease_out_back,
    "ease_in_out_back": ease_in_out_back,
    "ease_in_elastic": ease_in_elastic,
    "ease_out_elastic": ease_out_elastic,
    "ease_in_out_elastic": ease_in_out_elastic,
    "ease_in_bounce": ease_in_bounce,
    "ease_out_bounce": ease_out_bounce,
    "ease_in_out_bounce": ease_in_out_bounce,
}


def get_easing(name: str) -> EasingFn:
    """Look up an easing function by name.

    Args:
        name: Name of the easing function.

    Returns:
        The easing function.

    Raises:
        ValueError: If the easing name is not recognized.
    """
    fn = EASING_REGISTRY.get(name)
    if fn is None:
        available = ", ".join(sorted(EASING_REGISTRY.keys()))
        msg = f"Unknown easing function '{name}'. Available: {available}"
        raise ValueError(msg)
    return fn
