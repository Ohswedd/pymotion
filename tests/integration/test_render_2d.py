"""Integration tests for 2D rendering pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.shape import ShapeClip
from pymotion.clip.text import TextClip
from pymotion.composition import Composition


def _make_ctx(
    width: int = 320,
    height: int = 240,
    frame: int = 0,
) -> RenderContext:
    """Create a simple render context for testing."""
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(width=width, height=height),
        time_range=TimeRange(start=0, end=30),
        local_frame=frame,
        progress=frame / 29 if frame < 30 else 1.0,
    )


class TestColorClipRender:
    """Test ColorClip rendering."""

    def test_solid_black(self) -> None:
        clip = ColorClip("#000000")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        assert frame.dtype == np.uint8
        assert frame[120, 160, 0] == 0  # B
        assert frame[120, 160, 3] == 255  # A

    def test_solid_red(self) -> None:
        clip = ColorClip("#FF0000")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame[120, 160, 2] == 255  # R in BGRA

    def test_solid_white(self) -> None:
        clip = ColorClip("#FFFFFF")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame[120, 160, 0] == 255  # B
        assert frame[120, 160, 1] == 255  # G
        assert frame[120, 160, 2] == 255  # R


class TestShapeClipRender:
    """Test ShapeClip rendering."""

    def test_circle_renders(self) -> None:
        clip = ShapeClip.circle(cx=160, cy=120, r=50, fill="#FF0000")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        # Center pixel should be red
        assert frame[120, 160, 2] > 200  # R

    def test_rect_renders(self) -> None:
        clip = ShapeClip.rect(x=50, y=50, w=100, h=100, fill="#00FF00")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        # Pixel inside rect should be green
        assert frame[100, 100, 1] > 200  # G

    def test_outside_shape_transparent(self) -> None:
        clip = ShapeClip.circle(cx=160, cy=120, r=10, fill="#FF0000")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        # Corner should be transparent
        assert frame[0, 0, 3] == 0


class TestGradientClipRender:
    """Test GradientClip rendering."""

    def test_renders_gradient(self) -> None:
        clip = GradientClip("#000000", "#FFFFFF")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        # Top should be darker than bottom
        top_val = int(frame[10, 160, 0])
        bottom_val = int(frame[230, 160, 0])
        assert bottom_val > top_val


class TestCompositionRender:
    """Test composition-level rendering."""

    def test_render_single_frame(self) -> None:
        comp = Composition(width=320, height=240, fps=30, duration=10)
        comp.add(ColorClip("#FF0000").set_duration(10))
        frame = comp._render_frame(0)
        assert frame.shape == (240, 320, 4)
        assert frame[120, 160, 2] == 255  # Red

    def test_render_with_shape_overlay(self) -> None:
        comp = Composition(width=320, height=240, fps=30, duration=10)
        comp.add(
            ColorClip("#000000").set_duration(10),
            ShapeClip.circle(cx=160, cy=120, r=50, fill="#FFFFFF").set_duration(10),
        )
        frame = comp._render_frame(0)
        # Center should be white (circle)
        assert frame[120, 160, 0] > 200
        # Corner should be black (background)
        assert frame[0, 0, 0] == 0


class TestTextClipRender:
    """Test TextClip rendering."""

    def test_text_renders_to_frame(self) -> None:
        """TextClip should render text pixels onto a frame."""
        try:
            clip = TextClip("Hello", font="Helvetica", size=24.0)
            clip.set_duration(30)
            ctx = _make_ctx()
            frame = clip.render_frame(ctx)
            assert frame.shape == (240, 320, 4)
            assert frame.dtype == np.uint8
            # Should have some non-zero alpha pixels (text rendered)
            assert np.any(frame[:, :, 3] > 0)
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_text_empty_renders_transparent(self) -> None:
        """Empty TextClip should render transparent."""
        try:
            clip = TextClip("", font="Helvetica", size=24.0)
            clip.set_duration(30)
            ctx = _make_ctx()
            frame = clip.render_frame(ctx)
            assert frame.shape == (240, 320, 4)
            assert np.all(frame[:, :, 3] == 0)
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_text_in_composition(self) -> None:
        """TextClip should render correctly within a composition."""
        try:
            comp = Composition(width=320, height=240, fps=30, duration=10)
            comp.add(
                ColorClip("#000000").set_duration(10),
                TextClip("Test", font="Helvetica", size=48.0, color="#FFFFFF").set_duration(10),
            )
            frame = comp._render_frame(0)
            assert frame.shape == (240, 320, 4)
            # Should have white text pixels somewhere
            white_pixels = (frame[:, :, 0] > 200) & (frame[:, :, 1] > 200) & (frame[:, :, 2] > 200)
            assert np.any(white_pixels)
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")


class TestGradientClipTypes:
    """Test gradient clip variants (radial, conic)."""

    def test_radial_gradient(self) -> None:
        clip = GradientClip("#FFFFFF", "#000000", gradient_type="radial")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        # Center should be lighter than corner
        center_val = int(frame[120, 160, 0])
        corner_val = int(frame[0, 0, 0])
        assert center_val > corner_val

    def test_conic_gradient(self) -> None:
        clip = GradientClip("#FF0000", "#0000FF", gradient_type="conic")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        # Should have some color variation
        assert frame.std() > 0
