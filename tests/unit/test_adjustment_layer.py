"""Tests for AdjustmentLayer — v1.3.2."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.composition import AdjustmentLayer, Composition, get_shared_frame_cache
from pymotion.effects.base import Effect
from pymotion.effects.color import Brightness, Contrast


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_shared_frame_cache().clear()


def _make_ctx(
    frame: int = 0,
    width: int = 200,
    height: int = 100,
    duration: int = 60,
) -> RenderContext:
    local_frame = frame
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(width=width, height=height),
        time_range=TimeRange(start=0, end=duration),
        local_frame=local_frame,
        progress=local_frame / max(duration - 1, 1),
    )


class _InvertEffect(Effect):
    """Test effect that inverts RGB channels."""

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        result = frame.copy()
        result[:, :, :3] = 255 - result[:, :, :3]
        return result


class TestAdjustmentLayerBasic:
    """Test basic AdjustmentLayer functionality."""

    def test_is_clip_subclass(self) -> None:
        from pymotion.clip.base import Clip

        adj = AdjustmentLayer()
        assert isinstance(adj, Clip)

    def test_init_with_no_effects(self) -> None:
        adj = AdjustmentLayer()
        assert len(adj._effects) == 0

    def test_init_with_effects(self) -> None:
        adj = AdjustmentLayer(effects=[Brightness(value=0.5)])
        assert len(adj._effects) == 1

    def test_init_with_multiple_effects(self) -> None:
        adj = AdjustmentLayer(effects=[Brightness(value=0.3), Contrast(value=1.2)])
        assert len(adj._effects) == 2

    def test_render_frame_returns_transparent(self) -> None:
        adj = AdjustmentLayer()
        adj.set_duration(10)
        ctx = _make_ctx(duration=10)
        frame = adj.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        assert frame.max() == 0  # Fully transparent

    def test_add_effect_fluent(self) -> None:
        adj = AdjustmentLayer()
        result = adj.add_effect(Brightness(value=0.5))
        assert result is adj

    def test_set_duration(self) -> None:
        adj = AdjustmentLayer()
        adj.set_duration(60)
        assert adj.duration == 60


class TestAdjustmentLayerInComposition:
    """Test AdjustmentLayer behaviour inside a Composition."""

    def test_affects_layers_below(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        # Add a white clip
        white = ColorClip("#FFFFFF").set_duration(30)
        comp.add(white)

        # Render without adjustment
        frame_before = comp._render_frame(0).copy()

        # Add adjustment layer with invert effect
        adj = AdjustmentLayer(effects=[_InvertEffect()])
        adj.set_duration(30)
        comp.add(adj)

        frame_after = comp._render_frame(0)

        # White inverted = black (RGB channels)
        assert frame_after[50, 50, 0] == 0  # B
        assert frame_after[50, 50, 1] == 0  # G
        assert frame_after[50, 50, 2] == 0  # R
        # Original was white
        assert frame_before[50, 50, 0] == 255

    def test_does_not_affect_layers_above(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#808080")
        # Add adjustment layer that inverts
        adj = AdjustmentLayer(effects=[_InvertEffect()])
        adj.set_duration(30)
        comp.add(adj)

        # Add white clip ABOVE adjustment layer
        white = ColorClip("#FFFFFF").set_duration(30)
        comp.add(white)

        frame = comp._render_frame(0)
        # White clip above should be unaffected
        assert frame[50, 50, 0] == 255
        assert frame[50, 50, 1] == 255
        assert frame[50, 50, 2] == 255

    def test_respects_time_range(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=60, background="#000000")
        white = ColorClip("#FFFFFF").set_duration(60)
        comp.add(white)

        # Adjustment layer only active for frames 0-29
        adj = AdjustmentLayer(effects=[_InvertEffect()])
        adj.set_duration(30)
        comp.add(adj)

        # Frame 0: adjustment active → white inverted to black
        frame_0 = comp._render_frame(0)
        assert frame_0[50, 50, 2] == 0

        # Frame 30: adjustment inactive → white stays white
        frame_30 = comp._render_frame(30)
        assert frame_30[50, 50, 2] == 255

    def test_respects_opacity(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        white = ColorClip("#FFFFFF").set_duration(30)
        comp.add(white)

        # 50% opacity adjustment layer with invert
        adj = AdjustmentLayer(effects=[_InvertEffect()])
        adj.set_duration(30)
        adj.set_opacity(0.5)
        comp.add(adj)

        frame = comp._render_frame(0)
        # White (255) inverted = 0, blended 50% = ~127
        center_r = frame[50, 50, 2]
        assert 120 <= center_r <= 135  # Allow rounding

    def test_no_effects_passthrough(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        white = ColorClip("#FFFFFF").set_duration(30)
        comp.add(white)

        adj = AdjustmentLayer()  # No effects
        adj.set_duration(30)
        comp.add(adj)

        frame = comp._render_frame(0)
        # Should be unchanged — still white
        assert frame[50, 50, 0] == 255
        assert frame[50, 50, 1] == 255
        assert frame[50, 50, 2] == 255

    def test_multiple_adjustment_layers(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        gray = ColorClip("#808080").set_duration(30)
        comp.add(gray)

        # First invert: 128 → 127
        adj1 = AdjustmentLayer(effects=[_InvertEffect()])
        adj1.set_duration(30)
        comp.add(adj1)

        # Second invert: 127 → 128 (back to approximately original)
        adj2 = AdjustmentLayer(effects=[_InvertEffect()])
        adj2.set_duration(30)
        comp.add(adj2)

        frame = comp._render_frame(0)
        # Double invert ≈ original (within 1 due to rounding)
        center_b = frame[50, 50, 0]
        assert abs(int(center_b) - 128) <= 1

    def test_with_real_brightness_effect(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        gray = ColorClip("#808080").set_duration(30)
        comp.add(gray)

        adj = AdjustmentLayer(effects=[Brightness(value=1.5)])
        adj.set_duration(30)
        comp.add(adj)

        frame_adj = comp._render_frame(0)

        # Without adjustment layer
        comp2 = Composition(
            width=200, height=100, fps=30, duration=30, background="#000000"
        )
        gray2 = ColorClip("#808080").set_duration(30)
        comp2.add(gray2)
        frame_no_adj = comp2._render_frame(0)

        # Brightness 1.5 should increase pixel values
        assert frame_adj[50, 50, 0] > frame_no_adj[50, 50, 0]


class TestAdjustmentLayerExport:
    """Test that AdjustmentLayer is in public API."""

    def test_importable_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "AdjustmentLayer")
        assert pm.AdjustmentLayer is AdjustmentLayer
