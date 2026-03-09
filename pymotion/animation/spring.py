"""Physics-based spring animation solver.

Implements an analytical damped harmonic oscillator that produces
an easing function. No simulation loop — always stable.
"""

from __future__ import annotations

import math
from collections.abc import Callable

EasingFn = Callable[[float], float]


def spring(
    stiffness: float = 180.0,
    damping: float = 12.0,
    mass: float = 1.0,
) -> EasingFn:
    """Create an easing function based on a damped harmonic oscillator.

    Uses the analytical solution of the spring equation:
        m * x'' + c * x' + k * x = 0

    The returned function maps t in [0, 1] to a spring-animated value
    that settles at 1.0.

    Args:
        stiffness: Spring stiffness constant (k). Higher = faster oscillation.
        damping: Damping coefficient (c). Higher = less oscillation.
        mass: Mass of the object (m).

    Returns:
        An easing function.

    Raises:
        ValueError: If stiffness, damping, or mass are not positive.
    """
    if stiffness <= 0:
        msg = f"stiffness must be positive, got {stiffness}"
        raise ValueError(msg)
    if damping < 0:
        msg = f"damping must be non-negative, got {damping}"
        raise ValueError(msg)
    if mass <= 0:
        msg = f"mass must be positive, got {mass}"
        raise ValueError(msg)

    omega0 = math.sqrt(stiffness / mass)  # natural frequency
    zeta = damping / (2 * math.sqrt(stiffness * mass))  # damping ratio

    # We solve for displacement from target (1.0), starting at -1 (i.e., from 0 to 1)
    # x(0) = -1, x'(0) = 0, settling at x = 0 (so output = 1 + x)

    # Scale time so the spring mostly settles within t=[0,1]
    # Use ~4 natural periods as the time scale
    duration = 4 * math.pi / omega0 if omega0 > 0 else 1.0

    if zeta < 1.0:
        # Underdamped
        omega_d = omega0 * math.sqrt(1 - zeta * zeta)

        def _underdamped(t: float) -> float:
            if t <= 0.0:
                return 0.0
            if t >= 1.0:
                return 1.0
            time = t * duration
            decay = math.exp(-zeta * omega0 * time)
            cos_part = math.cos(omega_d * time)
            sin_part = math.sin(omega_d * time)
            # x(t) = e^(-zeta*omega0*t) * (A*cos(omega_d*t) + B*sin(omega_d*t))
            # With x(0) = -1 → A = -1
            # With x'(0) = 0 → B = -zeta*omega0 / omega_d
            a_coeff = -1.0
            b_coeff = -(zeta * omega0) / omega_d if omega_d > 0 else 0.0
            x = decay * (a_coeff * cos_part + b_coeff * sin_part)
            return 1.0 + x

        return _underdamped

    if zeta == 1.0:
        # Critically damped

        def _critical(t: float) -> float:
            if t <= 0.0:
                return 0.0
            if t >= 1.0:
                return 1.0
            time = t * duration
            decay = math.exp(-omega0 * time)
            # x(t) = (A + B*t) * e^(-omega0*t)
            # x(0) = -1 → A = -1
            # x'(0) = 0 → B = -omega0
            x = (-1.0 - omega0 * time) * decay
            return 1.0 + x

        return _critical

    # Overdamped (zeta > 1)
    s1 = -omega0 * (zeta + math.sqrt(zeta * zeta - 1))
    s2 = -omega0 * (zeta - math.sqrt(zeta * zeta - 1))

    # x(0) = -1: A + B = -1
    # x'(0) = 0: A*s1 + B*s2 = 0
    # → A = s2 / (s2 - s1), B = -s1 / (s2 - s1)  (scaled by -1)
    denom = s2 - s1
    a_coeff = s2 / denom if abs(denom) > 1e-12 else -0.5
    b_coeff = -s1 / denom if abs(denom) > 1e-12 else -0.5

    def _overdamped(t: float) -> float:
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        time = t * duration
        x = a_coeff * math.exp(s1 * time) + b_coeff * math.exp(s2 * time)
        return 1.0 + x

    return _overdamped
