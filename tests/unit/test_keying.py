"""Tests for keying effects — ChromaKey, LumaKey, ColorKey, DifferenceKey."""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.effects.keying import (
    ChromaKey,
    ColorKey,
    DifferenceKey,
    LumaKey,
    _choke_mask,
    _despill,
    _feather_mask,
)


def _ctx() -> RenderContext:
    """Create a minimal render context."""
    return RenderContext(
        frame=0,
        fps=30,
        resolution=Resolution(width=64, height=64),
        time_range=TimeRange(start=0, end=60),
        local_frame=0,
        progress=0.0,
    )


def _green_frame(h: int = 64, w: int = 64) -> np.ndarray:
    """Create a solid green BGRA frame."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[:, :, 1] = 255  # Green channel (B=0, G=255, R=0)
    frame[:, :, 3] = 255  # Full alpha
    return frame


def _red_frame(h: int = 64, w: int = 64) -> np.ndarray:
    """Create a solid red BGRA frame."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[:, :, 2] = 255  # Red channel (BGRA: index 2)
    frame[:, :, 3] = 255
    return frame


def _mixed_frame(h: int = 64, w: int = 64) -> np.ndarray:
    """Create a frame with green top half and red bottom half."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[: h // 2, :, 1] = 255  # Top: green
    frame[h // 2 :, :, 2] = 255  # Bottom: red
    frame[:, :, 3] = 255
    return frame


class TestFeatherMask:
    """Tests for _feather_mask utility."""

    def test_feather_zero_radius(self) -> None:
        mask = np.ones((10, 10), dtype=np.float32)
        result = _feather_mask(mask, 0)
        np.testing.assert_array_equal(result, mask)

    def test_feather_positive_radius(self) -> None:
        mask = np.zeros((20, 20), dtype=np.float32)
        mask[5:15, 5:15] = 1.0
        result = _feather_mask(mask, 2)
        assert result.shape == mask.shape
        # Edges should be softer than the sharp input
        assert result[5, 5] < 1.0 or result[4, 4] > 0.0

    def test_feather_preserves_shape(self) -> None:
        mask = np.random.rand(30, 50).astype(np.float32)
        result = _feather_mask(mask, 3)
        assert result.shape == mask.shape


class TestChokeMask:
    """Tests for _choke_mask utility."""

    def test_choke_zero(self) -> None:
        mask = np.full((10, 10), 0.5, dtype=np.float32)
        result = _choke_mask(mask, 0.0)
        np.testing.assert_array_almost_equal(result, mask)

    def test_choke_expand(self) -> None:
        mask = np.full((10, 10), 0.5, dtype=np.float32)
        result = _choke_mask(mask, 0.3)
        assert np.all(result >= 0.5)

    def test_choke_contract(self) -> None:
        mask = np.full((10, 10), 0.5, dtype=np.float32)
        result = _choke_mask(mask, -0.3)
        assert np.all(result <= 0.5)

    def test_choke_clamps(self) -> None:
        mask = np.full((10, 10), 0.8, dtype=np.float32)
        result = _choke_mask(mask, 0.5)
        assert np.all(result <= 1.0)


class TestDespill:
    """Tests for _despill utility."""

    def test_despill_zero_strength(self) -> None:
        frame = _green_frame()
        spill = np.array([0, 255, 0], dtype=np.uint8)
        result = _despill(frame, spill, 0.0)
        np.testing.assert_array_equal(result, frame)

    def test_despill_reduces_spill(self) -> None:
        frame = _green_frame()
        spill = np.array([0, 255, 0], dtype=np.uint8)
        result = _despill(frame, spill, 1.0)
        # Green should be reduced
        assert result[0, 0, 1] < 255


class TestChromaKey:
    """Tests for ChromaKey effect."""

    def test_chroma_key_green(self) -> None:
        """Green frame with green key should become transparent."""
        frame = _green_frame()
        effect = ChromaKey(color="#00FF00", tolerance=0.5)
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape
        # Alpha should be reduced for green pixels
        assert result[0, 0, 3] < 128

    def test_chroma_key_preserves_non_key(self) -> None:
        """Red frame with green key should remain opaque."""
        frame = _red_frame()
        effect = ChromaKey(color="#00FF00", tolerance=0.3)
        result = effect.apply(frame, _ctx())
        # Red pixels should remain mostly opaque
        assert result[0, 0, 3] > 128

    def test_chroma_key_with_softness(self) -> None:
        frame = _green_frame()
        effect = ChromaKey(color="#00FF00", tolerance=0.5, edge_softness=0.1)
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape

    def test_chroma_key_with_spill(self) -> None:
        frame = _green_frame()
        effect = ChromaKey(color="#00FF00", tolerance=0.5, spill_suppression=0.8)
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape

    def test_chroma_key_mixed_frame(self) -> None:
        """Mixed frame: green should become transparent, red should stay."""
        frame = _mixed_frame()
        effect = ChromaKey(color="#00FF00", tolerance=0.5)
        result = effect.apply(frame, _ctx())
        # Top half (green) should be more transparent
        top_alpha = result[10, 32, 3]
        # Bottom half (red) should be more opaque
        bottom_alpha = result[50, 32, 3]
        assert bottom_alpha > top_alpha

    def test_chroma_key_no_spill(self) -> None:
        frame = _green_frame()
        effect = ChromaKey(color="#00FF00", tolerance=0.5, spill_suppression=0.0)
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape


class TestLumaKey:
    """Tests for LumaKey effect."""

    def test_luma_key_dark(self) -> None:
        """Dark frame keyed at threshold=0.5 should become transparent."""
        frame = np.zeros((64, 64, 4), dtype=np.uint8)
        frame[:, :, 3] = 255  # Full alpha, black pixels
        effect = LumaKey(threshold=0.5)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] < 128

    def test_luma_key_bright(self) -> None:
        """Bright frame keyed at threshold=0.5 should stay opaque."""
        frame = np.full((64, 64, 4), 255, dtype=np.uint8)
        effect = LumaKey(threshold=0.5)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] > 128

    def test_luma_key_inverted(self) -> None:
        """Inverted: bright frame should become transparent."""
        frame = np.full((64, 64, 4), 255, dtype=np.uint8)
        effect = LumaKey(threshold=0.5, invert=True)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] < 128


class TestColorKey:
    """Tests for ColorKey effect."""

    def test_color_key_matching(self) -> None:
        """Frame matching key color should become transparent."""
        frame = _red_frame()
        effect = ColorKey(color="#FF0000", tolerance=0.3)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] < 128

    def test_color_key_non_matching(self) -> None:
        """Frame not matching key color should stay opaque."""
        frame = _green_frame()
        effect = ColorKey(color="#FF0000", tolerance=0.2)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] > 128

    def test_color_key_with_softness(self) -> None:
        frame = _red_frame()
        effect = ColorKey(color="#FF0000", tolerance=0.3, softness=0.2)
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape


class TestDifferenceKey:
    """Tests for DifferenceKey effect."""

    def test_difference_key_identical(self) -> None:
        """Frame identical to reference should become transparent."""
        frame = _red_frame()
        reference = _red_frame()
        effect = DifferenceKey(reference=reference, tolerance=0.1)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] < 128

    def test_difference_key_different(self) -> None:
        """Frame very different from reference should stay opaque."""
        frame = _red_frame()
        reference = _green_frame()
        effect = DifferenceKey(reference=reference, tolerance=0.1)
        result = effect.apply(frame, _ctx())
        assert result[0, 0, 3] > 128

    def test_difference_key_size_mismatch(self) -> None:
        """Should handle reference of different size."""
        frame = _red_frame(64, 64)
        reference = _red_frame(32, 32)
        effect = DifferenceKey(reference=reference, tolerance=0.1)
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape

    def test_difference_key_empty_reference(self) -> None:
        """Empty reference should return frame unchanged."""
        frame = _red_frame()
        effect = DifferenceKey()  # default 1x1 reference
        result = effect.apply(frame, _ctx())
        assert result.shape == frame.shape


class TestAddEffect:
    """Tests for Clip.add_effect() and render_with_effects()."""

    def test_add_effect_to_clip(self) -> None:
        from pymotion.clip.color import ColorClip
        from pymotion.utils.color import Color

        clip = ColorClip(color=Color.parse("#00FF00"))
        clip.start = 0
        clip.end = 60
        effect = ChromaKey(color="#00FF00", tolerance=0.5)
        result = clip.add_effect(effect)
        assert result is clip
        assert len(clip._effects) == 1

    def test_render_with_effects(self) -> None:
        from pymotion.clip.color import ColorClip
        from pymotion.utils.color import Color

        clip = ColorClip(color=Color.parse("#00FF00"))
        clip.start = 0
        clip.end = 60
        clip.add_effect(ChromaKey(color="#00FF00", tolerance=0.5))
        frame = clip.render_with_effects(_ctx())
        assert frame.shape == (64, 64, 4)
        # Green should be keyed out
        assert frame[0, 0, 3] < 128

    def test_render_without_effects(self) -> None:
        from pymotion.clip.color import ColorClip
        from pymotion.utils.color import Color

        clip = ColorClip(color=Color.parse("#00FF00"))
        clip.start = 0
        clip.end = 60
        frame = clip.render_with_effects(_ctx())
        # No effects: should be fully opaque green
        assert frame[0, 0, 3] == 255
