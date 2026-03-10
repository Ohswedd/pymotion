"""Clip operation wrappers — split, join, subclip, repeat, freeze, concatenate.

These wrapper clips delegate rendering to source clips while remapping
the frame timeline for various editing operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from pymotion.clip.base import Clip, RenderContext, TimeRange
from pymotion.utils.logging import get_logger

if TYPE_CHECKING:
    from pymotion.transition.base import Transition

logger = get_logger(__name__)


def _make_source_ctx(
    ctx: RenderContext,
    source: Clip,
    source_local_frame: int,
) -> RenderContext:
    """Create a RenderContext mapped to the source clip's frame space.

    Args:
        ctx: The original render context.
        source: The source clip to map into.
        source_local_frame: The local frame within the source clip.

    Returns:
        A new RenderContext with remapped local_frame and progress.
    """
    source_duration = source.duration
    clamped = max(0, min(source_local_frame, source_duration - 1))
    progress = clamped / max(source_duration - 1, 1)
    return RenderContext(
        frame=ctx.frame,
        fps=ctx.fps,
        resolution=ctx.resolution,
        time_range=TimeRange(start=source.start, end=source.end),
        local_frame=clamped,
        progress=progress,
    )


@dataclass
class SubClip(Clip):
    """A clip that renders a subrange of another clip.

    Maps local frames to a window within the source clip's frame space.

    Args:
        _source: The source clip to render from.
        _source_start: Start frame within the source (inclusive).
        _source_end: End frame within the source (exclusive).
    """

    _source: Clip = field(default_factory=lambda: _placeholder_clip())
    _source_start: int = 0
    _source_end: int = 0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a frame by delegating to the source clip with remapped frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        source_local = ctx.local_frame + self._source_start
        source_ctx = _make_source_ctx(ctx, self._source, source_local)
        return self._source.render_frame(source_ctx)


@dataclass
class JoinedClip(Clip):
    """A clip that plays two clips sequentially.

    First plays clip_a for its full duration, then clip_b.

    Args:
        _clip_a: First clip to play.
        _clip_b: Second clip to play.
    """

    _clip_a: Clip = field(default_factory=lambda: _placeholder_clip())
    _clip_b: Clip = field(default_factory=lambda: _placeholder_clip())

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render from clip_a or clip_b based on local frame position.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        a_duration = self._clip_a.duration
        if ctx.local_frame < a_duration:
            source_ctx = _make_source_ctx(ctx, self._clip_a, ctx.local_frame)
            return self._clip_a.render_frame(source_ctx)
        else:
            local_in_b = ctx.local_frame - a_duration
            source_ctx = _make_source_ctx(ctx, self._clip_b, local_in_b)
            return self._clip_b.render_frame(source_ctx)


@dataclass
class RepeatedClip(Clip):
    """A clip that repeats its source N times.

    Args:
        _source: The source clip to repeat.
        _repeat_count: Number of repetitions.
    """

    _source: Clip = field(default_factory=lambda: _placeholder_clip())
    _repeat_count: int = 1

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render by looping back into the source clip's frame range.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        source_duration = self._source.duration
        if source_duration <= 0:
            return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)
        source_local = ctx.local_frame % source_duration
        source_ctx = _make_source_ctx(ctx, self._source, source_local)
        return self._source.render_frame(source_ctx)


@dataclass
class FreezeFrameClip(Clip):
    """A clip that holds a single frame for a duration, then resumes.

    Playback: source[0..freeze_at] + hold(freeze_at) * freeze_duration +
    source[freeze_at+1..end].

    Args:
        _source: The source clip.
        _freeze_at: Frame index within the source to freeze.
        _freeze_duration: Number of frames to hold the frozen frame.
    """

    _source: Clip = field(default_factory=lambda: _placeholder_clip())
    _freeze_at: int = 0
    _freeze_duration: int = 0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render with a frozen frame inserted at the specified position.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        local = ctx.local_frame
        freeze_at = self._freeze_at
        freeze_dur = self._freeze_duration

        if local <= freeze_at:
            # Before or at freeze point: play source normally
            source_local = local
        elif local < freeze_at + freeze_dur:
            # During freeze: hold the frozen frame
            source_local = freeze_at
        else:
            # After freeze: resume from frame after freeze point
            source_local = local - freeze_dur

        source_ctx = _make_source_ctx(ctx, self._source, source_local)
        return self._source.render_frame(source_ctx)


@dataclass
class _SegmentInfo:
    """Internal segment metadata for concatenated clips.

    Args:
        global_start: Start frame in the concatenated timeline.
        global_end: End frame in the concatenated timeline (exclusive).
        clip: The source clip for this segment.
    """

    global_start: int
    global_end: int
    clip: Clip


@dataclass
class ConcatenatedClip(Clip):
    """A clip that plays multiple clips sequentially with optional transitions.

    When a transition is provided, adjacent clips overlap by
    transition_duration frames and are blended using the transition.

    Args:
        _clips: Source clips in playback order.
        _transition: Optional transition to apply between each pair.
        _transition_duration: Overlap duration in frames for transitions.
        _segments: Computed segment layout (internal).
    """

    _clips: list[Clip] = field(default_factory=list)
    _transition: Transition | None = None
    _transition_duration: int = 0
    _segments: list[_SegmentInfo] = field(default_factory=list)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render the correct clip or transition blend for this frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        local = ctx.local_frame

        # Check if we're in a transition region
        if self._transition is not None and self._transition_duration > 0:
            for i in range(len(self._segments) - 1):
                seg_a = self._segments[i]
                seg_b = self._segments[i + 1]
                # Transition region: where segments overlap
                t_start = seg_b.global_start
                t_end = seg_a.global_end
                if t_start <= local < t_end:
                    # Render both clips and blend
                    local_a = local - seg_a.global_start
                    local_b = local - seg_b.global_start
                    ctx_a = _make_source_ctx(ctx, seg_a.clip, local_a)
                    ctx_b = _make_source_ctx(ctx, seg_b.clip, local_b)
                    frame_a = seg_a.clip.render_frame(ctx_a)
                    frame_b = seg_b.clip.render_frame(ctx_b)
                    t_progress = (local - t_start) / max(t_end - t_start - 1, 1)
                    return self._transition.render_frame(frame_a, frame_b, t_progress)

        # Non-transition region: find the single active segment
        for seg in self._segments:
            if seg.global_start <= local < seg.global_end:
                source_local = local - seg.global_start
                source_ctx = _make_source_ctx(ctx, seg.clip, source_local)
                return seg.clip.render_frame(source_ctx)

        # Fallback: black frame
        return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)


def concatenate(
    clips: list[Clip],
    transition: Transition | None = None,
    transition_duration: int = 15,
) -> ConcatenatedClip:
    """Merge a list of clips sequentially with optional transitions.

    When a transition is provided, adjacent clips overlap by
    transition_duration frames and are blended using the transition.

    Args:
        clips: List of clips to concatenate.
        transition: Optional transition to apply between each pair.
        transition_duration: Duration of transitions in frames.

    Returns:
        A new ConcatenatedClip containing all clips.

    Raises:
        ValueError: If the clip list is empty or transition_duration
            exceeds any clip's duration.
    """
    if not clips:
        msg = "Cannot concatenate an empty list of clips"
        raise ValueError(msg)

    effective_t_dur = transition_duration if transition is not None else 0

    # Validate transition_duration doesn't exceed any clip duration
    if effective_t_dur > 0:
        for i, clip in enumerate(clips):
            if clip.duration < effective_t_dur:
                msg = (
                    f"Clip {i} duration ({clip.duration}) is less than "
                    f"transition_duration ({effective_t_dur})"
                )
                raise ValueError(msg)

    # Build segment layout
    segments: list[_SegmentInfo] = []
    offset = 0
    for i, clip in enumerate(clips):
        seg_start = offset
        seg_end = seg_start + clip.duration
        segments.append(_SegmentInfo(global_start=seg_start, global_end=seg_end, clip=clip))
        offset = seg_end
        if i < len(clips) - 1:
            offset -= effective_t_dur

    total_duration = offset

    result = ConcatenatedClip()
    result._clips = list(clips)
    result._transition = transition
    result._transition_duration = effective_t_dur
    result._segments = segments
    result.start = 0
    result.end = total_duration

    logger.debug(
        "concatenate",
        clip_count=len(clips),
        total_duration=total_duration,
        transition=type(transition).__name__ if transition else None,
    )

    return result


def _placeholder_clip() -> Clip:
    """Create a minimal placeholder clip for dataclass defaults.

    Returns:
        A minimal Clip instance that renders black frames.

    Raises:
        RuntimeError: If render_frame is called (should never happen
            on a properly initialized wrapper clip).
    """

    class _Placeholder(Clip):
        def render_frame(self, ctx: RenderContext) -> np.ndarray:
            return np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)

    return _Placeholder()
