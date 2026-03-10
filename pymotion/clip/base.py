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
    from pathlib import Path

    from pymotion.animation.keyframe import KeyframeTrack
    from pymotion.clip.operations import (
        FreezeFrameClip,
        JoinedClip,
        RepeatedClip,
        ReversedClip,
        SpeedClip,
        SpeedRampClip,
        SubClip,
        TimeRemappedClip,
    )
    from pymotion.effects.base import Effect
    from pymotion.expressions import ExpressionFn
    from pymotion.masking import MaskGroup, MaskOp
    from pymotion.proxy import ProxyClip
    from pymotion.tracking import StabilizedClip


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


def _interp_speed(keyframes: list[tuple[int, float]], frame: int) -> float:
    """Linearly interpolate speed at a given frame from speed keyframes.

    Args:
        keyframes: Sorted list of (frame, factor) pairs.
        frame: The output frame to evaluate.

    Returns:
        Interpolated speed factor.
    """
    if not keyframes:
        return 1.0
    if frame <= keyframes[0][0]:
        return keyframes[0][1]
    if frame >= keyframes[-1][0]:
        return keyframes[-1][1]
    for i in range(len(keyframes) - 1):
        f_a, s_a = keyframes[i]
        f_b, s_b = keyframes[i + 1]
        if f_a <= frame <= f_b:
            if f_b == f_a:
                return s_b
            t = (frame - f_a) / (f_b - f_a)
            return s_a + (s_b - s_a) * t
    return keyframes[-1][1]


