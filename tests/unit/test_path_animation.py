"""Tests for path animation — v1.3.6."""

from __future__ import annotations

import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.clip.shape import ShapeClip
from pymotion.path_animation import (
    StrokeClip,
    _line_length,
    _parse_svg_path,
    follow_path,
    morph_paths,
)
from pymotion.utils.math import Vec2


def _ctx(
    frame: int = 0,
    local_frame: int | None = None,
    fps: int = 30,
    duration: int = 60,
    width: int = 200,
    height: int = 100,
) -> RenderContext:
    if local_frame is None:
        local_frame = frame
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=Resolution(width=width, height=height),
        time_range=TimeRange(start=0, end=duration),
        local_frame=local_frame,
        progress=local_frame / max(duration - 1, 1),
    )


# ---------------------------------------------------------------------------
# SVG path parsing
# ---------------------------------------------------------------------------


class TestParseSvgPath:
    """Test minimal SVG path parser."""

    def test_empty_string(self) -> None:
        assert _parse_svg_path("") == []

    def test_move_only(self) -> None:
        segs = _parse_svg_path("M 10 20")
        assert segs == []

    def test_line(self) -> None:
        segs = _parse_svg_path("M 0 0 L 100 0")
        assert len(segs) == 1
        assert segs[0].start.x == 0.0
        assert segs[0].end.x == 100.0
        assert segs[0].cp1 is None

    def test_relative_line(self) -> None:
        segs = _parse_svg_path("M 10 10 l 50 0")
        assert len(segs) == 1
        assert segs[0].end.x == 60.0
        assert segs[0].end.y == 10.0

    def test_cubic_bezier(self) -> None:
        segs = _parse_svg_path("M 0 0 C 10 20 30 40 50 60")
        assert len(segs) == 1
        assert segs[0].cp1 is not None
        assert segs[0].cp2 is not None
        assert segs[0].end.x == 50.0

    def test_relative_cubic(self) -> None:
        segs = _parse_svg_path("M 10 10 c 5 5 15 15 20 20")
        assert len(segs) == 1
        assert segs[0].cp1 is not None
        assert segs[0].cp1.x == 15.0
        assert segs[0].end.x == 30.0

    def test_close_path(self) -> None:
        segs = _parse_svg_path("M 0 0 L 100 0 L 100 100 Z")
        assert len(segs) == 3  # two lines + closing segment

    def test_close_path_no_extra_if_at_start(self) -> None:
        segs = _parse_svg_path("M 0 0 L 100 0 L 0 0 Z")
        assert len(segs) == 2  # no extra close segment needed

    def test_multiple_segments(self) -> None:
        segs = _parse_svg_path("M 0 0 L 50 0 L 50 50 L 0 50 Z")
        assert len(segs) == 4

    def test_segment_lengths_positive(self) -> None:
        segs = _parse_svg_path("M 0 0 L 100 0 L 100 100")
        for seg in segs:
            assert seg.length > 0


class TestLineLength:
    """Test line length helper."""

    def test_horizontal(self) -> None:
        assert _line_length(Vec2(0, 0), Vec2(3, 0)) == 3.0

    def test_diagonal(self) -> None:
        length = _line_length(Vec2(0, 0), Vec2(3, 4))
        assert abs(length - 5.0) < 1e-10


# ---------------------------------------------------------------------------
# follow_path
# ---------------------------------------------------------------------------


