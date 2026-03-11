"""Motion presets — easing curves and duration constants.

Standard motion presets used by all components for consistent,
professional animation timing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ── Easing Functions ────────────────────────────────────────────────────


def _cubic_bezier_eval(p1x: float, p1y: float, p2x: float, p2y: float, t: float) -> float:
    """Evaluate a cubic bezier curve at parameter t.

    Uses Newton-Raphson to find the t parameter for a given x value,
    then returns the corresponding y value.

    Args:
        p1x: First control point x.
        p1y: First control point y.
        p2x: Second control point x.
        p2y: Second control point y.
        t: Input progress (0.0-1.0).

    Returns:
        Eased output value (0.0-1.0).
    """
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0

    # Newton-Raphson to solve for bezier t from x
    guess = t
    for _ in range(8):
        # Bezier x at guess
        cx = 3.0 * p1x
        bx = 3.0 * (p2x - p1x) - cx
        ax = 1.0 - cx - bx
        x = ((ax * guess + bx) * guess + cx) * guess
        if abs(x - t) < 1e-7:
            break
        # Derivative
        dx = (3.0 * ax * guess + 2.0 * bx) * guess + cx
        if abs(dx) < 1e-7:
            break
        guess -= (x - t) / dx

    # Compute y at the solved t
    cy = 3.0 * p1y
    by = 3.0 * (p2y - p1y) - cy
    ay = 1.0 - cy - by
    return ((ay * guess + by) * guess + cy) * guess


def ease_out_quart(t: float) -> float:
    """Quartic ease-out — fast start, gentle deceleration.

    Use for: most enter animations, elements sliding or fading in.

    Args:
        t: Progress (0.0-1.0).

    Returns:
        Eased value.
    """
    return _cubic_bezier_eval(0.25, 1.0, 0.5, 1.0, t)


def ease_in_quart(t: float) -> float:
    """Quartic ease-in — slow start, accelerates out.

    Use for: exit animations, elements leaving the frame.

    Args:
        t: Progress (0.0-1.0).

    Returns:
        Eased value.
    """
    return _cubic_bezier_eval(0.5, 0.0, 0.75, 0.0, t)


def ease_in_out_quart(t: float) -> float:
    """Quartic ease-in-out — symmetrical, polished.

    Use for: state transitions, progress bars, value changes.

    Args:
        t: Progress (0.0-1.0).

    Returns:
        Eased value.
    """
    return _cubic_bezier_eval(0.76, 0.0, 0.24, 1.0, t)


# ── Spring Simulations ─────────────────────────────────────────────────


def _spring_eval(
    stiffness: float,
    damping: float,
    mass: float,
    t: float,
) -> float:
    """Evaluate a critically/underdamped spring at normalized time t.

    Args:
        stiffness: Spring stiffness.
        damping: Damping coefficient.
        mass: Mass.
        t: Normalized time (0.0-1.0), mapped to ~1 second of spring sim.

    Returns:
        Spring displacement (0.0-1.0 at rest).
    """
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0

    # Map t to physical time (1 second of simulation)
    time = t * 1.0
    omega = math.sqrt(stiffness / mass)
    zeta = damping / (2.0 * math.sqrt(stiffness * mass))

    if zeta < 1.0:
        # Underdamped
        omega_d = omega * math.sqrt(1.0 - zeta * zeta)
        envelope = math.exp(-zeta * omega * time)
        return 1.0 - envelope * (
            math.cos(omega_d * time) + (zeta * omega / omega_d) * math.sin(omega_d * time)
        )
    else:
        # Critically/overdamped — use quartic fallback
        return ease_out_quart(t)


def spring_ui(t: float) -> float:
    """UI spring — quick snap with barely perceptible bounce.

    Use for: small UI elements snapping into position.
    stiffness=300, damping=30, mass=1

    Args:
        t: Progress (0.0-1.0).

    Returns:
        Spring value.
    """
    return _spring_eval(300, 30, 1, t)


def spring_reveal(t: float) -> float:
    """Reveal spring — smooth arrival with subtle elastic finish.

    Use for: larger elements like cards, modals, titles.
    stiffness=180, damping=18, mass=1

    Args:
        t: Progress (0.0-1.0).

    Returns:
        Spring value.
    """
    return _spring_eval(180, 18, 1, t)


def spring_bounce(t: float) -> float:
    """Bounce spring — visible bounce, playful but not cartoonish.

    Use for: celebratory or attention-grabbing reveals.
    stiffness=120, damping=10, mass=1

    Args:
        t: Progress (0.0-1.0).

    Returns:
        Spring value.
    """
    return _spring_eval(120, 10, 1, t)


# ── Duration Presets (frames at 30fps) ──────────────────────────────────

INSTANT = 0  # Cut — no animation
FAST = 9  # 300ms — micro-interactions
NORMAL = 15  # 500ms — standard UI transitions
SLOW = 24  # 800ms — larger reveals, titles
STAGGER = 4  # 133ms — delay between sequenced items


# ── Easing Lookup ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class MotionPreset:
    """Named motion preset combining easing and duration.

    Args:
        name: Preset name.
        duration: Duration in frames at 30fps.
        easing_name: Name of the easing function.
    """

    name: str
    duration: int
    easing_name: str


# Standard enter/exit presets
ENTER = MotionPreset("enter", NORMAL, "ease_out_quart")
EXIT = MotionPreset("exit", FAST, "ease_in_quart")
STATE_CHANGE = MotionPreset("state_change", NORMAL, "ease_in_out_quart")

EASINGS: dict[str, type[float]] = {}  # Populated below for lookup

_EASING_FNS: dict[str, object] = {
    "ease_out_quart": ease_out_quart,
    "ease_in_quart": ease_in_quart,
    "ease_in_out_quart": ease_in_out_quart,
    "spring_ui": spring_ui,
    "spring_reveal": spring_reveal,
    "spring_bounce": spring_bounce,
}


def get_motion_easing(name: str) -> object:
    """Get an easing function by name.

    Args:
        name: Easing name (ease_out_quart, spring_ui, etc.).

    Returns:
        Easing function (float -> float).

    Raises:
        ValueError: If the easing name is unknown.
    """
    if name not in _EASING_FNS:
        valid = ", ".join(sorted(_EASING_FNS))
        msg = f"Unknown motion easing '{name}'. Valid: {valid}"
        raise ValueError(msg)
    return _EASING_FNS[name]
