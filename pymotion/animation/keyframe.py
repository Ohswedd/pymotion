"""Keyframe and KeyframeTrack for property animation.

Provides the core animation primitives: Keyframe defines a value at a
specific frame with an easing function, and KeyframeTrack holds a sequence
of keyframes and interpolates between them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pymotion.animation.easing import get_easing
from pymotion.animation.interpolator import interpolate
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2, Vec3

AnimatableValue = float | Color | Vec2 | Vec3


def animate(
    start: AnimatableValue,
    end: AnimatableValue,
    duration: int,
    *,
    easing: str = "linear",
    delay: int = 0,
) -> KeyframeTrack:
    """Shorthand for creating a simple 2-keyframe animation.

    Creates a KeyframeTrack that animates from ``start`` to ``end`` over
    ``duration`` frames, optionally starting after a delay.

    Args:
        start: Value at the beginning of the animation.
        end: Value at the end of the animation.
        duration: Number of frames for the animation.
        easing: Name of the easing function to apply.
        delay: Number of frames to wait before the animation starts.

    Returns:
        A KeyframeTrack with two keyframes.

    Raises:
        ValueError: If duration is not positive.
    """
    if duration <= 0:
        msg = f"Duration must be positive, got {duration}"
        raise ValueError(msg)
    return KeyframeTrack(
        keyframes=[
            Keyframe(frame=delay, value=start, easing=easing),
            Keyframe(frame=delay + duration, value=end),
        ]
    )


@dataclass
class Keyframe:
    """A single keyframe defining a value at a specific frame.

    Args:
        frame: The frame number for this keyframe.
        value: The value at this frame.
        easing: Name of the easing function to use when interpolating
            from this keyframe to the next.
    """

    frame: int
    value: AnimatableValue
    easing: str = "linear"


@dataclass
class KeyframeTrack:
    """Holds keyframes for one animatable property and interpolates between them.

    Keyframes are kept sorted by frame number. Interpolation uses the easing
    function specified on each keyframe.

    Args:
        keyframes: List of keyframes for this track.
    """

    keyframes: list[Keyframe] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Sort keyframes by frame number after initialization."""
        self._sort()

    def _sort(self) -> None:
        """Sort keyframes by frame number."""
        self.keyframes.sort(key=lambda k: k.frame)

    def add(self, keyframe: Keyframe) -> None:
        """Add a keyframe to the track.

        Args:
            keyframe: The keyframe to add.
        """
        self.keyframes.append(keyframe)
        self._sort()

    def value_at(self, frame: int) -> AnimatableValue:
        """Interpolate the value at the given frame.

        If the frame is before the first keyframe, returns the first value.
        If the frame is after the last keyframe, returns the last value.
        Otherwise, interpolates between the surrounding keyframes using
        the appropriate easing function.

        Args:
            frame: The frame number to evaluate.

        Returns:
            The interpolated value at the given frame.

        Raises:
            ValueError: If the track has no keyframes.
        """
        if not self.keyframes:
            msg = "KeyframeTrack has no keyframes"
            raise ValueError(msg)

        # Before first keyframe
        if frame <= self.keyframes[0].frame:
            return self.keyframes[0].value

        # After last keyframe
        if frame >= self.keyframes[-1].frame:
            return self.keyframes[-1].value

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            kf_a = self.keyframes[i]
            kf_b = self.keyframes[i + 1]
            if kf_a.frame <= frame <= kf_b.frame:
                # Calculate raw progress
                duration = kf_b.frame - kf_a.frame
                if duration == 0:
                    return kf_b.value
                raw_t = (frame - kf_a.frame) / duration

                # Apply easing
                easing_fn = get_easing(kf_a.easing)
                eased_t = easing_fn(raw_t)

                # Interpolate
                return interpolate(kf_a.value, kf_b.value, eased_t)

        # Fallback (should not reach here with sorted keyframes)
        return self.keyframes[-1].value
