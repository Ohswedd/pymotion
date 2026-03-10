"""Tests for CompositionClip — nested composition support (v1.3.1)."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.composition import (
    Composition,
    CompositionClip,
    _NestedFrameCache,
    get_shared_frame_cache,
)


def _make_ctx(
    frame: int = 0,
    fps: int = 30,
    width: int = 200,
    height: int = 100,
    local_frame: int | None = None,
    duration: int = 60,
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


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear the shared frame cache between tests."""
    get_shared_frame_cache().clear()


class TestCompositionToClip:
    """Test Composition.to_clip() basic functionality."""

    def test_to_clip_returns_composition_clip(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=60)
        clip = comp.to_clip()
        assert isinstance(clip, CompositionClip)

    def test_to_clip_preserves_duration(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=90)
        clip = comp.to_clip()
        assert clip.duration == 90

    def test_to_clip_zero_duration_raises(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=0)
        with pytest.raises(ValueError, match="zero duration"):
            comp.to_clip()

    def test_to_clip_renders_background(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=30, background="#FF0000")
        clip = comp.to_clip()
        ctx = _make_ctx(width=200, height=100, duration=30)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        # Red in BGRA = (0, 0, 255, 255)
        assert frame[50, 50, 2] == 255  # R channel
        assert frame[50, 50, 0] == 0  # B channel

    def test_to_clip_renders_child_clips(self) -> None:
        child = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        green = ColorClip("#00FF00").set_duration(30)
        child.add(green)

        clip = child.to_clip()
        ctx = _make_ctx(width=200, height=100, duration=30)
        frame = clip.render_frame(ctx)
        # Green in BGRA = (0, 255, 0, 255)
        assert frame[50, 50, 1] == 255  # G channel


class TestNestedCompositions:
    """Test nesting compositions inside other compositions."""

    def test_two_level_nesting(self) -> None:
        inner = Composition(width=200, height=100, fps=30, duration=30, background="#0000FF")
        inner_clip = inner.to_clip()

        outer = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        outer.add(inner_clip)
        frame = outer._render_frame(0)
        assert frame.shape == (100, 200, 4)
        # Blue in BGRA = (255, 0, 0, 255)
        assert frame[50, 50, 0] == 255

    def test_three_level_nesting(self) -> None:
        level1 = Composition(width=200, height=100, fps=30, duration=30, background="#FF0000")
        level2 = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        level2.add(level1.to_clip())

        level3 = Composition(width=200, height=100, fps=30, duration=30, background="#000000")
        level3.add(level2.to_clip())

        frame = level3._render_frame(0)
        assert frame.shape == (100, 200, 4)
        # Should see red from level1
        assert frame[50, 50, 2] == 255

    def test_max_nesting_depth_raises(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=10)
        clip = CompositionClip(_composition=comp, _nesting_depth=10)
        clip.set_duration(10)

        ctx = _make_ctx(width=200, height=100, duration=10)
        with pytest.raises(RecursionError, match="nesting depth"):
            clip.render_frame(ctx)

    def test_nesting_at_depth_9_succeeds(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=10, background="#FFFFFF")
        clip = CompositionClip(_composition=comp, _nesting_depth=9)
        clip.set_duration(10)

        ctx = _make_ctx(width=200, height=100, duration=10)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)


class TestResolutionScaling:
    """Test auto-scaling when nested comp has different resolution."""

    def test_upscale_child_to_parent(self) -> None:
        child = Composition(width=100, height=50, fps=30, duration=10, background="#FF0000")
        clip = child.to_clip()

        # Parent is larger
        ctx = _make_ctx(width=200, height=100, duration=10)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        # Should still be red
        assert frame[50, 50, 2] > 200

    def test_downscale_child_to_parent(self) -> None:
        child = Composition(width=400, height=200, fps=30, duration=10, background="#00FF00")
        clip = child.to_clip()

        # Parent is smaller
        ctx = _make_ctx(width=200, height=100, duration=10)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        # Should still be green
        assert frame[50, 50, 1] > 200

    def test_same_resolution_no_scaling(self) -> None:
        child = Composition(width=200, height=100, fps=30, duration=10, background="#AABBCC")
        clip = child.to_clip()
        ctx = _make_ctx(width=200, height=100, duration=10)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)


