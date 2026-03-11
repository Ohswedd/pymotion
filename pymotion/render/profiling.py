"""Profiling & diagnostics — render timing, benchmarking, memory tracking,
bottleneck detection, and frame diff comparison.

Provides tools for measuring and optimizing render pipeline performance.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes for profiling results
# ---------------------------------------------------------------------------


@dataclass
class ClipTiming:
    """Timing data for a single clip render.

    Attributes:
        track_name: Name of the track containing the clip.
        clip_index: Index of the clip within the track.
        clip_type: Type name of the clip class.
        render_ms: Time spent rendering in milliseconds.
        effects_count: Number of effects applied.
    """

    track_name: str
    clip_index: int
    clip_type: str
    render_ms: float
    effects_count: int


@dataclass
class FrameProfile:
    """Profiling data for a single frame render.

    Attributes:
        frame: Frame number.
        total_ms: Total render time in milliseconds.
        composite_ms: Time spent compositing layers.
        clip_timings: Per-clip timing breakdown.
    """

    frame: int
    total_ms: float
    composite_ms: float
    clip_timings: list[ClipTiming] = field(default_factory=list)


@dataclass
class RenderProfile:
    """Aggregate profiling data for a full render.

    Attributes:
        total_frames: Number of frames rendered.
        total_ms: Total render time in milliseconds.
        avg_frame_ms: Average time per frame.
        min_frame_ms: Fastest frame render time.
        max_frame_ms: Slowest frame render time.
        fps_achieved: Effective frames per second.
        frame_profiles: Per-frame profiles (if detailed=True).
    """

    total_frames: int
    total_ms: float
    avg_frame_ms: float
    min_frame_ms: float
    max_frame_ms: float
    fps_achieved: float
    frame_profiles: list[FrameProfile] = field(default_factory=list)


@dataclass
class MemoryReport:
    """Memory usage report for a render.

    Attributes:
        peak_ram_bytes: Peak RAM usage during render.
        current_ram_bytes: Current RAM usage.
        peak_ram_mb: Peak RAM in megabytes.
        per_stage: Per-stage memory snapshots.
    """

    peak_ram_bytes: int
    current_ram_bytes: int
    peak_ram_mb: float
    per_stage: dict[str, int] = field(default_factory=dict)


@dataclass
class Bottleneck:
    """Identified performance bottleneck.

    Attributes:
        category: Type of bottleneck (``"clip"``, ``"effect"``, ``"composite"``).
        description: Human-readable description of the bottleneck.
        time_ms: Time consumed by this bottleneck.
        percentage: Percentage of total render time.
    """

    category: str
    description: str
    time_ms: float
    percentage: float


@dataclass
class FrameDiff:
    """Result of a pixel-level frame comparison.

    Attributes:
        diff_image: Absolute difference image (H, W, 4), dtype uint8.
        max_diff: Maximum pixel difference across all channels.
        mean_diff: Mean pixel difference.
        psnr: Peak signal-to-noise ratio in dB (inf if identical).
        identical: True if frames are pixel-identical.
        changed_pixels: Number of pixels with any difference.
        total_pixels: Total number of pixels.
    """

    diff_image: np.ndarray
    max_diff: int
    mean_diff: float
    psnr: float
    identical: bool
    changed_pixels: int
    total_pixels: int


# ---------------------------------------------------------------------------
# Profiled rendering
# ---------------------------------------------------------------------------


def profile_composition(
    composition: Any,
    start: int = 0,
    end: int | None = None,
    *,
    detailed: bool = True,
) -> RenderProfile:
    """Profile a composition's render performance.

    Renders frames and collects per-frame and per-clip timing data.
    Does not encode to a file — only measures the frame rendering pipeline.

    Args:
        composition: The Composition to profile.
        start: Start frame (inclusive).
        end: End frame (exclusive). Defaults to composition duration.
        detailed: If True, collect per-clip timing for each frame.

    Returns:
        A RenderProfile with timing statistics.
    """
    if end is None:
        end = composition.duration

    frame_profiles: list[FrameProfile] = []
    frame_times: list[float] = []

    total_t0 = time.perf_counter()

    for frame_idx in range(start, end):
        frame_t0 = time.perf_counter()

        clip_timings: list[ClipTiming] = []

        if detailed:
            # Profile individual clips
            for track in composition.tracks:
                if not track.visible or track.opacity <= 0.0:
                    continue
                for clip_idx, clip in enumerate(track.clips):
                    if clip.start <= frame_idx < clip.end:
                        clip_t0 = time.perf_counter()
                        local_frame = frame_idx - clip.start
                        clip_duration = clip.end - clip.start
                        progress = local_frame / max(clip_duration - 1, 1)

                        from pymotion.clip.base import RenderContext, TimeRange

                        ctx = RenderContext(
                            frame=frame_idx,
                            fps=composition.fps,
                            resolution=composition.resolution,
                            time_range=TimeRange(start=clip.start, end=clip.end),
                            local_frame=local_frame,
                            progress=progress,
                        )
                        clip.render_with_effects(ctx)
                        clip_dt = (time.perf_counter() - clip_t0) * 1000

                        effects_count = len(clip._effects if hasattr(clip, "_effects") else [])
                        clip_timings.append(
                            ClipTiming(
                                track_name=track.name,
                                clip_index=clip_idx,
                                clip_type=type(clip).__name__,
                                render_ms=round(clip_dt, 3),
                                effects_count=effects_count,
                            )
                        )

        # Full frame render (includes compositing)
        composite_t0 = time.perf_counter()
        composition._render_frame(frame_idx)
        composite_dt = (time.perf_counter() - composite_t0) * 1000

        frame_dt = (time.perf_counter() - frame_t0) * 1000
        frame_times.append(frame_dt)

        if detailed:
            frame_profiles.append(
                FrameProfile(
                    frame=frame_idx,
                    total_ms=round(frame_dt, 3),
                    composite_ms=round(composite_dt, 3),
                    clip_timings=clip_timings,
                )
            )

    total_ms = (time.perf_counter() - total_t0) * 1000
    n = len(frame_times)

    return RenderProfile(
        total_frames=n,
        total_ms=round(total_ms, 3),
        avg_frame_ms=round(total_ms / max(n, 1), 3),
        min_frame_ms=round(min(frame_times), 3) if frame_times else 0.0,
        max_frame_ms=round(max(frame_times), 3) if frame_times else 0.0,
        fps_achieved=round(n / (total_ms / 1000), 2) if total_ms > 0 else 0.0,
        frame_profiles=frame_profiles if detailed else [],
    )


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


def benchmark(
    composition: Any,
    n_frames: int = 100,
) -> RenderProfile:
    """Benchmark a composition's render throughput.

    Renders up to ``n_frames`` frames (or composition duration, whichever
    is smaller) and returns performance metrics.

    Args:
        composition: The Composition to benchmark.
        n_frames: Maximum number of frames to render.

    Returns:
        A RenderProfile with throughput statistics.
    """
    frame_count = min(n_frames, composition.duration)
    profile = profile_composition(composition, start=0, end=frame_count, detailed=False)

    logger.info(
        "benchmark_result",
        frames=profile.total_frames,
        total_ms=profile.total_ms,
        avg_ms=profile.avg_frame_ms,
        fps=profile.fps_achieved,
    )

    return profile


# ---------------------------------------------------------------------------
# Memory report
# ---------------------------------------------------------------------------


def memory_report(
    composition: Any,
    n_frames: int = 10,
) -> MemoryReport:
    """Measure memory usage during rendering.

    Uses ``tracemalloc`` to track peak and per-stage RAM allocation.
    Renders a small number of frames to sample memory behaviour.

    Args:
        composition: The Composition to analyze.
        n_frames: Number of frames to render for measurement.

    Returns:
        A MemoryReport with peak and per-stage memory data.
    """
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()

    stages: dict[str, int] = {}

    # Stage 1: baseline
    tracemalloc.reset_peak()
    _, peak_baseline = tracemalloc.get_traced_memory()
    stages["baseline"] = peak_baseline

    # Stage 2: render frames
    tracemalloc.reset_peak()
    frame_count = min(n_frames, composition.duration)
    for i in range(frame_count):
        composition._render_frame(i)
    current_render, peak_render = tracemalloc.get_traced_memory()
    stages["render"] = peak_render

    # Final snapshot
    current, peak = tracemalloc.get_traced_memory()

    if not was_tracing:
        tracemalloc.stop()

    return MemoryReport(
        peak_ram_bytes=peak,
        current_ram_bytes=current,
        peak_ram_mb=round(peak / (1024 * 1024), 2),
        per_stage=stages,
    )


# ---------------------------------------------------------------------------
# Bottleneck detector
# ---------------------------------------------------------------------------


def detect_bottlenecks(
    composition: Any,
    n_frames: int = 30,
    *,
    top_n: int = 5,
) -> list[Bottleneck]:
    """Identify the slowest clips and effects in a composition.

    Profiles a sample of frames and ranks clips by total render time.

    Args:
        composition: The Composition to analyze.
        n_frames: Number of frames to sample.
        top_n: Maximum number of bottlenecks to return.

    Returns:
        List of Bottleneck entries, sorted by time descending.
    """
    frame_count = min(n_frames, composition.duration)
    profile = profile_composition(composition, start=0, end=frame_count, detailed=True)

    # Aggregate clip timings by (track, clip_type, clip_index)
    clip_totals: dict[str, tuple[float, str]] = {}
    for fp in profile.frame_profiles:
        for ct in fp.clip_timings:
            key = f"{ct.track_name}:{ct.clip_type}[{ct.clip_index}]"
            if key in clip_totals:
                old_time, old_desc = clip_totals[key]
                clip_totals[key] = (old_time + ct.render_ms, old_desc)
            else:
                desc = (
                    f"{ct.clip_type} on '{ct.track_name}' "
                    f"(index {ct.clip_index}, {ct.effects_count} effects)"
                )
                clip_totals[key] = (ct.render_ms, desc)

    total_clip_ms = sum(t for t, _ in clip_totals.values())

    bottlenecks: list[Bottleneck] = []
    for _key, (time_ms, desc) in sorted(clip_totals.items(), key=lambda x: x[1][0], reverse=True)[
        :top_n
    ]:
        pct = (time_ms / total_clip_ms * 100) if total_clip_ms > 0 else 0.0
        bottlenecks.append(
            Bottleneck(
                category="clip",
                description=desc,
                time_ms=round(time_ms, 3),
                percentage=round(pct, 1),
            )
        )

    logger.info(
        "bottlenecks_detected",
        count=len(bottlenecks),
        total_clip_ms=round(total_clip_ms, 1),
    )

    return bottlenecks


# ---------------------------------------------------------------------------
# Frame diff
# ---------------------------------------------------------------------------


def frame_diff(frame_a: np.ndarray, frame_b: np.ndarray) -> FrameDiff:
    """Compare two frames pixel-by-pixel.

    Computes the absolute difference, PSNR, and change statistics.

    Args:
        frame_a: First BGRA frame (H, W, 4), dtype uint8.
        frame_b: Second BGRA frame (H, W, 4), dtype uint8.

    Returns:
        A FrameDiff with comparison metrics.

    Raises:
        ValueError: If frames have different shapes.
    """
    if frame_a.shape != frame_b.shape:
        msg = f"Frame shapes must match: {frame_a.shape} vs {frame_b.shape}"
        raise ValueError(msg)

    diff = np.abs(frame_a.astype(np.int16) - frame_b.astype(np.int16)).astype(np.uint8)
    max_diff = int(diff.max())
    mean_diff = float(diff.mean())

    # PSNR calculation
    mse = float(np.mean((frame_a.astype(np.float64) - frame_b.astype(np.float64)) ** 2))
    if mse == 0.0:
        psnr = float("inf")
    else:
        psnr = round(10.0 * np.log10(255.0**2 / mse), 2)

    # Changed pixel count (any channel differs)
    pixel_diffs = diff[:, :, :3].max(axis=2) > 0
    changed = int(pixel_diffs.sum())
    total = frame_a.shape[0] * frame_a.shape[1]

    identical = max_diff == 0

    return FrameDiff(
        diff_image=diff,
        max_diff=max_diff,
        mean_diff=round(mean_diff, 4),
        psnr=psnr,
        identical=identical,
        changed_pixels=changed,
        total_pixels=total,
    )