class TestFollowPath:
    """Test follow_path expression setup."""

    def test_returns_clip(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        result = follow_path(clip, "M 0 0 L 100 0", 60)
        assert result is clip

    def test_sets_position_expressions(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        follow_path(clip, "M 0 0 L 100 0", 60)
        assert "position.x" in clip._expressions
        assert "position.y" in clip._expressions

    def test_sets_rotation_when_align(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        follow_path(clip, "M 0 0 L 100 0", 60, align=True)
        assert "rotation" in clip._expressions

    def test_no_rotation_when_no_align(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        follow_path(clip, "M 0 0 L 100 0", 60, align=False)
        assert "rotation" not in clip._expressions

    def test_position_at_start(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        follow_path(clip, "M 10 20 L 110 20", 60)
        ctx = _ctx(frame=0, local_frame=0, duration=60)
        clip.render_with_effects(ctx)
        assert abs(clip._position.x - 10.0) < 1e-6
        assert abs(clip._position.y - 20.0) < 1e-6

    def test_position_at_end(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        follow_path(clip, "M 0 0 L 100 0", 60)
        ctx = _ctx(frame=59, local_frame=59, duration=60)
        clip.render_with_effects(ctx)
        assert abs(clip._position.x - 100.0) < 1e-6

    def test_position_at_midpoint(self) -> None:
        clip = ColorClip("#FF0000").set_duration(61)
        follow_path(clip, "M 0 0 L 100 0", 61)
        ctx = _ctx(frame=30, local_frame=30, duration=61)
        clip.render_with_effects(ctx)
        assert abs(clip._position.x - 50.0) < 1e-6

    def test_empty_path_raises(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        with pytest.raises(ValueError, match="empty"):
            follow_path(clip, "", 60)

    def test_zero_duration_raises(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        with pytest.raises(ValueError, match="positive"):
            follow_path(clip, "M 0 0 L 100 0", 0)

    def test_clip_method(self) -> None:
        clip = ColorClip("#FF0000").set_duration(60)
        result = clip.follow_path("M 0 0 L 100 0", 60)
        assert result is clip
        assert "position.x" in clip._expressions


# ---------------------------------------------------------------------------
# StrokeClip
# ---------------------------------------------------------------------------


class TestStrokeClip:
    """Test StrokeClip rendering."""

    def test_init_defaults(self) -> None:
        clip = StrokeClip()
        assert clip.trim_start == 0.0
        assert clip.trim_end == 1.0
        assert clip.stroke_width == 2.0

    def test_init_with_path(self) -> None:
        clip = StrokeClip(path="M 0 0 L 100 0", stroke_width=3.0)
        assert len(clip._segments) == 1
        assert clip._total_length > 0
        assert clip.stroke_width == 3.0

    def test_render_produces_frame(self) -> None:
        clip = StrokeClip(path="M 10 50 L 190 50", stroke_width=4.0)
        clip.set_duration(30)
        ctx = _ctx(frame=0, duration=30)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        assert frame.dtype.name == "uint8"

    def test_render_empty_path(self) -> None:
        clip = StrokeClip()
        clip.set_duration(30)
        ctx = _ctx(frame=0, duration=30)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        # Empty path → all zeros
        assert frame.sum() == 0

    def test_trim_start_equals_trim_end(self) -> None:
        clip = StrokeClip(path="M 0 0 L 100 0", trim_start=0.5, trim_end=0.5)
        clip.set_duration(30)
        ctx = _ctx(frame=0, duration=30)
        frame = clip.render_frame(ctx)
        assert frame.sum() == 0  # nothing visible

    def test_stroke_color(self) -> None:
        clip = StrokeClip(
            path="M 10 50 L 190 50",
            stroke_color="#FF0000",
            stroke_width=4.0,
        )
        clip.set_duration(30)
        ctx = _ctx(frame=0, duration=30)
        frame = clip.render_frame(ctx)
        # Should have some non-zero pixels (red stroke)
        assert frame.sum() > 0

    def test_partial_trim(self) -> None:
        clip_full = StrokeClip(path="M 10 50 L 190 50", stroke_width=4.0)
        clip_full.set_duration(30)

        clip_half = StrokeClip(
            path="M 10 50 L 190 50",
            trim_start=0.0,
            trim_end=0.5,
            stroke_width=4.0,
        )
        clip_half.set_duration(30)

        ctx = _ctx(frame=0, duration=30)
        frame_full = clip_full.render_frame(ctx)
        frame_half = clip_half.render_frame(ctx)

        # Half trim should have fewer non-zero pixels
        assert frame_half.sum() < frame_full.sum()


# ---------------------------------------------------------------------------
# morph_paths
# ---------------------------------------------------------------------------


class TestMorphPaths:
    """Test path morphing interpolation."""

    def test_morph_at_zero(self) -> None:
        path_a = "M 0 0 L 100 0"
        path_b = "M 0 0 L 200 0"
        result = morph_paths(path_a, path_b, 0.0)
        assert "M 0.00 0.00" in result
        assert "L 100.00 0.00" in result

    def test_morph_at_one(self) -> None:
        path_a = "M 0 0 L 100 0"
        path_b = "M 0 0 L 200 0"
        result = morph_paths(path_a, path_b, 1.0)
        assert "L 200.00 0.00" in result

    def test_morph_at_half(self) -> None:
        path_a = "M 0 0 L 100 0"
        path_b = "M 0 0 L 200 0"
        result = morph_paths(path_a, path_b, 0.5)
        assert "L 150.00 0.00" in result

    def test_morph_mismatched_raises(self) -> None:
        path_a = "M 0 0 L 100 0"
        path_b = "M 0 0 L 100 0 L 200 100"
        with pytest.raises(ValueError, match="mismatch"):
            morph_paths(path_a, path_b, 0.5)

    def test_morph_empty_paths(self) -> None:
        assert morph_paths("M 0 0", "M 10 10", 0.5) == ""

    def test_morph_bezier_curves(self) -> None:
        path_a = "M 0 0 C 10 20 30 40 50 60"
        path_b = "M 0 0 C 20 40 60 80 100 120"
        result = morph_paths(path_a, path_b, 0.5)
        assert result.startswith("M ")
        assert "C " in result

    def test_morph_clamps_progress(self) -> None:
        path_a = "M 0 0 L 100 0"
        path_b = "M 0 0 L 200 0"
        result_neg = morph_paths(path_a, path_b, -1.0)
        result_zero = morph_paths(path_a, path_b, 0.0)
        assert result_neg == result_zero

        result_over = morph_paths(path_a, path_b, 2.0)
        result_one = morph_paths(path_a, path_b, 1.0)
        assert result_over == result_one


class TestShapeClipMorph:
    """Test ShapeClip.morph method."""

    def test_morph_sets_shape_type(self) -> None:
        clip = ShapeClip.rect(0, 0, 100, 100)
        clip.morph("M 0 0 L 100 0", "M 0 0 L 200 0", 0.5)
        assert clip.shape_type == "path"

    def test_morph_returns_self(self) -> None:
        clip = ShapeClip.rect(0, 0, 100, 100)
        result = clip.morph("M 0 0 L 100 0", "M 0 0 L 200 0", 0.5)
        assert result is clip

    def test_morph_clears_cache(self) -> None:
        clip = ShapeClip.rect(0, 0, 100, 100)
        clip._cached_frame = "fake"  # type: ignore[assignment]
        clip.morph("M 0 0 L 100 0", "M 0 0 L 200 0", 0.5)
        assert clip._cached_frame is None


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


class TestPathAnimationExports:
    """Test public API exports."""

    def test_importable(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "StrokeClip")
        assert hasattr(pm, "follow_path")
        assert hasattr(pm, "morph_paths")
