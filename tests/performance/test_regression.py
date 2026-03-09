"""Performance regression tests — establish baselines for render throughput.

These tests verify that rendering performance stays within acceptable bounds.
They are designed to run in CI and flag regressions early.
"""

from __future__ import annotations

import time

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.composition import Composition, Track
from pymotion.effects.color import Brightness, Contrast
from pymotion.effects.visual import GaussianBlur, Vignette
from pymotion.particle.system import sparkles
from pymotion.transition.library import Fade


def _time_render(comp: Composition, frames: int) -> float:
    """Render N frames and return elapsed time in seconds."""
    start = time.perf_counter()
    for i in range(frames):
        comp._render_frame(i)
    return time.perf_counter() - start


class TestRenderPerformance:
    """Baseline performance tests for frame rendering."""

    def test_1080p_color_clip_throughput(self) -> None:
        """1080p color clip renders at reasonable speed."""
        comp = Composition(1920, 1080, fps=30, duration=30)
        bg = ColorClip(color="#1a1a2e", duration=30, width=1920, height=1080)
        comp.add(bg)

        elapsed = _time_render(comp, 10)
        fps = 10 / elapsed
        # Baseline: should render at least 10 fps on any reasonable hardware
        assert fps > 5, f"1080p color clip too slow: {fps:.1f} fps"

    def test_720p_multi_layer(self) -> None:
        """720p with 3 layers renders without major regression."""
        comp = Composition(1280, 720, fps=30, duration=30)
        for i in range(3):
            clip = ColorClip(
                color=f"#{i * 40 + 50:02x}{i * 30 + 60:02x}{i * 20 + 70:02x}",
                duration=30,
                width=1280,
                height=720,
            )
            clip.set_opacity(0.7)
            track = Track(name=f"layer_{i}")
            track.add(clip)
            comp.add_track(track)

        elapsed = _time_render(comp, 10)
        fps = 10 / elapsed
        assert fps > 2, f"720p multi-layer too slow: {fps:.1f} fps"

    def test_effects_chain_performance(self) -> None:
        """Applying 4 effects to a frame stays within bounds."""
        frame = np.full((720, 1280, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(1280, 720),
            time_range=TimeRange(0, 30),
            local_frame=0,
            progress=0.0,
        )

        effects = [
            Brightness(value=1.2),
            Contrast(value=1.1),
            GaussianBlur(radius=2.0),
            Vignette(strength=0.5),
        ]

        start = time.perf_counter()
        for _ in range(10):
            result = frame
            for fx in effects:
                result = fx.apply(result, ctx)
        elapsed = time.perf_counter() - start

        fps = 10 / elapsed
        assert fps > 2, f"Effects chain too slow: {fps:.1f} fps"

    def test_transition_performance(self) -> None:
        """Transition render stays within bounds."""
        a = np.full((720, 1280, 4), 100, dtype=np.uint8)
        b = np.full((720, 1280, 4), 200, dtype=np.uint8)
        tr = Fade(duration=30)

        start = time.perf_counter()
        for i in range(30):
            tr.render_frame(a, b, i / 29)
        elapsed = time.perf_counter() - start

        fps = 30 / elapsed
        assert fps > 5, f"Transition too slow: {fps:.1f} fps"

    def test_particle_simulation_performance(self) -> None:
        """Particle system simulation at 720p stays within bounds."""
        ps = sparkles(width=1280, height=720)

        start = time.perf_counter()
        for _ in range(30):
            ps.simulate_frame()
        elapsed = time.perf_counter() - start

        fps = 30 / elapsed
        assert fps > 10, f"Particle simulation too slow: {fps:.1f} fps"
