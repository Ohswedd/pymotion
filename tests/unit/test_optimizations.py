"""Tests for render optimizations — incremental renderer, mmap buffer,
static layer cache, SIMD blend, and parallel audio rendering."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from pymotion.render.optimizations import (
    IncrementalRenderer,
    MappedFrameBuffer,
    StaticLayerCache,
    profiled_frame_iterator,
    render_audio_parallel,
    try_simd_blend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_composition_mock(
    width: int = 4,
    height: int = 4,
    tracks: list[MagicMock] | None = None,
) -> MagicMock:
    """Create a mock Composition for testing."""
    comp = MagicMock()
    res = MagicMock()
    res.width = width
    res.height = height
    comp.resolution = res

    if tracks is None:
        clip = MagicMock()
        clip.start = 0
        clip.end = 10
        clip._opacity = 1.0
        clip.blend_mode.value = "normal"
        clip._effects = []

        track = MagicMock()
        track.name = "Track 1"
        track.opacity = 1.0
        track.clips = [clip]
        tracks = [track]

    comp.tracks = tracks

    frame = np.zeros((height, width, 4), dtype=np.uint8)
    frame[:, :, 2] = 128  # Red channel in BGRA
    comp._render_frame.return_value = frame
    return comp


# ---------------------------------------------------------------------------
# IncrementalRenderer
# ---------------------------------------------------------------------------


class TestIncrementalRenderer:
    """Tests for IncrementalRenderer."""

    def test_first_render_calls_render_frame(self, tmp_path: Path) -> None:
        comp = _make_composition_mock()
        renderer = IncrementalRenderer(cache_dir=tmp_path / "cache")
        result = renderer.render_frame(comp, 0)
        comp._render_frame.assert_called_once_with(0)
        assert result.shape == (4, 4, 4)

    def test_cached_frame_skips_render(self, tmp_path: Path) -> None:
        comp = _make_composition_mock()
        renderer = IncrementalRenderer(cache_dir=tmp_path / "cache")
        renderer.render_frame(comp, 0)
        renderer.render_frame(comp, 0)
        # Second call should use cache — _render_frame called only once
        assert comp._render_frame.call_count == 1

    def test_different_frames_both_rendered(self, tmp_path: Path) -> None:
        comp = _make_composition_mock()
        renderer = IncrementalRenderer(cache_dir=tmp_path / "cache")
        renderer.render_frame(comp, 0)
        renderer.render_frame(comp, 1)
        assert comp._render_frame.call_count == 2

    def test_invalidate_clears_cache(self, tmp_path: Path) -> None:
        comp = _make_composition_mock()
        renderer = IncrementalRenderer(cache_dir=tmp_path / "cache")
        renderer.render_frame(comp, 0)
        assert renderer.cached_frames == 1
        renderer.invalidate()
        assert renderer.cached_frames == 0

    def test_state_change_triggers_rerender(self, tmp_path: Path) -> None:
        comp = _make_composition_mock()
        renderer = IncrementalRenderer(cache_dir=tmp_path / "cache")
        renderer.render_frame(comp, 0)

        # Change track opacity to alter state hash
        comp.tracks[0].opacity = 0.5
        renderer.render_frame(comp, 0)
        assert comp._render_frame.call_count == 2

    def test_cached_frames_property(self, tmp_path: Path) -> None:
        comp = _make_composition_mock()
        renderer = IncrementalRenderer(cache_dir=tmp_path / "cache")
        assert renderer.cached_frames == 0
        renderer.render_frame(comp, 0)
        renderer.render_frame(comp, 3)
        assert renderer.cached_frames == 2

    def test_cache_dir_created(self, tmp_path: Path) -> None:
        cache = tmp_path / "deep" / "nested" / "cache"
        IncrementalRenderer(cache_dir=cache)
        assert cache.exists()


# ---------------------------------------------------------------------------
# MappedFrameBuffer
# ---------------------------------------------------------------------------


class TestMappedFrameBuffer:
    """Tests for MappedFrameBuffer."""

    def test_write_read_roundtrip(self) -> None:
        buf = MappedFrameBuffer(4, 4)
        frame = np.random.default_rng(42).integers(0, 256, (4, 4, 4), dtype=np.uint8)
        buf.write_frame(frame)
        result = buf.read_frame()
        np.testing.assert_array_equal(result, frame)
        buf.close()

    def test_read_region(self) -> None:
        buf = MappedFrameBuffer(8, 8)
        frame = np.zeros((8, 8, 4), dtype=np.uint8)
        frame[2:4, 3:6, :] = 200
        buf.write_frame(frame)
        region = buf.read_region(2, 4, 3, 6)
        assert region.shape == (2, 3, 4)
        assert np.all(region == 200)
        buf.close()

    def test_size_bytes(self) -> None:
        buf = MappedFrameBuffer(1920, 1080)
        assert buf.size_bytes == 1920 * 1080 * 4
        buf.close()

    def test_path_property(self) -> None:
        buf = MappedFrameBuffer(4, 4)
        assert buf.path.exists()
        buf.close()

    def test_close_removes_file(self) -> None:
        buf = MappedFrameBuffer(4, 4)
        path = buf.path
        assert path.exists()
        buf.close()
        assert not path.exists()

    def test_custom_path(self, tmp_path: Path) -> None:
        path = tmp_path / "custom.raw"
        buf = MappedFrameBuffer(4, 4, path=path)
        assert buf.path == path
        buf.close()

    def test_double_close_safe(self) -> None:
        buf = MappedFrameBuffer(4, 4)
        buf.close()
        buf.close()  # Should not raise


# ---------------------------------------------------------------------------
# try_simd_blend
# ---------------------------------------------------------------------------


class TestSIMDBlend:
    """Tests for try_simd_blend (NumPy fallback)."""

    def test_fully_opaque_blend(self) -> None:
        dst = np.zeros((4, 4, 4), dtype=np.uint8)
        src = np.full((4, 4, 4), 200, dtype=np.uint8)
        src[:, :, 3] = 255  # Full alpha
        result = try_simd_blend(dst, src, 1.0)
        # With full alpha and opacity=1.0, result should be close to src
        assert result[:, :, :3].mean() > 190

    def test_zero_opacity_blend(self) -> None:
        dst = np.full((4, 4, 4), 100, dtype=np.uint8)
        src = np.full((4, 4, 4), 200, dtype=np.uint8)
        src[:, :, 3] = 255
        result = try_simd_blend(dst, src, 0.0)
        # Zero opacity → result should be very close to dst (integer rounding)
        np.testing.assert_allclose(result[:, :, :3], dst[:, :, :3], atol=1)

    def test_half_opacity_blend(self) -> None:
        dst = np.zeros((4, 4, 4), dtype=np.uint8)
        dst[:, :, 3] = 255
        src = np.full((4, 4, 4), 200, dtype=np.uint8)
        src[:, :, 3] = 255
        result = try_simd_blend(dst, src, 0.5)
        # Should be roughly halfway
        mean_val = result[:, :, 0].mean()
        assert 80 < mean_val < 120

    def test_transparent_src_no_change(self) -> None:
        dst = np.full((4, 4, 4), 100, dtype=np.uint8)
        src = np.full((4, 4, 4), 200, dtype=np.uint8)
        src[:, :, 3] = 0  # Transparent source
        result = try_simd_blend(dst, src, 1.0)
        # Transparent source → result should be very close to dst (integer rounding)
        np.testing.assert_allclose(result[:, :, :3], dst[:, :, :3], atol=1)

    def test_output_shape_preserved(self) -> None:
        dst = np.zeros((8, 6, 4), dtype=np.uint8)
        src = np.zeros((8, 6, 4), dtype=np.uint8)
        result = try_simd_blend(dst, src, 0.5)
        assert result.shape == (8, 6, 4)


# ---------------------------------------------------------------------------
# StaticLayerCache
# ---------------------------------------------------------------------------


class TestStaticLayerCache:
    """Tests for StaticLayerCache."""

    def test_static_clip_is_baked(self) -> None:
        clip = MagicMock()
        clip.start = 0
        clip.end = 30
        clip._keyframe_tracks = {}
        clip._expressions = {}
        clip.render_with_effects.return_value = np.zeros((4, 4, 4), dtype=np.uint8)

        track = MagicMock()
        track.name = "BG"
        track.clips = [clip]

        comp = _make_composition_mock(tracks=[track])
        comp.fps = 30

        cache = StaticLayerCache(comp)
        count = cache.bake()
        assert count == 1
        assert cache.baked_count == 1

    def test_animated_clip_not_baked(self) -> None:
        clip = MagicMock()
        clip.start = 0
        clip.end = 30
        clip._keyframe_tracks = {"opacity": [0.0, 1.0]}
        clip._expressions = {}

        track = MagicMock()
        track.name = "Anim"
        track.clips = [clip]

        comp = _make_composition_mock(tracks=[track])
        comp.fps = 30

        cache = StaticLayerCache(comp)
        count = cache.bake()
        assert count == 0

    def test_get_baked_returns_none_for_animated(self) -> None:
        comp = _make_composition_mock(tracks=[])
        cache = StaticLayerCache(comp)
        assert cache.get_baked(0, 0) is None

    def test_get_baked_returns_frame(self) -> None:
        frame_data = np.ones((4, 4, 4), dtype=np.uint8) * 42
        clip = MagicMock()
        clip.start = 0
        clip.end = 10
        clip._keyframe_tracks = {}
        clip._expressions = {}
        clip.render_with_effects.return_value = frame_data

        track = MagicMock()
        track.name = "Static"
        track.clips = [clip]

        comp = _make_composition_mock(tracks=[track])
        comp.fps = 30

        cache = StaticLayerCache(comp)
        cache.bake()
        result = cache.get_baked(0, 0)
        assert result is not None
        np.testing.assert_array_equal(result, frame_data)


# ---------------------------------------------------------------------------
# render_audio_parallel
# ---------------------------------------------------------------------------


class TestRenderAudioParallel:
    """Tests for render_audio_parallel."""

    def test_single_segment(self) -> None:
        audio = np.ones(100, dtype=np.float32) * 0.5
        segments = [(audio, 0, 100)]
        result = render_audio_parallel(segments, 100)
        np.testing.assert_allclose(result[:100], 0.5, atol=1e-6)

    def test_two_overlapping_segments(self) -> None:
        seg1 = np.ones(50, dtype=np.float32) * 0.3
        seg2 = np.ones(50, dtype=np.float32) * 0.2
        segments = [(seg1, 0, 50), (seg2, 25, 75)]
        result = render_audio_parallel(segments, 100)
        # Overlap region [25:50] should sum to 0.5
        np.testing.assert_allclose(result[25:50], 0.5, atol=1e-6)
        # Non-overlap regions
        np.testing.assert_allclose(result[0:25], 0.3, atol=1e-6)
        np.testing.assert_allclose(result[50:75], 0.2, atol=1e-6)

    def test_empty_segments(self) -> None:
        result = render_audio_parallel([], 100)
        np.testing.assert_array_equal(result, np.zeros(100))

    def test_segment_clipped_to_end(self) -> None:
        audio = np.ones(200, dtype=np.float32)
        segments = [(audio, 0, 100)]  # end=100 but audio is 200
        result = render_audio_parallel(segments, 100)
        np.testing.assert_allclose(result, 1.0, atol=1e-6)

    def test_thread_count_respected(self) -> None:
        audio = np.ones(10, dtype=np.float32)
        segments = [(audio, 0, 10)]
        # Just verify it runs with different thread counts
        result = render_audio_parallel(segments, 10, num_threads=1)
        assert result.shape == (10,)
        result = render_audio_parallel(segments, 10, num_threads=8)
        assert result.shape == (10,)


# ---------------------------------------------------------------------------
# profiled_frame_iterator
# ---------------------------------------------------------------------------


class TestProfiledFrameIterator:
    """Tests for profiled_frame_iterator."""

    def test_yields_frame_and_timing(self) -> None:
        frames = [np.zeros((2, 2, 4), dtype=np.uint8) for _ in range(3)]
        results = list(profiled_frame_iterator(iter(frames)))
        assert len(results) == 3
        for frame, timing in results:
            assert isinstance(frame, np.ndarray)
            assert isinstance(timing, float)
            assert timing >= 0.0

    def test_empty_iterator(self) -> None:
        results = list(profiled_frame_iterator(iter([])))
        assert results == []
