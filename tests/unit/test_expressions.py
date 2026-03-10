"""Tests for expression system — v1.3.5."""

from __future__ import annotations

import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.expressions import ExpressionContext, loop_in, loop_out, wiggle


def _ctx(
    frame: int = 0,
    local_frame: int | None = None,
    fps: int = 30,
    duration: int = 60,
) -> RenderContext:
    if local_frame is None:
        local_frame = frame
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=Resolution(width=200, height=100),
        time_range=TimeRange(start=0, end=duration),
        local_frame=local_frame,
        progress=local_frame / max(duration - 1, 1),
    )


class TestSetExpression:
    """Test clip.set_expression() basic API."""

    def test_set_expression_returns_self(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        result = clip.set_expression("position.x", lambda ctx: ctx.frame * 2.0)
        assert result is clip

    def test_invalid_property_raises(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        with pytest.raises(ValueError, match="Unsupported"):
            clip.set_expression("invalid_prop", lambda ctx: 0.0)

    def test_all_valid_properties(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        for prop in [
            "position.x",
            "position.y",
            "scale.x",
            "scale.y",
            "rotation",
            "opacity",
        ]:
            clip.set_expression(prop, lambda ctx: 1.0)

    def test_clear_expressions(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.set_expression("position.x", lambda ctx: 50.0)
        clip.clear_expressions()
        assert len(clip._expressions) == 0


class TestExpressionEvaluation:
    """Test that expressions modify clip properties during render."""

    def test_position_x(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        clip.set_expression("position.x", lambda ctx: ctx.frame * 3.0)
        ctx = _ctx(frame=10, local_frame=10)
        clip.render_with_effects(ctx)
        assert clip._position.x == 30.0

    def test_position_y(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        clip.set_expression("position.y", lambda ctx: 100.0)
        ctx = _ctx(frame=0)
        clip.render_with_effects(ctx)
        assert clip._position.y == 100.0

    def test_scale_x(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        clip.set_expression("scale.x", lambda ctx: 2.0 + ctx.progress)
        ctx = _ctx(frame=30, local_frame=30)
        clip.render_with_effects(ctx)
        assert clip._scale.x > 2.0

    def test_rotation(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        clip.set_expression("rotation", lambda ctx: ctx.frame * 6.0)
        ctx = _ctx(frame=15)
        clip.render_with_effects(ctx)
        assert clip._rotation == 90.0

    def test_opacity_clamped(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        clip.set_expression("opacity", lambda ctx: 5.0)  # Over 1.0
        ctx = _ctx(frame=0)
        clip.render_with_effects(ctx)
        assert clip._opacity == 1.0

    def test_opacity_clamped_negative(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        clip.set_expression("opacity", lambda ctx: -1.0)
        ctx = _ctx(frame=0)
        clip.render_with_effects(ctx)
        assert clip._opacity == 0.0


class TestExpressionContext:
    """Test ExpressionContext fields."""

    def test_context_fields(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(60)
        captured: list[ExpressionContext] = []

        def capture(ctx: ExpressionContext) -> float:
            captured.append(ctx)
            return 0.0

        clip.set_expression("position.x", capture)
        ctx = _ctx(frame=15, local_frame=15, fps=30, duration=60)
        clip.render_with_effects(ctx)

        assert len(captured) == 1
        ec = captured[0]
        assert ec.frame == 15
        assert ec.local_frame == 15
        assert ec.fps == 30
        assert ec.comp_width == 200
        assert ec.comp_height == 100
        assert 0.0 <= ec.progress <= 1.0
        assert ec.time == 15.0 / 30.0


class TestExpressionLinking:
    """Test expressions linking between clips."""

    def test_link_opacity(self) -> None:
        clip_a = ColorClip("#FF0000").set_duration(60)
        clip_a.set_opacity(0.7)

        clip_b = ColorClip("#00FF00").set_duration(60)
        clip_b.set_expression("opacity", lambda ctx: clip_a.opacity_at(ctx.frame))

        ctx = _ctx(frame=0)
        clip_b.render_with_effects(ctx)
        assert clip_b._opacity == 0.7


class TestWiggle:
    """Test wiggle expression helper."""

    def test_returns_callable(self) -> None:
        fn = wiggle(2.0, 50.0)
        assert callable(fn)

    def test_produces_values_in_range(self) -> None:
        fn = wiggle(2.0, 50.0, seed=42)
        for i in range(100):
            ec_i = ExpressionContext(
                frame=i,
                time=i / 30.0,
                fps=30,
                comp_width=200,
                comp_height=100,
                progress=i / 99.0,
                local_frame=i,
            )
            val = fn(ec_i)
            assert -50.0 <= val <= 50.0

    def test_different_seeds_different_results(self) -> None:
        fn_a = wiggle(2.0, 50.0, seed=0)
        fn_b = wiggle(2.0, 50.0, seed=999)
        ec = ExpressionContext(
            frame=10,
            time=10.0 / 30.0,
            fps=30,
            comp_width=200,
            comp_height=100,
            progress=0.1,
            local_frame=10,
        )
        assert fn_a(ec) != fn_b(ec)

    def test_same_seed_reproducible(self) -> None:
        fn = wiggle(2.0, 50.0, seed=42)
        ec = ExpressionContext(
            frame=5,
            time=5.0 / 30.0,
            fps=30,
            comp_width=200,
            comp_height=100,
            progress=0.05,
            local_frame=5,
        )
        assert fn(ec) == fn(ec)


class TestLoopIn:
    """Test loop_in expression helper."""

    def test_loops_first_n_frames(self) -> None:
        def ramp(ctx: ExpressionContext) -> float:
            return float(ctx.local_frame)

        looped = loop_in(10, ramp)
        # Frame 5 → should be 5
        ec5 = ExpressionContext(
            frame=5,
            time=5 / 30,
            fps=30,
            comp_width=200,
            comp_height=100,
            progress=0.05,
            local_frame=5,
        )
        assert looped(ec5) == 5.0

        # Frame 15 → 15 % 10 = 5
        ec15 = ExpressionContext(
            frame=15,
            time=15 / 30,
            fps=30,
            comp_width=200,
            comp_height=100,
            progress=0.15,
            local_frame=15,
        )
        assert looped(ec15) == 5.0

    def test_zero_duration(self) -> None:
        fn = loop_in(0, lambda ctx: 42.0)
        ec = ExpressionContext(
            frame=0,
            time=0,
            fps=30,
            comp_width=200,
            comp_height=100,
            progress=0,
            local_frame=0,
        )
        assert fn(ec) == 42.0


class TestLoopOut:
    """Test loop_out expression helper."""

    def test_loops(self) -> None:
        def ramp(ctx: ExpressionContext) -> float:
            return float(ctx.local_frame)

        looped = loop_out(10, ramp)
        ec = ExpressionContext(
            frame=25,
            time=25 / 30,
            fps=30,
            comp_width=200,
            comp_height=100,
            progress=0.25,
            local_frame=25,
        )
        # 25 % 10 = 5
        assert looped(ec) == 5.0


class TestExpressionExports:
    """Test public API exports."""

    def test_importable(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "ExpressionContext")
        assert hasattr(pm, "ExpressionFn")
        assert hasattr(pm, "wiggle")
        assert hasattr(pm, "loop_in")
        assert hasattr(pm, "loop_out")
