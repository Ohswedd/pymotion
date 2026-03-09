"""Tests to boost coverage for spring, audio effects, shape, image, and base clips."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pymotion.animation.spring import spring
from pymotion.audio.effects import EQ, Compressor, EQBand, Limiter
from pymotion.clip.base import (
    BlendMode,
    Clip,
    RenderContext,
    Resolution,
    TimeRange,
)
from pymotion.clip.image import ImageClip
from pymotion.clip.shape import ShapeClip
from pymotion.utils.math import Vec2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyClip(Clip):
    """Minimal concrete Clip for testing base class methods."""

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        w = ctx.resolution.width
        h = ctx.resolution.height
        return np.zeros((h, w, 4), dtype=np.uint8)


def _make_ctx(
    frame: int = 0,
    fps: int = 30,
    width: int = 200,
    height: int = 200,
) -> RenderContext:
    res = Resolution(width, height)
    tr = TimeRange(start=0, end=90)
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=res,
        time_range=tr,
        local_frame=frame,
        progress=frame / 90.0 if frame < 90 else 1.0,
    )


# ===========================================================================
# Spring animation
# ===========================================================================


class TestSpring:
    """Tests for pymotion.animation.spring.spring()."""

    def test_underdamped_boundaries(self) -> None:
        fn = spring(stiffness=180.0, damping=12.0, mass=1.0)
        assert fn(0.0) == 0.0
        assert fn(1.0) == 1.0

    def test_underdamped_midpoint_in_range(self) -> None:
        fn = spring(stiffness=180.0, damping=12.0, mass=1.0)
        val = fn(0.5)
        assert 0.0 <= val <= 2.0  # may overshoot but should be reasonable

    def test_underdamped_negative_t(self) -> None:
        fn = spring()
        assert fn(-0.5) == 0.0

    def test_underdamped_t_above_one(self) -> None:
        fn = spring()
        assert fn(1.5) == 1.0

    def test_critically_damped(self) -> None:
        # zeta = damping / (2 * sqrt(stiffness * mass))
        # For zeta = 1: damping = 2 * sqrt(stiffness * mass)
        stiffness = 100.0
        mass = 1.0
        damping = 2 * (stiffness * mass) ** 0.5  # = 20.0
        fn = spring(stiffness=stiffness, damping=damping, mass=mass)
        assert fn(0.0) == 0.0
        assert fn(1.0) == 1.0
        val = fn(0.5)
        assert 0.0 <= val <= 1.5

    def test_critically_damped_negative_t(self) -> None:
        damping = 2 * (100.0 * 1.0) ** 0.5
        fn = spring(stiffness=100.0, damping=damping, mass=1.0)
        assert fn(-1.0) == 0.0

    def test_overdamped(self) -> None:
        fn = spring(stiffness=100.0, damping=50.0, mass=1.0)
        assert fn(0.0) == 0.0
        assert fn(1.0) == 1.0
        val = fn(0.5)
        assert 0.0 <= val <= 1.5

    def test_overdamped_negative_t(self) -> None:
        fn = spring(stiffness=100.0, damping=50.0, mass=1.0)
        assert fn(-0.1) == 0.0

    def test_overdamped_t_above_one(self) -> None:
        fn = spring(stiffness=100.0, damping=50.0, mass=1.0)
        assert fn(2.0) == 1.0

    def test_invalid_stiffness(self) -> None:
        with pytest.raises(ValueError, match="stiffness"):
            spring(stiffness=0)

    def test_negative_stiffness(self) -> None:
        with pytest.raises(ValueError, match="stiffness"):
            spring(stiffness=-5)

    def test_negative_damping(self) -> None:
        with pytest.raises(ValueError, match="damping"):
            spring(damping=-1)

    def test_invalid_mass(self) -> None:
        with pytest.raises(ValueError, match="mass"):
            spring(mass=0)

    def test_negative_mass(self) -> None:
        with pytest.raises(ValueError, match="mass"):
            spring(mass=-2)

    def test_zero_damping_underdamped(self) -> None:
        fn = spring(stiffness=100.0, damping=0.0, mass=1.0)
        assert fn(0.0) == 0.0
        assert fn(1.0) == 1.0

    def test_overdamped_approaches_one(self) -> None:
        fn = spring(stiffness=100.0, damping=50.0, mass=1.0)
        # Overdamped: value near end should be close to 1.0
        val = fn(0.9)
        assert 0.9 <= val <= 1.1


# ===========================================================================
# Audio effects — construction and parameter setting only
# ===========================================================================


class TestAudioEffects:
    """Tests for audio effect dataclass construction (no pedalboard needed)."""

    def test_eq_band_defaults(self) -> None:
        band = EQBand()
        assert band.frequency == 1000.0
        assert band.gain_db == 0.0
        assert band.q == 1.0
        assert band.band_type == "peak"

    def test_eq_band_custom(self) -> None:
        band = EQBand(frequency=500.0, gain_db=-3.0, q=2.0, band_type="low_shelf")
        assert band.frequency == 500.0
        assert band.band_type == "low_shelf"

    def test_eq_empty_bands_passthrough(self) -> None:
        eq = EQ(bands=[])
        samples = np.random.default_rng(42).random((1000, 2)).astype(np.float32)
        result = eq.apply(samples, 44100)
        np.testing.assert_array_equal(result, samples)

    def test_eq_default_construction(self) -> None:
        eq = EQ()
        assert eq.bands == []

    def test_compressor_defaults(self) -> None:
        comp = Compressor()
        assert comp.threshold_db == -20.0
        assert comp.ratio == 4.0
        assert comp.attack_ms == 10.0
        assert comp.release_ms == 100.0

    def test_compressor_custom(self) -> None:
        comp = Compressor(threshold_db=-10.0, ratio=2.0, attack_ms=5.0, release_ms=50.0)
        assert comp.threshold_db == -10.0
        assert comp.ratio == 2.0

    def test_limiter_defaults(self) -> None:
        lim = Limiter()
        assert lim.threshold_db == -1.0
        assert lim.release_ms == 100.0

    def test_limiter_custom(self) -> None:
        lim = Limiter(threshold_db=-3.0, release_ms=200.0)
        assert lim.threshold_db == -3.0
        assert lim.release_ms == 200.0


# ===========================================================================
# ShapeClip factory methods and rendering
# ===========================================================================


class TestShapeClip:
    """Tests for ShapeClip factory methods and render_frame."""

    def test_circle_factory(self) -> None:
        clip = ShapeClip.circle(cx=50, cy=50, r=25, fill="red")
        assert clip.shape_type == "circle"
        assert clip.params["cx"] == 50
        assert clip.params["cy"] == 50
        assert clip.params["r"] == 25
        assert clip.fill_color.r == 1.0

    def test_circle_with_stroke(self) -> None:
        clip = ShapeClip.circle(cx=50, cy=50, r=25, fill="red", stroke="blue", stroke_width=2.0)
        assert clip.stroke_color is not None
        assert clip.stroke_width == 2.0

    def test_ellipse_factory(self) -> None:
        clip = ShapeClip.ellipse(cx=100, cy=100, rx=60, ry=40, fill="#00FF00")
        assert clip.shape_type == "ellipse"
        assert clip.params["rx"] == 60
        assert clip.params["ry"] == 40

    def test_polygon_factory(self) -> None:
        pts = [(0, 0), (100, 0), (50, 80)]
        clip = ShapeClip.polygon(points=pts, fill="yellow")
        assert clip.shape_type == "polygon"
        assert clip.params["n_points"] == 3.0
        assert clip.params["x0"] == 0
        assert clip.params["y1"] == 0
        assert clip.params["x2"] == 50

    def test_line_factory(self) -> None:
        clip = ShapeClip.line(x1=10, y1=20, x2=90, y2=80, color="white", width=3.0)
        assert clip.shape_type == "line"
        assert clip.stroke_color is not None
        assert clip.stroke_width == 3.0
        assert clip.params["x1"] == 10

    def test_rect_factory(self) -> None:
        clip = ShapeClip.rect(x=5, y=10, w=50, h=30, fill="blue")
        assert clip.shape_type == "rect"
        assert clip.params["w"] == 50

    def test_rect_with_stroke(self) -> None:
        clip = ShapeClip.rect(fill="red", stroke="#00FF00", stroke_width=4.0)
        assert clip.stroke_color is not None
        assert clip.stroke_width == 4.0

    def test_set_fill(self) -> None:
        clip = ShapeClip.rect(fill="red")
        result = clip.set_fill("blue")
        assert result is clip
        assert clip.fill_color.b == 1.0

    def test_render_rect(self) -> None:
        clip = ShapeClip.rect(x=0, y=0, w=100, h=100, fill="#FF0000")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)
        assert frame.dtype == np.uint8

    def test_render_circle(self) -> None:
        clip = ShapeClip.circle(cx=100, cy=100, r=50, fill="green")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)

    def test_render_ellipse(self) -> None:
        clip = ShapeClip.ellipse(cx=100, cy=100, rx=80, ry=40, fill="blue")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)

    def test_render_polygon(self) -> None:
        pts = [(10, 10), (190, 10), (100, 190)]
        clip = ShapeClip.polygon(points=pts, fill="cyan")
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)

    def test_render_line(self) -> None:
        clip = ShapeClip.line(x1=10, y1=10, x2=190, y2=190, color="white", width=2.0)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)

    def test_render_rect_with_stroke(self) -> None:
        clip = ShapeClip.rect(x=10, y=10, w=80, h=80, fill="red", stroke="blue", stroke_width=3.0)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)

    def test_polygon_less_than_two_points(self) -> None:
        clip = ShapeClip.polygon(points=[(0, 0)], fill="red")
        ctx = _make_ctx()
        # Should not crash; polygon with < 2 points just doesn't draw
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)


# ===========================================================================
# ImageClip
# ===========================================================================


class TestImageClip:
    """Tests for ImageClip construction and rendering."""

    def test_construction(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.fromarray(np.zeros((100, 100, 4), dtype=np.uint8), mode="RGBA")
            img.save(f.name)
            clip = ImageClip(source=f.name)
            assert clip.source == Path(f.name)

    def test_render_frame(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            arr = np.full((50, 80, 4), 128, dtype=np.uint8)
            img = Image.fromarray(arr, mode="RGBA")
            img.save(f.name)
            clip = ImageClip(source=f.name)
            ctx = _make_ctx()
            frame = clip.render_frame(ctx)
            assert frame.shape == (200, 200, 4)
            assert frame.dtype == np.uint8

    def test_render_frame_caching(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            arr = np.full((50, 80, 4), 200, dtype=np.uint8)
            img = Image.fromarray(arr, mode="RGBA")
            img.save(f.name)
            clip = ImageClip(source=f.name)
            ctx = _make_ctx()
            frame1 = clip.render_frame(ctx)
            frame2 = clip.render_frame(ctx)
            np.testing.assert_array_equal(frame1, frame2)

    def test_render_frame_different_resolution(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            arr = np.full((50, 80, 4), 100, dtype=np.uint8)
            img = Image.fromarray(arr, mode="RGBA")
            img.save(f.name)
            clip = ImageClip(source=f.name)
            ctx1 = _make_ctx(width=200, height=200)
            frame1 = clip.render_frame(ctx1)
            assert frame1.shape == (200, 200, 4)
            ctx2 = _make_ctx(width=100, height=100)
            # Should reload because resolution changed
            frame2 = clip.render_frame(ctx2)
            assert frame2.shape == (100, 100, 4)

    def test_file_not_found(self) -> None:
        clip = ImageClip(source="/nonexistent/path/image.png")
        ctx = _make_ctx()
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            clip.render_frame(ctx)

    def test_bgra_conversion(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create an image with known RGBA: pure red (255,0,0,255)
            arr = np.zeros((10, 10, 4), dtype=np.uint8)
            arr[:, :, 0] = 255  # R
            arr[:, :, 3] = 255  # A
            img = Image.fromarray(arr, mode="RGBA")
            img.save(f.name)
            clip = ImageClip(source=f.name)
            ctx = _make_ctx(width=10, height=10)
            frame = clip.render_frame(ctx)
            # BGRA: red channel should be in index 2
            assert frame[5, 5, 2] == 255  # R -> channel 2
            assert frame[5, 5, 0] == 0  # B -> channel 0


# ===========================================================================
# Base clip — Resolution, TimeRange, Clip methods
# ===========================================================================


class TestResolution:
    """Tests for Resolution validation."""

    def test_valid_resolution(self) -> None:
        r = Resolution(1920, 1080)
        assert r.width == 1920
        assert r.height == 1080

    def test_zero_width(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Resolution(0, 1080)

    def test_negative_height(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Resolution(1920, -1)

    def test_odd_width(self) -> None:
        with pytest.raises(ValueError, match="even"):
            Resolution(1921, 1080)

    def test_odd_height(self) -> None:
        with pytest.raises(ValueError, match="even"):
            Resolution(1920, 1081)


class TestTimeRange:
    """Tests for TimeRange."""

    def test_duration(self) -> None:
        tr = TimeRange(start=10, end=40)
        assert tr.duration == 30

    def test_zero_duration(self) -> None:
        tr = TimeRange(start=5, end=5)
        assert tr.duration == 0


class TestClipBase:
    """Tests for Clip base class methods."""

    def test_set_position(self) -> None:
        clip = _DummyClip()
        result = clip.set_position(100.0, 200.0)
        assert result is clip
        assert clip._position == Vec2(100.0, 200.0)

    def test_set_scale_uniform(self) -> None:
        clip = _DummyClip()
        result = clip.set_scale(2.0)
        assert result is clip
        assert clip._scale == Vec2(2.0, 2.0)

    def test_set_scale_nonuniform(self) -> None:
        clip = _DummyClip()
        clip.set_scale(2.0, 3.0)
        assert clip._scale == Vec2(2.0, 3.0)

    def test_set_rotation(self) -> None:
        clip = _DummyClip()
        result = clip.set_rotation(45.0)
        assert result is clip
        assert clip._rotation == 45.0

    def test_set_opacity_valid(self) -> None:
        clip = _DummyClip()
        result = clip.set_opacity(0.5)
        assert result is clip
        assert clip._opacity == 0.5

    def test_set_opacity_zero(self) -> None:
        clip = _DummyClip()
        clip.set_opacity(0.0)
        assert clip._opacity == 0.0

    def test_set_opacity_one(self) -> None:
        clip = _DummyClip()
        clip.set_opacity(1.0)
        assert clip._opacity == 1.0

    def test_set_opacity_too_high(self) -> None:
        clip = _DummyClip()
        with pytest.raises(ValueError, match="Opacity"):
            clip.set_opacity(1.5)

    def test_set_opacity_negative(self) -> None:
        clip = _DummyClip()
        with pytest.raises(ValueError, match="Opacity"):
            clip.set_opacity(-0.1)

    def test_set_duration(self) -> None:
        clip = _DummyClip()
        clip.start = 10
        result = clip.set_duration(30)
        assert result is clip
        assert clip.end == 40
        assert clip.duration == 30

    def test_at(self) -> None:
        clip = _DummyClip()
        clip.start = 0
        clip.end = 30
        result = clip.at(10)
        assert result is clip
        assert clip.start == 10
        assert clip.end == 40
        assert clip.duration == 30

    def test_duration_property(self) -> None:
        clip = _DummyClip()
        clip.start = 5
        clip.end = 15
        assert clip.duration == 10

    def test_blend_mode_default(self) -> None:
        clip = _DummyClip()
        assert clip.blend_mode == BlendMode.NORMAL

    def test_render_frame_dummy(self) -> None:
        clip = _DummyClip()
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        assert frame.shape == (200, 200, 4)

    def test_method_chaining(self) -> None:
        clip = (
            _DummyClip()
            .set_position(10.0, 20.0)
            .set_scale(1.5)
            .set_rotation(90.0)
            .set_opacity(0.8)
            .set_duration(60)
            .at(5)
        )
        assert clip._position == Vec2(10.0, 20.0)
        assert clip._scale == Vec2(1.5, 1.5)
        assert clip._rotation == 90.0
        assert clip._opacity == 0.8
        assert clip.start == 5
        assert clip.end == 65
