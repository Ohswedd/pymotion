"""Expression system — drive any animatable property with Python callables.

Expressions are Python callables that receive an :class:`ExpressionContext`
and return a float.  They can be attached to any animatable clip property
(position.x, position.y, scale.x, scale.y, rotation, opacity) via
:meth:`Clip.set_expression`.

Helper functions :func:`wiggle`, :func:`loop_in`, and :func:`loop_out`
provide common expression patterns.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Callable
from dataclasses import dataclass

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

# Supported property names for set_expression
EXPRESSION_PROPERTIES = frozenset(
    {
        "position.x",
        "position.y",
        "scale.x",
        "scale.y",
        "rotation",
        "opacity",
    }
)


@dataclass(frozen=True)
class ExpressionContext:
    """Immutable context passed to expression callables.

    Provides frame-level metadata for expression evaluation.

    Args:
        frame: Current global frame number.
        time: Current time in seconds (frame / fps).
        fps: Frames per second.
        comp_width: Composition width in pixels.
        comp_height: Composition height in pixels.
        progress: Progress within the clip duration (0.0–1.0).
        local_frame: Frame relative to the clip's start.
    """

    frame: int
    time: float
    fps: int
    comp_width: int
    comp_height: int
    progress: float
    local_frame: int


ExpressionFn = Callable[[ExpressionContext], float]


def evaluate_expressions(
    expressions: dict[str, ExpressionFn],
    ctx: ExpressionContext,
) -> dict[str, float]:
    """Evaluate all expressions and return property → value mapping.

    Args:
        expressions: Map of property name to callable.
        ctx: Expression context for the current frame.

    Returns:
        Map of property name to evaluated float value.
    """
    results: dict[str, float] = {}
    for prop, fn in expressions.items():
        results[prop] = fn(ctx)
    return results


# ---------------------------------------------------------------------------
# Expression helpers
# ---------------------------------------------------------------------------


def _noise_1d(seed: int, t: float) -> float:
    """Simple deterministic pseudo-noise based on hashing.

    Args:
        seed: Random seed.
        t: Time value.

    Returns:
        Smooth noise value in [-1, 1].
    """
    # Integer neighbours
    t0 = int(math.floor(t))
    t1 = t0 + 1
    frac = t - t0

    def _hash(n: int) -> float:
        data = struct.pack(">ii", seed, n)
        h = hashlib.md5(data, usedforsecurity=False).digest()  # noqa: S324
        val: int = struct.unpack(">H", h[:2])[0]
        return (val / 65535.0) * 2.0 - 1.0

    v0 = _hash(t0)
    v1 = _hash(t1)

    # Smoothstep interpolation
    s = frac * frac * (3.0 - 2.0 * frac)
    return v0 + (v1 - v0) * s


def wiggle(freq: float, amp: float, seed: int = 0) -> ExpressionFn:
    """Create a smooth random oscillation expression.

    Args:
        freq: Oscillation frequency (cycles per second).
        amp: Maximum amplitude of the oscillation.
        seed: Random seed for reproducible results.

    Returns:
        An expression function that produces smooth random values.

    Example::

        clip.set_expression("position.x", wiggle(2.0, 50.0))
    """

    def _wiggle(ctx: ExpressionContext) -> float:
        t = ctx.time * freq
        return _noise_1d(seed, t) * amp

    return _wiggle


def loop_in(
    duration_frames: int,
    base_fn: ExpressionFn,
) -> ExpressionFn:
    """Loop an expression's first N frames at the start of a clip.

    When the clip's local_frame exceeds ``duration_frames``, the
    expression evaluates normally.  Before that, it cycles through
    the first ``duration_frames`` frames repeatedly.

    Args:
        duration_frames: Number of frames to loop.
        base_fn: The expression to loop.

    Returns:
        A looping expression function.
    """

    def _loop_in(ctx: ExpressionContext) -> float:
        if duration_frames <= 0:
            return base_fn(ctx)
        looped_frame = ctx.local_frame % duration_frames
        looped_ctx = ExpressionContext(
            frame=ctx.frame,
            time=looped_frame / ctx.fps if ctx.fps > 0 else 0.0,
            fps=ctx.fps,
            comp_width=ctx.comp_width,
            comp_height=ctx.comp_height,
            progress=looped_frame / max(duration_frames - 1, 1),
            local_frame=looped_frame,
        )
        return base_fn(looped_ctx)

    return _loop_in


def loop_out(
    duration_frames: int,
    base_fn: ExpressionFn,
) -> ExpressionFn:
    """Loop an expression's last N frames at the end of a clip.

    When the clip's local_frame is before ``duration_frames`` from
    the end, the expression evaluates normally.  After that, it
    cycles through the last ``duration_frames`` frames repeatedly.

    Args:
        duration_frames: Number of frames to loop from the end.
        base_fn: The expression to loop.

    Returns:
        A looping expression function.
    """

    def _loop_out(ctx: ExpressionContext) -> float:
        if duration_frames <= 0:
            return base_fn(ctx)
        # Map current frame into the last N frames cyclically.
        # This loops the END segment of the animation, unlike loop_in
        # which loops the START segment.
        # Compute the loop offset so that frame 0 maps to the start
        # of the last-N-frames window.
        looped_frame = ctx.local_frame % duration_frames
        # Offset into the end of the duration_frames window
        end_offset = duration_frames - 1 - looped_frame
        # The looped frame counts backwards from the end of the region
        mapped_frame = duration_frames - 1 - end_offset
        looped_ctx = ExpressionContext(
            frame=ctx.frame,
            time=mapped_frame / ctx.fps if ctx.fps > 0 else 0.0,
            fps=ctx.fps,
            comp_width=ctx.comp_width,
            comp_height=ctx.comp_height,
            progress=mapped_frame / max(duration_frames - 1, 1),
            local_frame=mapped_frame,
        )
        return base_fn(looped_ctx)

    return _loop_out
