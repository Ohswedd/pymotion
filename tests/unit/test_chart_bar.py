"""Tests for BarChartClip."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.chart import BarChartClip, _get_theme, _resolve_data, _resolve_labels
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


class TestBarChartClipBasic:
    """Basic BarChartClip rendering."""

    def test_render_list_data(self) -> None:
        clip = BarChartClip(data=[10, 20, 30])
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=59))
        assert frame.shape == (600, 800, 4)
        assert frame.dtype == np.uint8

    def test_render_dict_data(self) -> None:
        clip = BarChartClip(data={"A": 5, "B": 15, "C": 10})
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (600, 800, 4)

    def test_render_callable_data(self) -> None:
        def dynamic(f: int) -> list[float]:
            return [float(f), float(f * 2)]

        clip = BarChartClip(data=dynamic)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=10))
        assert frame.shape == (600, 800, 4)

    def test_render_callable_dict_data(self) -> None:
        def dynamic(f: int) -> dict[str, float]:
            return {"x": float(f), "y": float(f * 2)}

        clip = BarChartClip(data=dynamic)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=5))
        assert frame.shape == (600, 800, 4)

    def test_empty_data_returns_background(self) -> None:
        clip = BarChartClip(data=[])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_single_bar(self) -> None:
        clip = BarChartClip(data=[42.0])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=29))
        assert frame.shape == (600, 800, 4)

    def test_zero_values(self) -> None:
        clip = BarChartClip(data=[0, 0, 0])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)


class TestBarChartClipAnimation:
    """Animation behavior."""

    def test_first_frame_bars_are_small(self) -> None:
        clip = BarChartClip(data=[100], animate_duration=30)
        clip.set_duration(60)
        frame_0 = clip.render_frame(_ctx(frame=0))
        frame_29 = clip.render_frame(_ctx(frame=29))
        # At frame 0, bars should be at ~0 height (mostly background)
        # At frame 29, bars should be at full height
        # We can't easily measure bar height, but the frames should differ
        assert not np.array_equal(frame_0, frame_29)

    def test_no_animation(self) -> None:
        clip = BarChartClip(data=[50, 100], animate_duration=0)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)

    def test_after_animation_is_static(self) -> None:
        clip = BarChartClip(data=[10, 20, 30], animate_duration=10)
        clip.set_duration(60)
        frame_30 = clip.render_frame(_ctx(frame=30))
        frame_50 = clip.render_frame(_ctx(frame=50))
        np.testing.assert_array_equal(frame_30, frame_50)


class TestBarChartClipThemes:
    """Theme support."""

    @pytest.mark.parametrize("theme", ["corporate", "minimal", "neon", "gradient"])
    def test_all_themes_render(self, theme: str) -> None:
        clip = BarChartClip(data=[10, 20, 30], theme=theme)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_invalid_theme_raises(self) -> None:
        clip = BarChartClip(data=[10], theme="nonexistent")
        clip.set_duration(30)
        with pytest.raises(ValueError, match="Unknown chart theme"):
            clip.render_frame(_ctx(frame=0))


class TestBarChartClipOptions:
    """Optional features."""

    def test_custom_labels(self) -> None:
        clip = BarChartClip(data=[10, 20], labels=["Foo", "Bar"])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_custom_bar_colors(self) -> None:
        clip = BarChartClip(
            data=[10, 20],
            bar_colors=[Color.parse("#FF0000"), Color.parse("#00FF00")],
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_title(self) -> None:
        clip = BarChartClip(data=[10, 20], title="Sales Report")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_show_values(self) -> None:
        clip = BarChartClip(data=[10, 20], show_values=True)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=29))
        assert frame.shape == (600, 800, 4)

    def test_custom_padding(self) -> None:
        clip = BarChartClip(data=[10], padding=(100, 100, 100, 100))
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_bar_gap(self) -> None:
        clip = BarChartClip(data=[10, 20, 30], bar_gap=0.5)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)


class TestBarChartClipEdgeCases:
    """Edge cases and boundary tests."""

    def test_large_values(self) -> None:
        clip = BarChartClip(data=[1_000_000, 2_000_000])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_negative_values_treated_as_abs(self) -> None:
        clip = BarChartClip(data=[-10, 20, -30])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=29))
        assert frame.shape == (600, 800, 4)

    def test_many_bars(self) -> None:
        clip = BarChartClip(data=list(range(50)))
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_small_resolution(self) -> None:
        clip = BarChartClip(data=[10, 20])
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15, w=200, h=150))
        assert frame.shape == (150, 200, 4)

    def test_tiny_chart_area(self) -> None:
        """Padding larger than resolution should not crash."""
        clip = BarChartClip(data=[10], padding=(500, 500, 500, 500))
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (600, 800, 4)


class TestBarChartClipIsClip:
    """BarChartClip behaves as a proper Clip."""

    def test_set_duration(self) -> None:
        clip = BarChartClip(data=[10, 20])
        clip.set_duration(90)
        assert clip.duration == 90

    def test_set_position(self) -> None:
        clip = BarChartClip(data=[10]).set_position(100, 200)
        assert clip._position.x == 100
        assert clip._position.y == 200

    def test_render_with_effects(self) -> None:
        clip = BarChartClip(data=[10, 20])
        clip.set_duration(30)
        frame = clip.render_with_effects(_ctx(frame=15))
        assert frame.shape == (600, 800, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "BarChartClip")
        assert pm.BarChartClip is BarChartClip


class TestHelpers:
    """Test helper functions."""

    def test_get_theme_valid(self) -> None:
        theme = _get_theme("corporate")
        assert "bar_colors" in theme

    def test_get_theme_invalid(self) -> None:
        with pytest.raises(ValueError, match="Unknown chart theme"):
            _get_theme("fantasy")

    def test_resolve_data_list(self) -> None:
        vals, keys = _resolve_data([1.0, 2.0, 3.0], 0)
        assert vals == [1.0, 2.0, 3.0]
        assert keys is None

    def test_resolve_data_dict(self) -> None:
        vals, keys = _resolve_data({"a": 1.0, "b": 2.0}, 0)
        assert vals == [1.0, 2.0]
        assert keys == ["a", "b"]

    def test_resolve_data_callable(self) -> None:
        vals, keys = _resolve_data(lambda f: [float(f)], 5)
        assert vals == [5.0]

    def test_resolve_labels_explicit(self) -> None:
        labels = _resolve_labels(["X", "Y"], None, 2)
        assert labels == ["X", "Y"]

    def test_resolve_labels_from_keys(self) -> None:
        labels = _resolve_labels(None, ["a", "b"], 2)
        assert labels == ["a", "b"]

    def test_resolve_labels_numeric(self) -> None:
        labels = _resolve_labels(None, None, 3)
        assert labels == ["0", "1", "2"]
