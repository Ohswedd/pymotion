"""Clip abstract base class — the foundation for all visual and audio clips.

All clips inherit from Clip and must implement render_frame(). Clips use
a fluent interface where mutation methods return self for chaining.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Self

import numpy as np

from pymotion.utils.math import Vec2

if TYPE_CHECKING:
    from pymotion.clip.operations import (
        FreezeFrameClip,
        JoinedClip,
        RepeatedClip,
        SubClip,
    )


class BlendMode(Enum):
    """Blending modes for compositing clips."""

    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ADD = "add"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    DIFFERENCE = "difference"


class Align(Enum):
    """Text and element alignment options.

    Used by TextClip and layout utilities to control positioning
    of content within a clip's bounding box.
    """

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


@dataclass(frozen=True)
class Resolution:
    """Video resolution.

    Args:
        width: Frame width in pixels (must be positive and even).
        height: Frame height in pixels (must be positive and even).
    """

    width: int
    height: int

    def __post_init__(self) -> None:
        """Validate resolution dimensions."""
        if self.width <= 0 or self.height <= 0:
            msg = f"Resolution must be positive, got {self.width}x{self.height}"
            raise ValueError(msg)
        if self.width % 2 != 0 or self.height % 2 != 0:
            msg = (
                f"Resolution must be even numbers for codec compatibility, "
                f"got {self.width}x{self.height}"
            )
            raise ValueError(msg)


@dataclass(frozen=True)
class TimeRange:
    """A range of frames (inclusive start, exclusive end).

    Args:
        start: First frame (inclusive).
        end: Last frame (exclusive).
    """

    start: int
    end: int

    @property
    def duration(self) -> int:
        """Number of frames in this range."""
        return self.end - self.start


@dataclass(frozen=True)
class RenderContext:
    """Immutable snapshot of rendering state at frame N.

    Passed to every render call to provide frame-specific context.

    Args:
        frame: Global frame number.
        fps: Frames per second.
        resolution: Output resolution.
        time_range: The clip's own time range.
        local_frame: Frame relative to clip start.
        progress: Progress within clip duration (0.0 to 1.0).
    """

    frame: int
    fps: int
    resolution: Resolution
    time_range: TimeRange
    local_frame: int
    progress: float


@dataclass
class Clip(ABC):
    """Abstract base class for all clips.

    Every clip has a position in the timeline, transform properties,
    and must implement render_frame() to produce BGRA pixel data.
    """

    start: int = 0
    end: int = 0
    _opacity: float = 1.0
    _position: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    anchor: Vec2 = field(default_factory=lambda: Vec2(0.5, 0.5))
    _scale: Vec2 = field(default_factory=lambda: Vec2(1.0, 1.0))
    _rotation: float = 0.0
    blend_mode: BlendMode = BlendMode.NORMAL

    def set_duration(self, frames: int) -> Self:
        """Set the duration of this clip in frames.

        Args:
            frames: Number of frames for this clip.

        Returns:
            Self for method chaining.
        """
        self.end = self.start + frames
        return self

    def set_position(self, x: float, y: float) -> Self:
        """Set the position of this clip.

        Args:
            x: X coordinate (pixels from left).
            y: Y coordinate (pixels from top).

        Returns:
            Self for method chaining.
        """
        self._position = Vec2(x, y)
        return self

    def set_scale(self, sx: float, sy: float | None = None) -> Self:
        """Set the scale of this clip.

        Args:
            sx: X scale factor.
            sy: Y scale factor (defaults to sx for uniform scaling).

        Returns:
            Self for method chaining.
        """
        if sy is None:
            sy = sx
        self._scale = Vec2(sx, sy)
        return self

    def set_rotation(self, deg: float) -> Self:
        """Set the rotation of this clip in degrees.

        Args:
            deg: Rotation angle in degrees, clockwise.

        Returns:
            Self for method chaining.
        """
        self._rotation = deg
        return self

    def set_opacity(self, value: float) -> Self:
        """Set the opacity of this clip.

        Args:
            value: Opacity value (0.0 = transparent, 1.0 = opaque).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If value is not between 0.0 and 1.0.
        """
        if not 0.0 <= value <= 1.0:
            msg = f"Opacity must be between 0.0 and 1.0, got {value}"
            raise ValueError(msg)
        self._opacity = value
        return self

    def at(self, frame: int) -> Self:
        """Set the start frame of this clip.

        Args:
            frame: Frame number at which this clip begins.

        Returns:
            Self for method chaining.
        """
        duration = self.end - self.start
        self.start = frame
        self.end = frame + duration
        return self

    @property
    def duration(self) -> int:
        """Duration of this clip in frames."""
        return self.end - self.start

    def split(self, frame: int) -> tuple[SubClip, SubClip]:
        """Split this clip into two at the given local frame.

        The first clip contains frames [0, frame) and the second contains
        frames [frame, duration). Both delegate rendering to this clip.

        Args:
            frame: Local frame index at which to split.

        Returns:
            Tuple of (first_half, second_half) SubClips.

        Raises:
            ValueError: If frame is outside the valid range.
        """
        from pymotion.clip.operations import SubClip

        if frame <= 0 or frame >= self.duration:
            msg = f"Split frame must be between 1 and {self.duration - 1} (inclusive), got {frame}"
            raise ValueError(msg)

        first = SubClip()
        first._source = self
        first._source_start = 0
        first._source_end = frame
        first.start = 0
        first.end = frame

        second = SubClip()
        second._source = self
        second._source_start = frame
        second._source_end = self.duration
        second.start = 0
        second.end = self.duration - frame

        return first, second

    def join(self, other: Clip) -> JoinedClip:
        """Concatenate this clip with another, playing self then other.

        Args:
            other: The clip to append after this one.

        Returns:
            A new JoinedClip that plays self followed by other.

        Raises:
            ValueError: If either clip has zero duration.
        """
        from pymotion.clip.operations import JoinedClip

        if self.duration <= 0:
            msg = "Cannot join: first clip has zero duration"
            raise ValueError(msg)
        if other.duration <= 0:
            msg = "Cannot join: second clip has zero duration"
            raise ValueError(msg)

        result = JoinedClip()
        result._clip_a = self
        result._clip_b = other
        result.start = 0
        result.end = self.duration + other.duration
        return result

    def subclip(self, start: int, end: int) -> SubClip:
        """Extract a portion of this clip in local frame coordinates.

        Args:
            start: Start frame (inclusive, local to this clip).
            end: End frame (exclusive, local to this clip).

        Returns:
            A new SubClip spanning the given range.

        Raises:
            ValueError: If the range is invalid.
        """
        from pymotion.clip.operations import SubClip

        if start < 0:
            msg = f"Start frame must be non-negative, got {start}"
            raise ValueError(msg)
        if end > self.duration:
            msg = f"End frame ({end}) exceeds clip duration ({self.duration})"
            raise ValueError(msg)
        if start >= end:
            msg = f"Start ({start}) must be less than end ({end})"
            raise ValueError(msg)

        result = SubClip()
        result._source = self
        result._source_start = start
        result._source_end = end
        result.start = 0
        result.end = end - start
        return result

    def repeat(self, n: int) -> RepeatedClip:
        """Repeat this clip N times.

        Args:
            n: Number of repetitions (must be >= 1).

        Returns:
            A new RepeatedClip that loops this clip.

        Raises:
            ValueError: If n is less than 1 or clip has zero duration.
        """
        from pymotion.clip.operations import RepeatedClip

        if n < 1:
            msg = f"Repeat count must be >= 1, got {n}"
            raise ValueError(msg)
        if self.duration <= 0:
            msg = "Cannot repeat a clip with zero duration"
            raise ValueError(msg)

        result = RepeatedClip()
        result._source = self
        result._repeat_count = n
        result.start = 0
        result.end = self.duration * n
        return result

    def freeze_frame(self, frame: int, duration: int) -> FreezeFrameClip:
        """Hold a single frame for a duration, then resume playback.

        Creates a new clip where playback proceeds normally until
        the freeze point, holds that frame for the specified duration,
        then resumes from the next frame.

        Args:
            frame: Local frame index to freeze.
            duration: Number of frames to hold the frozen frame.

        Returns:
            A new FreezeFrameClip with the frozen section inserted.

        Raises:
            ValueError: If frame is out of range or duration is not positive.
        """
        from pymotion.clip.operations import FreezeFrameClip

        if frame < 0 or frame >= self.duration:
            msg = f"Freeze frame must be between 0 and {self.duration - 1}, got {frame}"
            raise ValueError(msg)
        if duration <= 0:
            msg = f"Freeze duration must be positive, got {duration}"
            raise ValueError(msg)

        result = FreezeFrameClip()
        result._source = self
        result._freeze_at = frame
        result._freeze_duration = duration
        result.start = 0
        result.end = self.duration + duration
        return result

    @abstractmethod
    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of this clip.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        ...
