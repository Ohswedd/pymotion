"""Tests for motion tracking and stabilization."""

from __future__ import annotations

import pytest

from pymotion.animation.keyframe import KeyframeTrack
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.tracking import (
    MotionTracker,
    StabilizedClip,
    _smooth,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2


def _make_clip(color: str = "#FF0000", duration: int = 30) -> ColorClip:
    clip = ColorClip(color=Color.parse(color))
    clip.start = 0
    clip.end = duration
    return clip


def _ctx(local_frame: int = 0, duration: int = 30) -> RenderContext:
    return RenderContext(
        frame=local_frame,
        fps=30,
        resolution=Resolution(width=64, height=64),
        time_range=TimeRange(start=0, end=duration),
        local_frame=local_frame,
        progress=local_frame / max(duration - 1, 1),
    )


class TestMotionTracker:
    """Tests for MotionTracker."""

    def test_tracker_basic(self) -> None:
        clip = _make_clip(duration=10)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        data = tracker.track()
        assert isinstance(data, dict)
        assert len(data) == 10
        assert all(isinstance(v, Vec2) for v in data.values())

    def test_tracker_returns_positions(self) -> None:
        clip = _make_clip(duration=5)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        data = tracker.track()
        # For a static color clip, positions should be near the initial center
        center = Vec2(20.0, 20.0)  # 10 + 20//2 = 20
        for pos in data.values():
            assert abs(pos.x - center.x) < 50
            assert abs(pos.y - center.y) < 50

    def test_tracker_zero_duration(self) -> None:
        clip = _make_clip(duration=0)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        with pytest.raises(RuntimeError, match="zero duration"):
            tracker.track()

    def test_to_keyframes(self) -> None:
        clip = _make_clip(duration=10)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        tracker.track()
        kf = tracker.to_keyframes("position")
        assert isinstance(kf, KeyframeTrack)
        assert len(kf.keyframes) == 10

    def test_to_keyframes_no_data(self) -> None:
        clip = _make_clip(duration=10)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        with pytest.raises(RuntimeError, match="No tracking data"):
            tracker.to_keyframes("position")


class TestStabilize:
    """Tests for Clip.stabilize()."""

    def test_stabilize_basic(self) -> None:
        clip = _make_clip(duration=10)
        stabilized = clip.stabilize(smoothing=5)
        assert isinstance(stabilized, StabilizedClip)
        assert stabilized.duration == 10

    def test_stabilize_renders(self) -> None:
        clip = _make_clip(duration=10)
        stabilized = clip.stabilize(smoothing=3)
        frame = stabilized.render_frame(_ctx(local_frame=0, duration=10))
        assert frame.shape == (64, 64, 4)

    def test_stabilize_zero_duration(self) -> None:
        clip = _make_clip(duration=0)
        with pytest.raises(ValueError, match="zero duration"):
            clip.stabilize()

    def test_stabilize_invalid_smoothing(self) -> None:
        clip = _make_clip(duration=10)
        with pytest.raises(ValueError, match="Smoothing must be"):
            clip.stabilize(smoothing=0)


class TestFollowTracker:
    """Tests for Clip.follow_tracker()."""

    def test_follow_tracker(self) -> None:
        source = _make_clip(duration=10)
        target = _make_clip(duration=10)
        tracker = MotionTracker(clip=source, region=(10, 10, 20, 20))
        tracker.track()
        result = target.follow_tracker(tracker, prop="position")
        assert result is target

    def test_follow_tracker_with_offset(self) -> None:
        source = _make_clip(duration=10)
        target = _make_clip(duration=10)
        tracker = MotionTracker(clip=source, region=(10, 10, 20, 20))
        tracker.track()
        target.follow_tracker(tracker, prop="position", offset=(5.0, 5.0))
        # Position should be set
        assert target._position.x != 0 or target._position.y != 0

    def test_follow_tracker_invalid_prop(self) -> None:
        source = _make_clip(duration=10)
        target = _make_clip(duration=10)
        tracker = MotionTracker(clip=source, region=(10, 10, 20, 20))
        tracker.track()
        with pytest.raises(ValueError, match="Unsupported property"):
            target.follow_tracker(tracker, prop="rotation")

    def test_follow_tracker_no_data(self) -> None:
        source = _make_clip(duration=10)
        target = _make_clip(duration=10)
        tracker = MotionTracker(clip=source, region=(10, 10, 20, 20))
        with pytest.raises(RuntimeError, match="no data"):
            target.follow_tracker(tracker)

    def test_follow_tracker_invalid_type(self) -> None:
        target = _make_clip(duration=10)
        with pytest.raises(TypeError, match="MotionTracker"):
            target.follow_tracker("not_a_tracker")  # type: ignore[arg-type]


class TestSmooth:
    """Tests for _smooth utility."""

    def test_smooth_identity(self) -> None:
        values = [1.0, 1.0, 1.0, 1.0, 1.0]
        result = _smooth(values, 3)
        assert all(abs(v - 1.0) < 0.01 for v in result)

    def test_smooth_step(self) -> None:
        values = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
        result = _smooth(values, 3)
        assert len(result) == len(values)
        # Middle values should be between 0 and 1
        assert 0.0 < result[2] < 1.0 or 0.0 < result[3] < 1.0

    def test_smooth_window_1(self) -> None:
        values = [1.0, 2.0, 3.0]
        result = _smooth(values, 1)
        assert result == values
