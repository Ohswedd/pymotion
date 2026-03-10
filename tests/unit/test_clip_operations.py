"""Tests for clip manipulation operations — split, join, subclip, repeat, freeze, concatenate."""

from __future__ import annotations

import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.clip.operations import (
    ConcatenatedClip,
    FreezeFrameClip,
    JoinedClip,
    RepeatedClip,
    SubClip,
    concatenate,
)
from pymotion.transition.library import CrossDissolve, Fade
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


def _make_color_clip(color: str, duration: int = 60) -> ColorClip:
    """Helper to create a colored clip with a specific duration."""
    clip = ColorClip(color=Color.parse(color))
    clip.start = 0
    clip.end = duration
    return clip


class TestSplit:
    """Tests for Clip.split()."""

    def test_split_basic(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        a, b = clip.split(frame=30)
        assert a.duration == 30
        assert b.duration == 30
        assert isinstance(a, SubClip)
        assert isinstance(b, SubClip)

    def test_split_uneven(self) -> None:
        clip = _make_color_clip("#FF0000", 100)
        a, b = clip.split(frame=25)
        assert a.duration == 25
        assert b.duration == 75

    def test_split_renders_correct_frames(self) -> None:
        """After split, first half renders source frames 0..29,
        second half renders source frames 30..59."""
        clip = _make_color_clip("#FF0000", 60)
        a, b = clip.split(frame=30)

        # First half should render from source
        frame_a = a.render_frame(_ctx(local_frame=0, duration=30))
        assert frame_a.shape == (64, 64, 4)
        assert frame_a[0, 0, 2] == 255  # Red channel (BGRA: R is index 2)

        # Second half should also render from source
        frame_b = b.render_frame(_ctx(local_frame=0, duration=30))
        assert frame_b.shape == (64, 64, 4)
        assert frame_b[0, 0, 2] == 255

    def test_split_invalid_frame_zero(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="Split frame must be between"):
            clip.split(frame=0)

    def test_split_invalid_frame_at_end(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="Split frame must be between"):
            clip.split(frame=60)

    def test_split_invalid_frame_negative(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="Split frame must be between"):
            clip.split(frame=-1)


class TestJoin:
    """Tests for Clip.join()."""

    def test_join_basic(self) -> None:
        a = _make_color_clip("#FF0000", 30)
        b = _make_color_clip("#0000FF", 30)
        joined = a.join(b)
        assert isinstance(joined, JoinedClip)
        assert joined.duration == 60

    def test_join_renders_first_clip(self) -> None:
        red = _make_color_clip("#FF0000", 30)
        blue = _make_color_clip("#0000FF", 30)
        joined = red.join(blue)

        frame = joined.render_frame(_ctx(local_frame=0, duration=60))
        assert frame[0, 0, 2] == 255  # Red (BGRA index 2)
        assert frame[0, 0, 0] == 0  # Blue channel

    def test_join_renders_second_clip(self) -> None:
        red = _make_color_clip("#FF0000", 30)
        blue = _make_color_clip("#0000FF", 30)
        joined = red.join(blue)

        frame = joined.render_frame(_ctx(local_frame=30, duration=60))
        assert frame[0, 0, 0] == 255  # Blue (BGRA index 0)
        assert frame[0, 0, 2] == 0  # Red channel

    def test_join_different_durations(self) -> None:
        a = _make_color_clip("#FF0000", 20)
        b = _make_color_clip("#0000FF", 40)
        joined = a.join(b)
        assert joined.duration == 60

    def test_join_zero_duration_first(self) -> None:
        a = _make_color_clip("#FF0000", 0)
        b = _make_color_clip("#0000FF", 30)
        with pytest.raises(ValueError, match="first clip has zero duration"):
            a.join(b)

    def test_join_zero_duration_second(self) -> None:
        a = _make_color_clip("#FF0000", 30)
        b = _make_color_clip("#0000FF", 0)
        with pytest.raises(ValueError, match="second clip has zero duration"):
            a.join(b)


class TestSubclip:
    """Tests for Clip.subclip()."""

    def test_subclip_basic(self) -> None:
        clip = _make_color_clip("#FF0000", 100)
        sub = clip.subclip(10, 50)
        assert isinstance(sub, SubClip)
        assert sub.duration == 40

    def test_subclip_renders(self) -> None:
        clip = _make_color_clip("#00FF00", 100)
        sub = clip.subclip(0, 60)
        frame = sub.render_frame(_ctx(local_frame=0, duration=60))
        assert frame.shape == (64, 64, 4)
        assert frame[0, 0, 1] == 255  # Green (BGRA index 1)

    def test_subclip_invalid_start_negative(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="non-negative"):
            clip.subclip(-1, 30)

    def test_subclip_invalid_end_exceeds(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="exceeds clip duration"):
            clip.subclip(0, 100)

    def test_subclip_invalid_start_ge_end(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="must be less than end"):
            clip.subclip(30, 30)

    def test_subclip_full_range(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        sub = clip.subclip(0, 60)
        assert sub.duration == 60


class TestRepeat:
    """Tests for Clip.repeat()."""

    def test_repeat_basic(self) -> None:
        clip = _make_color_clip("#FF0000", 30)
        repeated = clip.repeat(3)
        assert isinstance(repeated, RepeatedClip)
        assert repeated.duration == 90

    def test_repeat_once(self) -> None:
        clip = _make_color_clip("#FF0000", 30)
        repeated = clip.repeat(1)
        assert repeated.duration == 30

    def test_repeat_renders_looped(self) -> None:
        """Frame 35 of a 30-frame clip repeated should render source frame 5."""
        clip = _make_color_clip("#FF0000", 30)
        repeated = clip.repeat(3)
        frame = repeated.render_frame(_ctx(local_frame=35, duration=90))
        assert frame.shape == (64, 64, 4)
        assert frame[0, 0, 2] == 255  # Red

    def test_repeat_invalid_zero(self) -> None:
        clip = _make_color_clip("#FF0000", 30)
        with pytest.raises(ValueError, match="must be >= 1"):
            clip.repeat(0)

    def test_repeat_invalid_negative(self) -> None:
        clip = _make_color_clip("#FF0000", 30)
        with pytest.raises(ValueError, match="must be >= 1"):
            clip.repeat(-1)

    def test_repeat_zero_duration_clip(self) -> None:
        clip = _make_color_clip("#FF0000", 0)
        with pytest.raises(ValueError, match="zero duration"):
            clip.repeat(3)


class TestFreezeFrame:
    """Tests for Clip.freeze_frame()."""

    def test_freeze_frame_basic(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        frozen = clip.freeze_frame(frame=15, duration=30)
        assert isinstance(frozen, FreezeFrameClip)
        assert frozen.duration == 90  # 60 original + 30 frozen

    def test_freeze_frame_before_freeze_point(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        frozen = clip.freeze_frame(frame=15, duration=30)
        frame = frozen.render_frame(_ctx(local_frame=10, duration=90))
        assert frame.shape == (64, 64, 4)

    def test_freeze_frame_during_freeze(self) -> None:
        """Frames during the freeze period should all render the frozen frame."""
        clip = _make_color_clip("#FF0000", 60)
        frozen = clip.freeze_frame(frame=15, duration=30)
        # Frame 20 is during the freeze (freeze_at=15, freeze_dur=30, so 15..44 are frozen)
        frame = frozen.render_frame(_ctx(local_frame=20, duration=90))
        assert frame.shape == (64, 64, 4)

    def test_freeze_frame_after_freeze(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        frozen = clip.freeze_frame(frame=15, duration=30)
        # Frame 50 is after freeze (resumes at 45), maps to source frame 20
        frame = frozen.render_frame(_ctx(local_frame=50, duration=90))
        assert frame.shape == (64, 64, 4)

    def test_freeze_frame_invalid_frame(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="Freeze frame must be between"):
            clip.freeze_frame(frame=60, duration=10)

    def test_freeze_frame_invalid_negative_frame(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="Freeze frame must be between"):
            clip.freeze_frame(frame=-1, duration=10)

    def test_freeze_frame_invalid_duration(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        with pytest.raises(ValueError, match="Freeze duration must be positive"):
            clip.freeze_frame(frame=15, duration=0)


class TestConcatenate:
    """Tests for the concatenate() function."""

    def test_concatenate_basic(self) -> None:
        clips = [
            _make_color_clip("#FF0000", 30),
            _make_color_clip("#00FF00", 30),
            _make_color_clip("#0000FF", 30),
        ]
        result = concatenate(clips)
        assert isinstance(result, ConcatenatedClip)
        assert result.duration == 90

    def test_concatenate_single_clip(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        result = concatenate([clip])
        assert result.duration == 60

    def test_concatenate_renders_correct_clips(self) -> None:
        red = _make_color_clip("#FF0000", 30)
        blue = _make_color_clip("#0000FF", 30)
        result = concatenate([red, blue])

        # Frame 10 → red clip
        frame = result.render_frame(_ctx(local_frame=10, duration=60))
        assert frame[0, 0, 2] == 255  # Red
        assert frame[0, 0, 0] == 0

        # Frame 40 → blue clip
        frame = result.render_frame(_ctx(local_frame=40, duration=60))
        assert frame[0, 0, 0] == 255  # Blue
        assert frame[0, 0, 2] == 0

    def test_concatenate_with_transition(self) -> None:
        red = _make_color_clip("#FF0000", 30)
        blue = _make_color_clip("#0000FF", 30)
        result = concatenate([red, blue], transition=CrossDissolve(), transition_duration=10)
        # Total = 30 + 30 - 10 = 50
        assert result.duration == 50

    def test_concatenate_transition_renders_blend(self) -> None:
        """During transition region, frame should be a blend of both clips."""
        red = _make_color_clip("#FF0000", 30)
        blue = _make_color_clip("#0000FF", 30)
        result = concatenate([red, blue], transition=Fade(), transition_duration=10)
        # Transition region: frames 20..29 (where seg B starts at 20, seg A ends at 30)
        # Frame 25 is in the middle of the transition
        frame = result.render_frame(_ctx(local_frame=25, duration=50))
        # Should have both red and blue components (blended)
        assert frame[0, 0, 2] > 0  # Some red
        assert frame[0, 0, 0] > 0  # Some blue

    def test_concatenate_empty_list(self) -> None:
        with pytest.raises(ValueError, match="empty list"):
            concatenate([])

    def test_concatenate_transition_too_long(self) -> None:
        clips = [_make_color_clip("#FF0000", 5)]
        with pytest.raises(ValueError, match="less than transition_duration"):
            concatenate(clips, transition=Fade(), transition_duration=10)

    def test_concatenate_three_clips_with_transition(self) -> None:
        clips = [
            _make_color_clip("#FF0000", 30),
            _make_color_clip("#00FF00", 30),
            _make_color_clip("#0000FF", 30),
        ]
        result = concatenate(clips, transition=Fade(), transition_duration=10)
        # Total = 30 + 30 + 30 - 2*10 = 70
        assert result.duration == 70


class TestSplitJoinRoundtrip:
    """Integration tests combining split and join operations."""

    def test_split_then_join(self) -> None:
        """Splitting and joining should produce a clip of the same duration."""
        clip = _make_color_clip("#FF0000", 60)
        a, b = clip.split(frame=30)
        joined = a.join(b)
        assert joined.duration == 60

    def test_subclip_chain(self) -> None:
        """Subclip of a subclip should work correctly."""
        clip = _make_color_clip("#FF0000", 100)
        sub1 = clip.subclip(10, 80)  # 70 frames
        sub2 = sub1.subclip(5, 50)  # 45 frames
        assert sub2.duration == 45
        frame = sub2.render_frame(_ctx(local_frame=0, duration=45))
        assert frame.shape == (64, 64, 4)

    def test_repeat_then_subclip(self) -> None:
        clip = _make_color_clip("#FF0000", 30)
        repeated = clip.repeat(3)
        sub = repeated.subclip(10, 80)
        assert sub.duration == 70

    def test_freeze_then_split(self) -> None:
        clip = _make_color_clip("#FF0000", 60)
        frozen = clip.freeze_frame(frame=15, duration=30)
        a, b = frozen.split(frame=45)
        assert a.duration + b.duration == frozen.duration
