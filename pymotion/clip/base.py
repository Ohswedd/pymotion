"""Clip abstract base class — the foundation for all visual and audio clips.

All clips inherit from Clip and must implement render_frame(). Clips use
a fluent interface where mutation methods return self for chaining.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Self

import numpy as np

from pymotion.utils.math import Vec2


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

    @abstractmethod
    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of this clip.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        ...
