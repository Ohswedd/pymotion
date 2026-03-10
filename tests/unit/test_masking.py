"""Tests for the masking system — v1.3.3."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.composition import Composition, get_shared_frame_cache
from pymotion.masking import (
    BezierMask,
    BezierPoint,
    LinearGradientMask,
    MaskOp,
    RadialGradientMask,
    TextMask,
    TrackMatte,
    apply_masks,
)
from pymotion.utils.math import Vec2


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_shared_frame_cache().clear()


def _ctx(
    width: int = 200,
    height: int = 100,
    frame: int = 0,
    duration: int = 60,
) -> RenderContext:
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(width=width, height=height),
        time_range=TimeRange(start=0, end=duration),
        local_frame=frame,
        progress=frame / max(duration - 1, 1),
    )


# ---------------------------------------------------------------------------
# BezierMask
# ---------------------------------------------------------------------------


class TestBezierMask:
    """Test BezierMask rasterization and animation."""

    def _rect_points(self, x: float, y: float, w: float, h: float) -> list[BezierPoint]:
        """Create rectangle bezier points (no curves)."""
        return [
            BezierPoint(vertex=Vec2(x, y)),
            BezierPoint(vertex=Vec2(x + w, y)),
            BezierPoint(vertex=Vec2(x + w, y + h)),
            BezierPoint(vertex=Vec2(x, y + h)),
        ]

    def test_render_mask_shape(self) -> None:
        mask = BezierMask(points=self._rect_points(10, 10, 100, 50))
        result = mask.render_mask(_ctx())
        assert result.shape == (100, 200)
        assert result.dtype == np.uint8

    def test_rect_mask_coverage(self) -> None:
        mask = BezierMask(points=self._rect_points(10, 10, 100, 50))
        result = mask.render_mask(_ctx())
        # Inside rectangle should be 255
        assert result[30, 50] == 255
        # Outside should be 0
        assert result[0, 0] == 0

    def test_empty_points_returns_zeros(self) -> None:
        mask = BezierMask(points=[])
        result = mask.render_mask(_ctx())
        assert result.max() == 0

    def test_single_point_returns_zeros(self) -> None:
        mask = BezierMask(points=[BezierPoint(vertex=Vec2(50, 50))])
        result = mask.render_mask(_ctx())
        assert result.max() == 0

    def test_curved_path(self) -> None:
        points = [
            BezierPoint(
                vertex=Vec2(50, 10),
                out_handle=Vec2(150, 10),
            ),
            BezierPoint(
                vertex=Vec2(150, 90),
                in_handle=Vec2(150, 90),
            ),
            BezierPoint(vertex=Vec2(50, 90)),
        ]
        mask = BezierMask(points=points)
        result = mask.render_mask(_ctx())
        assert result.shape == (100, 200)
        # Some pixels should be non-zero
        assert result.max() > 0

    def test_feather(self) -> None:
        mask = BezierMask(
            points=self._rect_points(20, 20, 80, 40),
            feather=5.0,
        )
        result = mask.render_mask(_ctx())
        # Mask should still have visible region
        assert result.max() > 0

    def test_invert(self) -> None:
        mask_normal = BezierMask(points=self._rect_points(10, 10, 100, 50))
        mask_inverted = BezierMask(points=self._rect_points(10, 10, 100, 50), invert=True)
        ctx = _ctx()
        normal = mask_normal.render_mask(ctx)
        # For inverted, we process via _process_single_mask
        from pymotion.masking import _process_single_mask

        inverted = _process_single_mask(mask_inverted, ctx, 0.0, 0.0, True, 1.0)
        # Inside rect: normal=255, inverted=0
        assert normal[30, 50] == 255
        assert inverted[30, 50] == 0

    def test_animation_keyframes(self) -> None:
        pts_start = self._rect_points(10, 10, 50, 30)
        pts_end = self._rect_points(100, 50, 50, 30)

        mask = BezierMask(points=pts_start)
        mask.set_points_at(0, pts_start)
        mask.set_points_at(60, pts_end)

        # At frame 0, should match start
        result_0 = mask.render_mask(_ctx(frame=0))
        assert result_0[20, 30] == 255  # Inside start rect

        # At frame 60, should match end
        result_60 = mask.render_mask(_ctx(frame=60))
        assert result_60[60, 120] == 255  # Inside end rect

    def test_animation_interpolation_midpoint(self) -> None:
        pts_a = [BezierPoint(vertex=Vec2(0, 0))] * 3 + [
            BezierPoint(vertex=Vec2(100, 0)),
            BezierPoint(vertex=Vec2(100, 100)),
            BezierPoint(vertex=Vec2(0, 100)),
        ]
        pts_a = self._rect_points(0, 0, 100, 50)
        pts_b = self._rect_points(100, 50, 100, 50)

        mask = BezierMask(points=pts_a)
        mask.set_points_at(0, pts_a)
        mask.set_points_at(60, pts_b)

        # At frame 30, points should be interpolated to midpoint
        points_mid = mask._get_points_at_frame(30)
        assert len(points_mid) == 4
        # First vertex should be at (50, 25) — midpoint of (0,0) and (100,50)
        assert abs(points_mid[0].vertex.x - 50.0) < 1.0
        assert abs(points_mid[0].vertex.y - 25.0) < 1.0

    def test_point_count_mismatch_raises(self) -> None:
        mask = BezierMask(points=self._rect_points(0, 0, 100, 50))
        with pytest.raises(ValueError, match="Point count mismatch"):
            mask.set_points_at(10, [BezierPoint(vertex=Vec2(0, 0))])


# ---------------------------------------------------------------------------
# LinearGradientMask
# ---------------------------------------------------------------------------


class TestLinearGradientMask:
    """Test linear gradient mask."""

    def test_shape(self) -> None:
        mask = LinearGradientMask(start=Vec2(0, 0), end=Vec2(200, 0))
        result = mask.render_mask(_ctx())
        assert result.shape == (100, 200)
        assert result.dtype == np.uint8

    def test_gradient_direction(self) -> None:
        mask = LinearGradientMask(start=Vec2(0, 0), end=Vec2(200, 0))
        result = mask.render_mask(_ctx())
        # Left edge should be dark, right edge should be bright
        assert result[50, 0] < result[50, 199]

    def test_zero_length_gradient(self) -> None:
        mask = LinearGradientMask(start=Vec2(50, 50), end=Vec2(50, 50))
        result = mask.render_mask(_ctx())
        # Zero length gradient returns all 255
        assert result.min() == 255


# ---------------------------------------------------------------------------
# RadialGradientMask
# ---------------------------------------------------------------------------


class TestRadialGradientMask:
    """Test radial gradient mask."""

    def test_shape(self) -> None:
        mask = RadialGradientMask(center=Vec2(100, 50), radius=80)
        result = mask.render_mask(_ctx())
        assert result.shape == (100, 200)

    def test_center_bright(self) -> None:
        mask = RadialGradientMask(center=Vec2(100, 50), radius=80)
        result = mask.render_mask(_ctx())
        assert result[50, 100] == 255  # Center
        # Far corner should be 0
        assert result[0, 0] == 0

    def test_zero_radius(self) -> None:
        mask = RadialGradientMask(center=Vec2(100, 50), radius=0)
        result = mask.render_mask(_ctx())
        assert result.max() == 0


# ---------------------------------------------------------------------------
# TrackMatte
# ---------------------------------------------------------------------------


class TestTrackMatte:
    """Test TrackMatte alpha and luma modes."""

    def test_alpha_mode(self) -> None:
        source = ColorClip("#FFFFFF").set_duration(60)
        matte = TrackMatte(source=source, mode="alpha")
        result = matte.render_mask(_ctx())
        assert result.shape == (100, 200)
        # ColorClip renders with alpha=255
        assert result[50, 50] == 255

    def test_luma_mode(self) -> None:
        # White clip → luma ≈ 255
        source = ColorClip("#FFFFFF").set_duration(60)
        matte = TrackMatte(source=source, mode="luma")
        result = matte.render_mask(_ctx())
        assert result[50, 50] > 250

    def test_luma_mode_black(self) -> None:
        # Black clip → luma ≈ 0
        source = ColorClip("#000000").set_duration(60)
        matte = TrackMatte(source=source, mode="luma")
        result = matte.render_mask(_ctx())
        assert result[50, 50] < 5

    def test_no_source_raises(self) -> None:
        matte = TrackMatte(source=None, mode="alpha")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="source clip"):
            matte.render_mask(_ctx())


# ---------------------------------------------------------------------------
# TextMask
# ---------------------------------------------------------------------------


class TestTextMask:
    """Test TextMask rendering."""

    def test_shape(self) -> None:
        mask = TextMask(text="HELLO", font="sans-serif", size=48)
        result = mask.render_mask(_ctx())
        assert result.shape == (100, 200)
        assert result.dtype == np.uint8

    def test_non_empty_text_has_visible_pixels(self) -> None:
        mask = TextMask(text="HELLO", font="sans-serif", size=48)
        result = mask.render_mask(_ctx())
        assert result.max() > 0

    def test_empty_text_returns_zeros(self) -> None:
        mask = TextMask(text="", font="sans-serif", size=48)
        result = mask.render_mask(_ctx())
        assert result.max() == 0


# ---------------------------------------------------------------------------
# Boolean operations
# ---------------------------------------------------------------------------


class TestMaskBooleanOps:
    """Test combining multiple masks with boolean operations."""

    def test_union(self) -> None:
        from pymotion.masking import MaskGroup

        # Two non-overlapping rects
        m1 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(50, 0)),
                BezierPoint(vertex=Vec2(50, 50)),
                BezierPoint(vertex=Vec2(0, 50)),
            ]
        )
        m2 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(100, 0)),
                BezierPoint(vertex=Vec2(150, 0)),
                BezierPoint(vertex=Vec2(150, 50)),
                BezierPoint(vertex=Vec2(100, 50)),
            ]
        )

        white_frame = np.full((100, 200, 4), 255, dtype=np.uint8)
        masks = [
            MaskGroup(mask=m1, op=MaskOp.ADD),
            MaskGroup(mask=m2, op=MaskOp.ADD),
        ]
        result = apply_masks(white_frame, masks, _ctx())
        # Both regions should be visible
        assert result[25, 25, 3] > 0
        assert result[25, 125, 3] > 0

    def test_intersect(self) -> None:
        from pymotion.masking import MaskGroup

        # Full-frame mask intersected with left-half
        m1 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(200, 0)),
                BezierPoint(vertex=Vec2(200, 100)),
                BezierPoint(vertex=Vec2(0, 100)),
            ]
        )
        m2 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(100, 0)),
                BezierPoint(vertex=Vec2(100, 100)),
                BezierPoint(vertex=Vec2(0, 100)),
            ]
        )

        white_frame = np.full((100, 200, 4), 255, dtype=np.uint8)
        masks = [
            MaskGroup(mask=m1, op=MaskOp.ADD),
            MaskGroup(mask=m2, op=MaskOp.INTERSECT),
        ]
        result = apply_masks(white_frame, masks, _ctx())
        # Left half visible
        assert result[50, 50, 3] > 0
        # Right half hidden
        assert result[50, 150, 3] == 0

    def test_subtract(self) -> None:
        from pymotion.masking import MaskGroup

        # Full frame minus a center rect
        m1 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(200, 0)),
                BezierPoint(vertex=Vec2(200, 100)),
                BezierPoint(vertex=Vec2(0, 100)),
            ]
        )
        m2 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(50, 25)),
                BezierPoint(vertex=Vec2(150, 25)),
                BezierPoint(vertex=Vec2(150, 75)),
                BezierPoint(vertex=Vec2(50, 75)),
            ]
        )

        white_frame = np.full((100, 200, 4), 255, dtype=np.uint8)
        masks = [
            MaskGroup(mask=m1, op=MaskOp.ADD),
            MaskGroup(mask=m2, op=MaskOp.SUBTRACT),
        ]
        result = apply_masks(white_frame, masks, _ctx())
        # Center should be hidden
        assert result[50, 100, 3] == 0
        # Corner should be visible
        assert result[5, 5, 3] > 0


# ---------------------------------------------------------------------------
# Clip integration
# ---------------------------------------------------------------------------


class TestClipMaskIntegration:
    """Test add_mask on actual clips."""

    def test_add_mask_fluent(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        mask = RadialGradientMask(center=Vec2(100, 50), radius=50)
        result = clip.add_mask(mask)
        assert result is clip

    def test_mask_modifies_alpha(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        # Mask only left half
        mask = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(100, 0)),
                BezierPoint(vertex=Vec2(100, 100)),
                BezierPoint(vertex=Vec2(0, 100)),
            ]
        )
        clip.add_mask(mask)
        frame = clip.render_with_effects(_ctx())
        # Left half: visible
        assert frame[50, 50, 3] > 0
        # Right half: hidden
        assert frame[50, 150, 3] == 0

    def test_clear_masks(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        clip.add_mask(RadialGradientMask(center=Vec2(100, 50), radius=50))
        clip.clear_masks()
        frame = clip.render_with_effects(_ctx())
        # Should be fully opaque again
        assert frame[50, 50, 3] == 255

    def test_invalid_mask_raises(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        with pytest.raises(TypeError, match="Mask instance"):
            clip.add_mask("not a mask")  # type: ignore[arg-type]

    def test_mask_in_composition(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        white = ColorClip("#FFFFFF").set_duration(30)
        # Mask to left half only
        white.add_mask(
            BezierMask(
                points=[
                    BezierPoint(vertex=Vec2(0, 0)),
                    BezierPoint(vertex=Vec2(100, 0)),
                    BezierPoint(vertex=Vec2(100, 100)),
                    BezierPoint(vertex=Vec2(0, 100)),
                ]
            )
        )
        comp.add(white)

        frame = comp._render_frame(0)
        # Left half should show white (composited over black bg)
        assert frame[50, 50, 0] > 250  # B channel (mask >> 8 rounding)
        # Right half should be black bg
        assert frame[50, 150, 0] == 0

    def test_add_mask_with_op(self) -> None:
        clip = ColorClip("#FFFFFF").set_duration(30)
        m1 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(200, 0)),
                BezierPoint(vertex=Vec2(200, 100)),
                BezierPoint(vertex=Vec2(0, 100)),
            ]
        )
        m2 = BezierMask(
            points=[
                BezierPoint(vertex=Vec2(0, 0)),
                BezierPoint(vertex=Vec2(100, 0)),
                BezierPoint(vertex=Vec2(100, 100)),
                BezierPoint(vertex=Vec2(0, 100)),
            ]
        )
        clip.add_mask(m1)
        clip.add_mask(m2, op=MaskOp.INTERSECT)

        frame = clip.render_with_effects(_ctx())
        # Only left half should be visible
        assert frame[50, 50, 3] > 0
        assert frame[50, 150, 3] == 0


class TestMaskExports:
    """Test public API exports."""

    def test_all_importable(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "BezierMask")
        assert hasattr(pm, "BezierPoint")
        assert hasattr(pm, "LinearGradientMask")
        assert hasattr(pm, "RadialGradientMask")
        assert hasattr(pm, "TextMask")
        assert hasattr(pm, "TrackMatte")
        assert hasattr(pm, "Mask")
        assert hasattr(pm, "MaskOp")
        assert hasattr(pm, "MaskGroup")
