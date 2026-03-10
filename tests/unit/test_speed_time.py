"""Tests for speed & time operations — speed, speed_ramp, reverse, time_remap."""

from __future__ import annotations

import math

import pytest

from pymotion.animation.keyframe import Keyframe, KeyframeTrack
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.clip.operations import (
    ReversedClip,
    SpeedClip,
    SpeedRampClip,
    TimeRemappedClip,
)
from pymotion.utils.color import Color


def _ctx(local_frame: int = 0, duration: int = 60) -> RenderContext:
    """Helper to create a RenderContext for testing."""
    return RenderContext(
        frame=local_frame,
        fps=30,
        resolution=Resolution(width=64, height=64),
        time_range=TimeRange(start=0, end=duration),
        local_frame=local_frame,
        progress=local_frame / max(duration - 1, 1),
    )


def _make_clip(color: str = "#FF0000", duration: int = 60) -> ColorClip:
    """Create a colored clip for testing."""
    clip = ColorClip(color=Color.parse(color))
    clip.start = 0
    clip.end = duration
    return clip


class TestSpeed:
    """Tests for Clip.speed()."""

    def test_speed_double(self) -> None:
        clip = _make_clip(duration=60)
        fast = clip.speed(2.0)
        assert isinstance(fast, SpeedClip)
        assert fast.duration == 30  # ceil(60 / 2.0)

    def test_speed_half(self) -> None:
        clip = _make_clip(duration=60)
        slow = clip.speed(0.5)
        assert isinstance(slow, SpeedClip)
        assert slow.duration == 120  # ceil(60 / 0.5)

    def test_speed_renders_correctly(self) -> None:
        clip = _make_clip(duration=60)
        fast = clip.speed(2.0)
        frame = fast.render_frame(_ctx(local_frame=0, duration=30))
        assert frame.shape == (64, 64, 4)
        assert frame[0, 0, 2] == 255  # Red

    def test_speed_double_duration(self) -> None:
        """Speed 2.0 halves the duration."""
        clip = _make_clip(duration=100)
        fast = clip.speed(2.0)
        assert fast.duration == 50

    def test_speed_fractional(self) -> None:
        clip = _make_clip(duration=60)
        result = clip.speed(1.5)
        assert result.duration == math.ceil(60 / 1.5)

    def test_speed_invalid_too_low(self) -> None:
        clip = _make_clip(duration=60)
        with pytest.raises(ValueError, match="between 0.1 and 10.0"):
            clip.speed(0.05)

    def test_speed_invalid_too_high(self) -> None:
        clip = _make_clip(duration=60)
        with pytest.raises(ValueError, match="between 0.1 and 10.0"):
            clip.speed(15.0)

    def test_speed_zero_duration(self) -> None:
        clip = _make_clip(duration=0)
        with pytest.raises(ValueError, match="zero duration"):
            clip.speed(2.0)

    def test_speed_with_optical_flow(self) -> None:
        """Optical flow mode should still render (falls back to linear blend)."""
        clip = _make_clip(duration=60)
        slow = clip.speed(0.5, interpolation="optical_flow")
        assert slow._interpolation == "optical_flow"
        frame = slow.render_frame(_ctx(local_frame=5, duration=120))
        assert frame.shape == (64, 64, 4)

    def test_speed_optical_flow_exact_frame(self) -> None:
        """When source frame is exact integer, should not interpolate."""
        clip = _make_clip(duration=60)
        slow = clip.speed(0.5, interpolation="optical_flow")
        # local_frame=0 * 0.5 = 0.0, exact frame
        frame = slow.render_frame(_ctx(local_frame=0, duration=120))
        assert frame.shape == (64, 64, 4)


class TestSpeedRamp:
    """Tests for Clip.speed_ramp()."""

    def test_speed_ramp_constant(self) -> None:
        """Constant speed ramp of 1.0 should preserve duration."""
        clip = _make_clip(duration=60)
        ramped = clip.speed_ramp([(0, 1.0), (60, 1.0)])
        assert isinstance(ramped, SpeedRampClip)
        assert ramped.duration == 60

    def test_speed_ramp_double_speed(self) -> None:
        """Constant 2x ramp should halve the duration."""
        clip = _make_clip(duration=60)
        ramped = clip.speed_ramp([(0, 2.0)])
        assert ramped.duration == 30

    def test_speed_ramp_renders(self) -> None:
        clip = _make_clip(duration=60)
        ramped = clip.speed_ramp([(0, 1.0), (30, 2.0)])
        frame = ramped.render_frame(_ctx(local_frame=0, duration=ramped.duration))
        assert frame.shape == (64, 64, 4)

    def test_speed_ramp_empty_keyframes(self) -> None:
        clip = _make_clip(duration=60)
        with pytest.raises(ValueError, match="cannot be empty"):
            clip.speed_ramp([])

    def test_speed_ramp_zero_duration(self) -> None:
        clip = _make_clip(duration=0)
        with pytest.raises(ValueError, match="zero duration"):
            clip.speed_ramp([(0, 1.0)])

    def test_speed_ramp_negative_factor(self) -> None:
        clip = _make_clip(duration=60)
        with pytest.raises(ValueError, match="must be positive"):
            clip.speed_ramp([(0, -1.0)])

    def test_speed_ramp_varying(self) -> None:
        """Variable speed should produce duration between min and max."""
        clip = _make_clip(duration=60)
        ramped = clip.speed_ramp([(0, 1.0), (30, 2.0), (60, 1.0)])
        # Duration should be less than 60 (since speed > 1 for part)
        assert ramped.duration < 60
        assert ramped.duration > 0


