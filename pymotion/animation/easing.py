"""Easing functions for animation curves.

All easing functions are pure functions (t: float) -> float where t is in [0.0, 1.0].
Phase 0.1 provides the first 10 easing functions.
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


# Registry of all easing functions by name
EASING_REGISTRY: dict[str, EasingFn] = {
    "linear": linear,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
    "ease_in_sine": ease_in_sine,
    "ease_out_sine": ease_out_sine,
    "ease_in_out_sine": ease_in_out_sine,
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
