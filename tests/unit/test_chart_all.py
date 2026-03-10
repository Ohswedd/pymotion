"""Tests for all chart clip types: Line, Pie, Area, Radar, Scatter, NumberCounter, ProgressBar."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.chart import (
    AreaChartClip,
    LineChartClip,
    NumberCounter,
    PieChartClip,
    ProgressBar,
    RadarChartClip,
    ScatterPlotClip,
)
from pymotion.utils.color import Color


def _ctx(
    frame: int = 0, w: int = 800, h: int = 600, fps: int = 30, duration: int = 90
) -> RenderContext:
    """Build a RenderContext for testing."""
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=Resolution(w, h),
        time_range=TimeRange(0, duration),
        local_frame=frame,
        progress=frame / duration if duration > 0 else 0.0,
    )


# ── LineChartClip ───────────────────────────────────────────────────────


class TestLineChartClip:
    """LineChartClip tests."""

    def test_render_basic(self) -> None:
        clip = LineChartClip(data=[10, 25, 15, 30, 20])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (600, 800, 4)
        assert frame.dtype == np.uint8

    def test_render_dict_data(self) -> None:
        clip = LineChartClip(data={"Jan": 10.0, "Feb": 20.0, "Mar": 15.0})
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)

    def test_render_callable_data(self) -> None:
        clip = LineChartClip(data=lambda f: [float(i + f) for i in range(5)])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=10))
        assert frame.shape == (600, 800, 4)

    def test_empty_data(self) -> None:
        clip = LineChartClip(data=[])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_animation_draw_on(self) -> None:
        clip = LineChartClip(data=[10, 20, 30], animate_duration=30)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f29 = clip.render_frame(_ctx(frame=29))
        assert not np.array_equal(f0, f29)

    def test_no_animation(self) -> None:
        clip = LineChartClip(data=[10, 20], animate_duration=0)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_show_fill(self) -> None:
        clip = LineChartClip(data=[10, 20, 30], show_fill=True)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)

    def test_show_dots_false(self) -> None:
        clip = LineChartClip(data=[10, 20], show_dots=False)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_single_point(self) -> None:
        clip = LineChartClip(data=[42.0])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_colors(self) -> None:
        clip = LineChartClip(data=[10, 20], line_colors=[Color.parse("#FF0000")])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    @pytest.mark.parametrize("theme", ["corporate", "minimal", "neon", "gradient"])
    def test_all_themes(self, theme: str) -> None:
        clip = LineChartClip(data=[10, 20, 30], theme=theme)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_with_title(self) -> None:
        clip = LineChartClip(data=[10, 20], title="Trend")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "LineChartClip")


# ── PieChartClip ────────────────────────────────────────────────────────


class TestPieChartClip:
    """PieChartClip tests."""

    def test_render_basic(self) -> None:
        clip = PieChartClip(data=[30, 20, 50])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)

    def test_render_dict_data(self) -> None:
        clip = PieChartClip(data={"A": 40.0, "B": 60.0})
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (600, 800, 4)

    def test_empty_data(self) -> None:
        clip = PieChartClip(data=[])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_zero_total(self) -> None:
        clip = PieChartClip(data=[0, 0])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_animation(self) -> None:
        clip = PieChartClip(data=[30, 70], animate_duration=30)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f29 = clip.render_frame(_ctx(frame=29))
        assert not np.array_equal(f0, f29)

    def test_donut_chart(self) -> None:
        clip = PieChartClip(data=[30, 70], inner_radius=0.5)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_no_labels(self) -> None:
        clip = PieChartClip(data=[30, 70], show_labels=False)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_colors(self) -> None:
        clip = PieChartClip(
            data=[30, 70],
            slice_colors=[Color.parse("#FF0000"), Color.parse("#00FF00")],
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    @pytest.mark.parametrize("theme", ["corporate", "minimal", "neon", "gradient"])
    def test_all_themes(self, theme: str) -> None:
        clip = PieChartClip(data=[30, 70], theme=theme)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "PieChartClip")


# ── AreaChartClip ───────────────────────────────────────────────────────


class TestAreaChartClip:
    """AreaChartClip tests."""

    def test_render_basic(self) -> None:
        clip = AreaChartClip(data=[5, 15, 10, 25, 20])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)

    def test_empty_data(self) -> None:
        clip = AreaChartClip(data=[])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_animation(self) -> None:
        clip = AreaChartClip(data=[10, 20, 30], animate_duration=20)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f20 = clip.render_frame(_ctx(frame=20))
        assert not np.array_equal(f0, f20)

    def test_fill_opacity(self) -> None:
        clip = AreaChartClip(data=[10, 20], fill_opacity=0.8)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_colors(self) -> None:
        clip = AreaChartClip(data=[10, 20], area_colors=[Color.parse("#FF0000")])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "AreaChartClip")


# ── RadarChartClip ──────────────────────────────────────────────────────


class TestRadarChartClip:
    """RadarChartClip tests."""

    def test_render_basic(self) -> None:
        clip = RadarChartClip(data=[80, 60, 90, 70, 50])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)

    def test_with_axes_labels(self) -> None:
        clip = RadarChartClip(
            data=[80, 60, 90, 70, 50],
            axes=["Speed", "Power", "Range", "Defense", "HP"],
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_empty_data(self) -> None:
        clip = RadarChartClip(data=[])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_animation(self) -> None:
        clip = RadarChartClip(data=[80, 60, 90], animate_duration=20)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f19 = clip.render_frame(_ctx(frame=19))
        assert not np.array_equal(f0, f19)

    def test_zero_values(self) -> None:
        clip = RadarChartClip(data=[0, 0, 0])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_fill_color(self) -> None:
        clip = RadarChartClip(data=[10, 20, 30], fill_color=Color.parse("#FF0000"))
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    @pytest.mark.parametrize("theme", ["corporate", "minimal", "neon", "gradient"])
    def test_all_themes(self, theme: str) -> None:
        clip = RadarChartClip(data=[80, 60, 90], theme=theme)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "RadarChartClip")


# ── ScatterPlotClip ─────────────────────────────────────────────────────


class TestScatterPlotClip:
    """ScatterPlotClip tests."""

    def test_render_basic(self) -> None:
        clip = ScatterPlotClip(x=[1, 2, 3, 4, 5], y=[2, 4, 1, 5, 3])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)

    def test_empty_data(self) -> None:
        clip = ScatterPlotClip(x=[], y=[])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_mismatched_lengths(self) -> None:
        """Uses min length."""
        clip = ScatterPlotClip(x=[1, 2, 3], y=[4, 5])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_animation(self) -> None:
        clip = ScatterPlotClip(x=[1, 2, 3], y=[4, 5, 6], animate_duration=20)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f19 = clip.render_frame(_ctx(frame=19))
        assert not np.array_equal(f0, f19)

    def test_same_values(self) -> None:
        clip = ScatterPlotClip(x=[5, 5, 5], y=[3, 3, 3])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_color_and_size(self) -> None:
        clip = ScatterPlotClip(
            x=[1, 2, 3],
            y=[4, 5, 6],
            point_color=Color.parse("#FF0000"),
            point_size=8.0,
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "ScatterPlotClip")


# ── NumberCounter ───────────────────────────────────────────────────────


class TestNumberCounter:
    """NumberCounter tests."""

    def test_render_basic(self) -> None:
        clip = NumberCounter(start_value=0, end_value=100, count_duration=60)
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (600, 800, 4)

    def test_at_start(self) -> None:
        clip = NumberCounter(start_value=0, end_value=100, count_duration=60)
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_after_animation(self) -> None:
        clip = NumberCounter(start_value=0, end_value=100, count_duration=30)
        clip.set_duration(60)
        f30 = clip.render_frame(_ctx(frame=30))
        f50 = clip.render_frame(_ctx(frame=50))
        np.testing.assert_array_equal(f30, f50)

    def test_custom_format(self) -> None:
        clip = NumberCounter(
            start_value=0,
            end_value=1000,
            count_duration=60,
            format_fn=lambda v: f"${v:,.0f}",
        )
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (600, 800, 4)

    def test_float_values(self) -> None:
        clip = NumberCounter(start_value=0.5, end_value=99.9, count_duration=30)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_negative_to_positive(self) -> None:
        clip = NumberCounter(start_value=-50, end_value=50, count_duration=30)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_font_size_color(self) -> None:
        clip = NumberCounter(
            start_value=0,
            end_value=100,
            size=48.0,
            color=Color.parse("#FF0000"),
        )
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "NumberCounter")


# ── ProgressBar ─────────────────────────────────────────────────────────


class TestProgressBar:
    """ProgressBar tests."""

    def test_render_basic(self) -> None:
        clip = ProgressBar(value=0.5)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_value_zero(self) -> None:
        clip = ProgressBar(value=0.0)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_value_one(self) -> None:
        clip = ProgressBar(value=1.0)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_callable_value(self) -> None:
        clip = ProgressBar(value=lambda f: f / 60.0)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f30 = clip.render_frame(_ctx(frame=30))
        assert not np.array_equal(f0, f30)

    def test_clamped_value(self) -> None:
        clip = ProgressBar(value=1.5)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_custom_colors(self) -> None:
        clip = ProgressBar(
            value=0.7,
            fill_color=Color.parse("#00FF00"),
            bg_color=Color.parse("#333333"),
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_custom_dimensions(self) -> None:
        clip = ProgressBar(value=0.5, bar_width=600, bar_height=50, radius=25)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_zero_radius(self) -> None:
        clip = ProgressBar(value=0.5, radius=0)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "ProgressBar")