class TestFpsConversion:
    """Test frame remapping when nested comp has different fps."""

    def test_child_fps_double_parent(self) -> None:
        child = Composition(width=200, height=100, fps=60, duration=120, background="#FF0000")
        clip = child.to_clip()

        # Parent at 30fps, local_frame=15 → child frame = 15 * 60/30 = 30
        ctx = _make_ctx(fps=30, local_frame=15, width=200, height=100, duration=60)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)

    def test_child_fps_half_parent(self) -> None:
        child = Composition(width=200, height=100, fps=15, duration=30, background="#00FF00")
        clip = child.to_clip()

        # Parent at 30fps, local_frame=20 → child frame = 20 * 15/30 = 10
        ctx = _make_ctx(fps=30, local_frame=20, width=200, height=100, duration=60)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)

    def test_same_fps_no_remap(self) -> None:
        child = Composition(width=200, height=100, fps=30, duration=60, background="#0000FF")
        clip = child.to_clip()
        ctx = _make_ctx(fps=30, local_frame=10, width=200, height=100, duration=60)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)

    def test_frame_clamped_to_child_duration(self) -> None:
        child = Composition(width=200, height=100, fps=30, duration=10, background="#FFFFFF")
        clip = child.to_clip()
        # local_frame=100 far exceeds child's 10-frame duration
        ctx = _make_ctx(fps=30, local_frame=100, width=200, height=100, duration=200)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)


class TestNestedFrameCache:
    """Test the shared LRU frame cache."""

    def test_cache_put_get(self) -> None:
        cache = _NestedFrameCache(max_frames=10)
        data = np.zeros((10, 20, 4), dtype=np.uint8)
        data[5, 10, :] = [1, 2, 3, 4]

        cache.put(42, 0, data)
        result = cache.get(42, 0)
        assert result is not None
        np.testing.assert_array_equal(result, data)

    def test_cache_miss_returns_none(self) -> None:
        cache = _NestedFrameCache(max_frames=10)
        assert cache.get(999, 0) is None

    def test_cache_returns_copy(self) -> None:
        cache = _NestedFrameCache(max_frames=10)
        data = np.zeros((10, 20, 4), dtype=np.uint8)
        cache.put(1, 0, data)

        a = cache.get(1, 0)
        b = cache.get(1, 0)
        assert a is not None and b is not None
        assert a is not b  # Different objects

    def test_cache_eviction(self) -> None:
        cache = _NestedFrameCache(max_frames=3)
        for i in range(5):
            cache.put(0, i, np.zeros((2, 2, 4), dtype=np.uint8))

        # First two should be evicted
        assert cache.get(0, 0) is None
        assert cache.get(0, 1) is None
        # Last three should be present
        assert cache.get(0, 2) is not None
        assert cache.get(0, 3) is not None
        assert cache.get(0, 4) is not None

    def test_cache_lru_order(self) -> None:
        cache = _NestedFrameCache(max_frames=3)
        for i in range(3):
            cache.put(0, i, np.zeros((2, 2, 4), dtype=np.uint8))

        # Access frame 0, making it recently used
        cache.get(0, 0)
        # Add one more, should evict frame 1 (least recently used)
        cache.put(0, 99, np.zeros((2, 2, 4), dtype=np.uint8))

        assert cache.get(0, 0) is not None  # Still present (recently accessed)
        assert cache.get(0, 1) is None  # Evicted
        assert cache.get(0, 2) is not None
        assert cache.get(0, 99) is not None

    def test_cache_clear(self) -> None:
        cache = _NestedFrameCache(max_frames=10)
        for i in range(5):
            cache.put(0, i, np.zeros((2, 2, 4), dtype=np.uint8))
        assert cache.size == 5
        cache.clear()
        assert cache.size == 0

    def test_cache_size_property(self) -> None:
        cache = _NestedFrameCache(max_frames=10)
        assert cache.size == 0
        cache.put(0, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        assert cache.size == 1

    def test_get_shared_frame_cache_returns_same_instance(self) -> None:
        a = get_shared_frame_cache()
        b = get_shared_frame_cache()
        assert a is b


class TestCompositionClipEffects:
    """Test that effects work on CompositionClip."""

    def test_effects_applied_via_render_with_effects(self) -> None:
        from pymotion.effects.color import Brightness

        child = Composition(width=200, height=100, fps=30, duration=10, background="#808080")
        clip = child.to_clip()
        clip.add_effect(Brightness(value=0.5))

        ctx = _make_ctx(width=200, height=100, duration=10)
        frame_no_fx = clip.render_frame(ctx)
        frame_with_fx = clip.render_with_effects(ctx)
        # Brightness should change pixel values
        assert not np.array_equal(frame_no_fx, frame_with_fx)


class TestCompositionClipTransforms:
    """Test fluent API on CompositionClip."""

    def test_set_position(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=10)
        clip = comp.to_clip()
        result = clip.set_position(100, 50)
        assert result is clip
        assert clip._position.x == 100
        assert clip._position.y == 50

    def test_set_opacity(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=10)
        clip = comp.to_clip()
        clip.set_opacity(0.5)
        assert clip._opacity == 0.5

    def test_at_sets_start(self) -> None:
        comp = Composition(width=200, height=100, fps=30, duration=10)
        clip = comp.to_clip()
        clip.at(15)
        assert clip.start == 15
        assert clip.end == 25


class TestCompositionClipExport:
    """Test that CompositionClip is available in public API."""

    def test_importable_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "CompositionClip")
        assert pm.CompositionClip is CompositionClip
