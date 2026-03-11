"""Tests for profiling & diagnostics module."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from pymotion.render.profiling import (
    Bottleneck,
    FrameDiff,
    FrameProfile,
    MemoryReport,
    RenderProfile,
    benchmark,
    detect_bottlenecks,
    frame_diff,
    memory_report,
    profile_composition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_comp(
    width: int = 4,
    height: int = 4,
    duration: int = 10,
    fps: int = 30,
    n_clips: int = 1,
) -> MagicMock:
    """Create a mock Composition with configurable clips."""
    comp = MagicMock()
    res = MagicMock()
    res.width = width
    res.height = height
    comp.resolution = res
    comp.fps = fps
    comp.duration = duration

    tracks = []
    for i in range(n_clips):
        clip = MagicMock()
        clip.start = 0
        clip.end = duration
        clip._opacity = 1.0
        clip._effects = []
        clip.blend_mode.value = "normal"
        clip.render_with_effects.return_value = np.zeros((height, width, 4), dtype=np.uint8)

        track = MagicMock()
        track.name = f"Track {i}"
        track.visible = True
        track.opacity = 1.0
        track.blend_mode = MagicMock()
        track.clips = [clip]
        tracks.append(track)

    comp.tracks = tracks

    frame = np.zeros((height, width, 4), dtype=np.uint8)
    comp._render_frame.return_value = frame
    return comp


# ---------------------------------------------------------------------------
# profile_composition
# ---------------------------------------------------------------------------


class TestProfileComposition:
    """Tests for profile_composition."""

    def test_basic_profile(self) -> None:
        comp = _make_comp(duration=5)
        result = profile_composition(comp, start=0, end=5)
        assert isinstance(result, RenderProfile)
        assert result.total_frames == 5
        assert result.total_ms > 0
        assert result.avg_frame_ms > 0
        assert result.fps_achieved > 0

    def test_detailed_has_frame_profiles(self) -> None:
        comp = _make_comp(duration=3)
        result = profile_composition(comp, start=0, end=3, detailed=True)
        assert len(result.frame_profiles) == 3
        for fp in result.frame_profiles:
            assert isinstance(fp, FrameProfile)
            assert fp.total_ms >= 0
            assert fp.composite_ms >= 0

    def test_not_detailed_has_no_profiles(self) -> None:
        comp = _make_comp(duration=3)
        result = profile_composition(comp, start=0, end=3, detailed=False)
        assert result.frame_profiles == []

    def test_clip_timings_present(self) -> None:
        comp = _make_comp(duration=2, n_clips=2)
        result = profile_composition(comp, start=0, end=2, detailed=True)
        # Each frame should have timing for 2 clips
        for fp in result.frame_profiles:
            assert len(fp.clip_timings) == 2

    def test_min_max_frame_ms(self) -> None:
        comp = _make_comp(duration=5)
        result = profile_composition(comp, start=0, end=5)
        assert result.min_frame_ms <= result.avg_frame_ms
        assert result.max_frame_ms >= result.avg_frame_ms

    def test_defaults_to_full_duration(self) -> None:
        comp = _make_comp(duration=4)
        result = profile_composition(comp)
        assert result.total_frames == 4

    def test_empty_range(self) -> None:
        comp = _make_comp(duration=10)
        result = profile_composition(comp, start=5, end=5)
        assert result.total_frames == 0
        assert result.fps_achieved == 0.0


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------


class TestBenchmark:
    """Tests for benchmark."""

    def test_basic_benchmark(self) -> None:
        comp = _make_comp(duration=20)
        result = benchmark(comp, n_frames=10)
        assert isinstance(result, RenderProfile)
        assert result.total_frames == 10

    def test_benchmark_caps_at_duration(self) -> None:
        comp = _make_comp(duration=5)
        result = benchmark(comp, n_frames=100)
        assert result.total_frames == 5

    def test_benchmark_not_detailed(self) -> None:
        comp = _make_comp(duration=5)
        result = benchmark(comp, n_frames=5)
        assert result.frame_profiles == []


# ---------------------------------------------------------------------------
# memory_report
# ---------------------------------------------------------------------------


class TestMemoryReport:
    """Tests for memory_report."""

    def test_basic_report(self) -> None:
        comp = _make_comp(duration=5)
        report = memory_report(comp, n_frames=3)
        assert isinstance(report, MemoryReport)
        assert report.peak_ram_bytes >= 0
        assert report.current_ram_bytes >= 0
        assert report.peak_ram_mb >= 0.0

    def test_per_stage_keys(self) -> None:
        comp = _make_comp(duration=5)
        report = memory_report(comp, n_frames=2)
        assert "baseline" in report.per_stage
        assert "render" in report.per_stage

    def test_caps_at_duration(self) -> None:
        comp = _make_comp(duration=3)
        memory_report(comp, n_frames=100)
        # Should only render 3 frames
        assert comp._render_frame.call_count == 3


# ---------------------------------------------------------------------------
# detect_bottlenecks
# ---------------------------------------------------------------------------


class TestDetectBottlenecks:
    """Tests for detect_bottlenecks."""

    def test_basic_detection(self) -> None:
        comp = _make_comp(duration=5, n_clips=3)
        bottlenecks = detect_bottlenecks(comp, n_frames=5)
        assert isinstance(bottlenecks, list)
        assert all(isinstance(b, Bottleneck) for b in bottlenecks)

    def test_top_n_limit(self) -> None:
        comp = _make_comp(duration=5, n_clips=10)
        bottlenecks = detect_bottlenecks(comp, n_frames=5, top_n=3)
        assert len(bottlenecks) <= 3

    def test_bottleneck_fields(self) -> None:
        comp = _make_comp(duration=3, n_clips=1)
        bottlenecks = detect_bottlenecks(comp, n_frames=3)
        if bottlenecks:
            b = bottlenecks[0]
            assert b.category == "clip"
            assert b.time_ms >= 0
            assert 0 <= b.percentage <= 100
            assert len(b.description) > 0

    def test_sorted_by_time(self) -> None:
        comp = _make_comp(duration=5, n_clips=5)
        bottlenecks = detect_bottlenecks(comp, n_frames=5)
        times = [b.time_ms for b in bottlenecks]
        assert times == sorted(times, reverse=True)

    def test_no_clips_no_bottlenecks(self) -> None:
        comp = _make_comp(duration=3, n_clips=0)
        bottlenecks = detect_bottlenecks(comp, n_frames=3)
        assert bottlenecks == []


# ---------------------------------------------------------------------------
# frame_diff
# ---------------------------------------------------------------------------


class TestFrameDiff:
    """Tests for frame_diff."""

    def test_identical_frames(self) -> None:
        frame = np.full((4, 4, 4), 128, dtype=np.uint8)
        result = frame_diff(frame, frame.copy())
        assert isinstance(result, FrameDiff)
        assert result.identical is True
        assert result.max_diff == 0
        assert result.mean_diff == 0.0
        assert result.psnr == float("inf")
        assert result.changed_pixels == 0
        assert result.total_pixels == 16

    def test_different_frames(self) -> None:
        a = np.zeros((4, 4, 4), dtype=np.uint8)
        b = np.full((4, 4, 4), 50, dtype=np.uint8)
        result = frame_diff(a, b)
        assert result.identical is False
        assert result.max_diff == 50
        assert result.mean_diff > 0
        assert result.psnr > 0
        assert result.changed_pixels == 16

    def test_diff_image_shape(self) -> None:
        a = np.zeros((8, 6, 4), dtype=np.uint8)
        b = np.ones((8, 6, 4), dtype=np.uint8) * 10
        result = frame_diff(a, b)
        assert result.diff_image.shape == (8, 6, 4)
        assert result.diff_image.dtype == np.uint8

    def test_mismatched_shapes_raises(self) -> None:
        a = np.zeros((4, 4, 4), dtype=np.uint8)
        b = np.zeros((8, 8, 4), dtype=np.uint8)
        with pytest.raises(ValueError, match="shapes must match"):
            frame_diff(a, b)

    def test_psnr_finite_for_different_frames(self) -> None:
        a = np.zeros((4, 4, 4), dtype=np.uint8)
        b = np.full((4, 4, 4), 128, dtype=np.uint8)
        result = frame_diff(a, b)
        assert result.psnr > 0
        assert result.psnr < 100  # Reasonable range

    def test_partial_difference(self) -> None:
        a = np.zeros((4, 4, 4), dtype=np.uint8)
        b = a.copy()
        b[0, 0, 0] = 100  # One channel of one pixel differs
        result = frame_diff(a, b)
        assert result.identical is False
        assert result.changed_pixels == 1
        assert result.max_diff == 100

    def test_only_alpha_difference(self) -> None:
        a = np.full((4, 4, 4), 100, dtype=np.uint8)
        b = a.copy()
        b[:, :, 3] = 200  # Only alpha channel changes
        result = frame_diff(a, b)
        # changed_pixels counts RGB channels only
        assert result.changed_pixels == 0
        assert result.identical is False  # max_diff includes alpha