def _check_circular_parent(proposed_parent: Clip, child: Clip) -> None:
    """Raise ValueError if assigning *proposed_parent* would create a cycle.

    Args:
        proposed_parent: The clip to be assigned as parent.
        child: The clip that would become the child.

    Raises:
        ValueError: If a cycle is detected.
    """
    visited: set[int] = {id(child)}
    current: Clip | None = proposed_parent
    while current is not None:
        if id(current) in visited:
            msg = "Circular parenting detected"
            raise ValueError(msg)
        visited.add(id(current))
        current = current._parent


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
    _effects: list[Effect] = field(default_factory=list)
    _masks: list[MaskGroup] = field(default_factory=list)
    _parent: Clip | None = field(default=None, repr=False)
    _expressions: dict[str, ExpressionFn] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def set_expression(
        self,
        prop: str,
        fn: ExpressionFn,
    ) -> Self:
        """Attach a Python callable expression to an animatable property.

        The expression is evaluated each frame during
        :meth:`render_with_effects` and the result is applied to the
        property before rendering.

        Supported properties: ``position.x``, ``position.y``,
        ``scale.x``, ``scale.y``, ``rotation``, ``opacity``.

        Args:
            prop: Property name to drive.
            fn: Callable receiving :class:`ExpressionContext` and
                returning a float.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If the property name is not supported.
        """
        from pymotion.expressions import EXPRESSION_PROPERTIES

        if prop not in EXPRESSION_PROPERTIES:
            msg = (
                f"Unsupported expression property '{prop}'. Valid: {sorted(EXPRESSION_PROPERTIES)}"
            )
            raise ValueError(msg)
        self._expressions[prop] = fn
        return self

    def clear_expressions(self) -> Self:
        """Remove all expressions from this clip.

        Returns:
            Self for method chaining.
        """
        self._expressions.clear()
        return self

    def _apply_expressions(self, ctx: RenderContext) -> None:
        """Evaluate and apply all expression results to clip properties.

        Called internally before rendering each frame.

        Args:
            ctx: Render context for the current frame.
        """
        if not self._expressions:
            return

        from pymotion.expressions import ExpressionContext, evaluate_expressions

        expr_ctx = ExpressionContext(
            frame=ctx.frame,
            time=ctx.local_frame / ctx.fps if ctx.fps > 0 else 0.0,
            fps=ctx.fps,
            comp_width=ctx.resolution.width,
            comp_height=ctx.resolution.height,
            progress=ctx.progress,
            local_frame=ctx.local_frame,
        )

        values = evaluate_expressions(self._expressions, expr_ctx)

        for prop, val in values.items():
            if prop == "position.x":
                self._position = Vec2(val, self._position.y)
            elif prop == "position.y":
                self._position = Vec2(self._position.x, val)
            elif prop == "scale.x":
                self._scale = Vec2(val, self._scale.y)
            elif prop == "scale.y":
                self._scale = Vec2(self._scale.x, val)
            elif prop == "rotation":
                self._rotation = val
            elif prop == "opacity":
                self._opacity = max(0.0, min(1.0, val))

    # ------------------------------------------------------------------
    # Parenting
    # ------------------------------------------------------------------

    @property
    def parent(self) -> Clip | None:
        """The parent clip whose transforms are inherited.

        Setting a parent causes this clip to inherit the parent's
        position, scale, and rotation each frame.  Independent local
        offsets are applied on top of the inherited transform.

        Raises:
            ValueError: If assigning the parent would create a cycle.
        """
        return self._parent

    @parent.setter
    def parent(self, value: Clip | None) -> None:
        if value is not None:
            _check_circular_parent(value, self)
        self._parent = value

    def position_at(self, frame: int) -> Vec2:
        """Return the effective position at a frame, including parent chain.

        The parent's world position is added to this clip's local position,
        and the parent's scale is applied to this clip's local offset.

        Args:
            frame: The frame to evaluate at (currently unused since
                position is not keyframed; reserved for future use).

        Returns:
            Accumulated position as Vec2.
        """
        pos = self._position
        if self._parent is not None:
            parent_pos = self._parent.position_at(frame)
            parent_scale = self._parent.scale_at(frame)
            pos = Vec2(
                parent_pos.x + pos.x * parent_scale.x,
                parent_pos.y + pos.y * parent_scale.y,
            )
        return pos

    def scale_at(self, frame: int) -> Vec2:
        """Return the effective scale at a frame, including parent chain.

        Scales are multiplied down the hierarchy.

        Args:
            frame: The frame to evaluate at.

        Returns:
            Accumulated scale as Vec2.
        """
        sc = self._scale
        if self._parent is not None:
            parent_sc = self._parent.scale_at(frame)
            sc = Vec2(sc.x * parent_sc.x, sc.y * parent_sc.y)
        return sc

    def rotation_at(self, frame: int) -> float:
        """Return the effective rotation at a frame, including parent chain.

        Rotations are summed down the hierarchy.

        Args:
            frame: The frame to evaluate at.

        Returns:
            Accumulated rotation in degrees.
        """
        rot = self._rotation
        if self._parent is not None:
            rot += self._parent.rotation_at(frame)
        return rot

    def opacity_at(self, frame: int) -> float:
        """Return the opacity at a frame.

        Args:
            frame: The frame to evaluate at (reserved for future use).

        Returns:
            Opacity value (0.0–1.0).
        """
        return self._opacity

    def add_effect(self, effect: Effect) -> Self:
        """Add a visual effect to this clip.

        Effects are applied in order after the clip renders its frame.

        Args:
            effect: The effect to add.

        Returns:
            Self for method chaining.
        """
        self._effects.append(effect)
        return self

    def add_mask(
        self,
        mask: object,
        op: MaskOp | None = None,
    ) -> Self:
        """Add a mask to this clip.

        Masks are applied after effects in :meth:`render_with_effects`.
        Multiple masks are combined using boolean operations.

        Args:
            mask: A :class:`~pymotion.masking.Mask` instance.
            op: Boolean operation for combining with previous masks.
                Defaults to :attr:`MaskOp.ADD`.

        Returns:
            Self for method chaining.
        """
        from pymotion.masking import Mask as MaskBase
        from pymotion.masking import MaskGroup as MaskGroupCls
        from pymotion.masking import MaskOp as MaskOpEnum

        if not isinstance(mask, MaskBase):
            msg = f"Expected a Mask instance, got {type(mask).__name__}"
            raise TypeError(msg)

        if op is None:
            op_val = MaskOpEnum.ADD
        else:
            op_val = op

        self._masks.append(MaskGroupCls(mask=mask, op=op_val))
        return self

    def clear_masks(self) -> Self:
        """Remove all masks from this clip.

        Returns:
            Self for method chaining.
        """
        self._masks.clear()
        return self

    def render_with_effects(self, ctx: RenderContext) -> np.ndarray:
        """Render a frame, apply all effects, then apply masks.

        The pipeline is: expressions → render_frame() → effects → masks.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array with all effects and masks applied.
        """
        self._apply_expressions(ctx)
        frame = self.render_frame(ctx)
        for effect in self._effects:
            frame = effect.apply(frame, ctx)
        if self._masks:
            from pymotion.masking import apply_masks

            frame = apply_masks(frame, self._masks, ctx)
        return frame

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

    def speed(self, factor: float, interpolation: str = "nearest") -> SpeedClip:
        """Apply a uniform speed change to this clip.

        A factor of 2.0 plays at double speed (shorter duration).
        A factor of 0.5 plays at half speed (longer duration).
        For slow-motion, ``interpolation="optical_flow"`` uses OpenCV
        optical flow for smoother results (falls back to linear blend
        if OpenCV is unavailable).

        Args:
            factor: Speed multiplier (0.1 to 10.0).
            interpolation: Frame interpolation mode. ``"nearest"`` for
                frame duplication, ``"optical_flow"`` for optical flow.

        Returns:
            A new SpeedClip with the speed change applied.

        Raises:
            ValueError: If factor is outside the valid range.
        """
        import math

        from pymotion.clip.operations import SpeedClip

        if factor < 0.1 or factor > 10.0:
            msg = f"Speed factor must be between 0.1 and 10.0, got {factor}"
            raise ValueError(msg)
        if self.duration <= 0:
            msg = "Cannot change speed of a clip with zero duration"
            raise ValueError(msg)

        new_duration = math.ceil(self.duration / factor)

        result = SpeedClip()
        result._source = self
        result._factor = factor
        result._interpolation = interpolation
        result.start = 0
        result.end = new_duration
        return result

    def speed_ramp(self, keyframes: list[tuple[int, float]]) -> SpeedRampClip:
        """Apply variable speed within this clip.

        Speed changes over time according to the given keyframe pairs.
        Each pair is ``(output_frame, speed_factor)``. The source frame
        is computed by integrating the speed curve, and the total
        duration is recalculated.

        Args:
            keyframes: List of ``(frame, factor)`` pairs defining the
                speed curve. Frames must be in ascending order.

        Returns:
            A new SpeedRampClip with variable speed applied.

        Raises:
            ValueError: If keyframes are empty or invalid.
        """
        from pymotion.clip.operations import SpeedRampClip

        if not keyframes:
            msg = "Speed ramp keyframes cannot be empty"
            raise ValueError(msg)
        if self.duration <= 0:
            msg = "Cannot speed ramp a clip with zero duration"
            raise ValueError(msg)

        # Sort by frame
        sorted_kfs = sorted(keyframes, key=lambda kf: kf[0])

        # Validate factors
        for frame_num, factor in sorted_kfs:
            if factor <= 0:
                msg = f"Speed factor must be positive, got {factor} at frame {frame_num}"
                raise ValueError(msg)

        # Build source frame map by integrating speed over output frames
        # We walk output frames 0..N and accumulate source frames
        source_frame_map: list[float] = []
        source_pos = 0.0
        max_output_frame = 10 * self.duration  # safety limit

        for out_frame in range(max_output_frame):
            if source_pos >= self.duration:
                break
            source_frame_map.append(source_pos)
            # Interpolate speed at this output frame
            current_speed = _interp_speed(sorted_kfs, out_frame)
            source_pos += current_speed

        result = SpeedRampClip()
        result._source = self
        result._speed_keyframes = sorted_kfs
        result._source_frame_map = source_frame_map
        result.start = 0
        result.end = len(source_frame_map)
        return result

    def reverse(self) -> ReversedClip:
        """Play this clip backwards.

        Returns:
            A new ReversedClip that plays in reverse.

        Raises:
            ValueError: If the clip has zero duration.
        """
        from pymotion.clip.operations import ReversedClip

        if self.duration <= 0:
            msg = "Cannot reverse a clip with zero duration"
            raise ValueError(msg)

        result = ReversedClip()
        result._source = self
        result.start = 0
        result.end = self.duration
        return result

    def time_remap(self, curve: KeyframeTrack) -> TimeRemappedClip:
        """Apply arbitrary time remapping via a keyframe curve.

        The curve maps output frames to source frames. For example,
        a curve with keyframes ``[(0, 0), (60, 30)]`` would play the
        first 30 source frames over 60 output frames (half speed).

        Args:
            curve: A KeyframeTrack where each keyframe value is a
                float representing the source frame number.

        Returns:
            A new TimeRemappedClip with the remapping applied.

        Raises:
            ValueError: If the curve has no keyframes.
        """
        from pymotion.clip.operations import TimeRemappedClip

        if not curve.keyframes:
            msg = "Time remap curve must have at least one keyframe"
            raise ValueError(msg)

        result = TimeRemappedClip()
        result._source = self
        result._curve = curve
        result.start = 0
        result.end = self.duration
        return result

    def create_proxy(
        self,
        scale: float = 0.25,
        cache_dir: Path | None = None,
    ) -> ProxyClip:
        """Generate a low-resolution proxy for this clip.

        The proxy is rendered at the given scale factor and cached on disk.
        Filename is ``SHA256(source + scale)[:12].proxy``. Reuses existing
        proxy if source hasn't changed.

        Args:
            scale: Scale factor (0.0 exclusive to 1.0 inclusive).
            cache_dir: Directory for proxy cache. Defaults to
                ``~/.pymotion/proxies/``.

        Returns:
            A ProxyClip backed by the cached file.

        Raises:
            ValueError: If scale is invalid or clip has zero duration.
        """
        from pymotion.proxy import create_proxy as _create_proxy

        return _create_proxy(self, scale=scale, cache_dir=cache_dir)

    def stabilize(
        self,
        smoothing: int = 30,
        border_mode: str = "crop",
    ) -> StabilizedClip:
        """Stabilize this clip by smoothing camera motion.

        Analyzes frame-to-frame motion and applies a smoothing filter
        to reduce camera shake. Requires OpenCV for feature tracking;
        falls back to no correction without it.

        Args:
            smoothing: Smoothing window size in frames. Larger values
                produce smoother but more delayed stabilization.
            border_mode: How to handle frame borders after correction.
                ``"crop"`` fills edges with black, ``"reflect"`` uses
                edge replication.

        Returns:
            A new StabilizedClip with stabilization applied.

        Raises:
            ValueError: If the clip has zero duration or smoothing is invalid.
        """
        from pymotion.tracking import (
            StabilizedClip as _StabilizedClip,
        )
        from pymotion.tracking import _compute_stabilization_offsets

        if self.duration <= 0:
            msg = "Cannot stabilize a clip with zero duration"
            raise ValueError(msg)
        if smoothing < 1:
            msg = f"Smoothing must be >= 1, got {smoothing}"
            raise ValueError(msg)

        offsets = _compute_stabilization_offsets(self, smoothing)

        result = _StabilizedClip()
        result._source = self
        result._smoothing = smoothing
        result._border_mode = border_mode
        result._offsets = offsets
        result.start = 0
        result.end = self.duration
        return result

    def follow_tracker(
        self,
        tracker: object,
        prop: str = "position",
        offset: tuple[float, float] = (0.0, 0.0),
    ) -> Self:
        """Wire motion tracking data to a clip property.

        Applies the tracker's keyframe data to this clip's property
        (e.g. position). The clip is modified in place.

        Args:
            tracker: A MotionTracker instance with tracking data.
            prop: Property to drive (currently "position").
            offset: Constant (dx, dy) offset added to tracked values.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If prop is not supported.
        """
        from pymotion.tracking import MotionTracker

        if not isinstance(tracker, MotionTracker):
            msg = "tracker must be a MotionTracker instance"
            raise TypeError(msg)

        if not tracker._tracking_data:
            msg = "Tracker has no data. Call tracker.track() first."
            raise RuntimeError(msg)

        if prop != "position":
            msg = f"Unsupported property '{prop}'. Only 'position' is supported."
            raise ValueError(msg)

        # Use first frame's position as default
        if tracker._tracking_data:
            first_pos = next(iter(tracker._tracking_data.values()))
            self.set_position(first_pos.x + offset[0], first_pos.y + offset[1])

        return self

    def follow_path(
        self,
        svg_path_str: str,
        duration: int,
        align: bool = True,
    ) -> Self:
        """Animate this clip's center along an SVG path.

        Sets expressions on position.x, position.y, and optionally rotation
        to follow the path over the given duration in frames.

        Args:
            svg_path_str: SVG path data string (M, L, C, Z commands).
            duration: Number of frames for the animation.
            align: If True, rotate the clip to follow the path tangent.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If the path is empty or duration is not positive.
        """
        from pymotion.path_animation import follow_path as _follow_path

        _follow_path(self, svg_path_str, duration, align=align)
        return self

    @abstractmethod
    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of this clip.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        ...


@dataclass
class NullObject(Clip):
    """An invisible clip used as a transform group anchor.

    NullObject has no visual output (fully transparent) but carries
    position, scale, and rotation properties that child clips inherit
    via the parenting system.

    Example::

        anchor = NullObject()
        anchor.set_position(100, 100).set_duration(60)
        child.parent = anchor
    """

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Return a fully transparent frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            Transparent BGRA numpy array.
        """
        return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)