class TestReverse:
    """Tests for Clip.reverse()."""

    def test_reverse_basic(self) -> None:
        clip = _make_clip(duration=60)
        rev = clip.reverse()
        assert isinstance(rev, ReversedClip)
        assert rev.duration == 60

    def test_reverse_renders(self) -> None:
        clip = _make_clip(duration=60)
        rev = clip.reverse()
        frame = rev.render_frame(_ctx(local_frame=0, duration=60))
        assert frame.shape == (64, 64, 4)
        # Frame 0 of reversed = frame 59 of source (still red)
        assert frame[0, 0, 2] == 255

    def test_reverse_zero_duration(self) -> None:
        clip = _make_clip(duration=0)
        with pytest.raises(ValueError, match="zero duration"):
            clip.reverse()

    def test_reverse_last_frame(self) -> None:
        """Last frame of reversed should map to source frame 0."""
        clip = _make_clip(duration=60)
        rev = clip.reverse()
        frame = rev.render_frame(_ctx(local_frame=59, duration=60))
        assert frame.shape == (64, 64, 4)


class TestTimeRemap:
    """Tests for Clip.time_remap()."""

    def test_time_remap_basic(self) -> None:
        clip = _make_clip(duration=60)
        curve = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=59, value=59.0),
            ]
        )
        remapped = clip.time_remap(curve)
        assert isinstance(remapped, TimeRemappedClip)
        assert remapped.duration == 60

    def test_time_remap_slow_motion(self) -> None:
        """Remap to play first 30 frames over 60 output frames."""
        clip = _make_clip(duration=60)
        curve = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=59, value=30.0),
            ]
        )
        remapped = clip.time_remap(curve)
        frame = remapped.render_frame(_ctx(local_frame=30, duration=60))
        assert frame.shape == (64, 64, 4)

    def test_time_remap_renders(self) -> None:
        clip = _make_clip(duration=60)
        curve = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=0.0),
                Keyframe(frame=59, value=59.0),
            ]
        )
        remapped = clip.time_remap(curve)
        frame = remapped.render_frame(_ctx(local_frame=0, duration=60))
        assert frame.shape == (64, 64, 4)

    def test_time_remap_empty_curve(self) -> None:
        clip = _make_clip(duration=60)
        with pytest.raises(ValueError, match="at least one keyframe"):
            clip.time_remap(KeyframeTrack(keyframes=[]))

    def test_time_remap_reverse_via_curve(self) -> None:
        """Use time_remap to create reverse playback."""
        clip = _make_clip(duration=60)
        curve = KeyframeTrack(
            keyframes=[
                Keyframe(frame=0, value=59.0),
                Keyframe(frame=59, value=0.0),
            ]
        )
        remapped = clip.time_remap(curve)
        frame = remapped.render_frame(_ctx(local_frame=0, duration=60))
        assert frame.shape == (64, 64, 4)


class TestSpeedIntegration:
    """Integration tests combining speed and other operations."""

    def test_speed_then_reverse(self) -> None:
        clip = _make_clip(duration=60)
        fast = clip.speed(2.0)
        rev = fast.reverse()
        assert rev.duration == 30

    def test_reverse_then_speed(self) -> None:
        clip = _make_clip(duration=60)
        rev = clip.reverse()
        fast = rev.speed(2.0)
        assert fast.duration == 30

    def test_speed_preserves_rendering(self) -> None:
        """Speed-changed clip should still render valid frames."""
        clip = _make_clip(duration=60)
        fast = clip.speed(2.0)
        for i in range(0, fast.duration, 10):
            frame = fast.render_frame(_ctx(local_frame=i, duration=fast.duration))
            assert frame.shape == (64, 64, 4)
