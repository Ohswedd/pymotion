"""4K rendering validation — verify end-to-end rendering at 3840x2160.

Tests that all clip types, effects, and compositing work correctly
at 4K resolution without memory errors or shape mismatches.
"""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.composition import Composition, Track
from pymotion.effects.color import Brightness, Contrast, Saturation
from pymotion.effects.visual import GaussianBlur, Vignette
from pymotion.particle.system import sparkles
from pymotion.render.color_pipeline import ColorGrade, apply_color_pipeline, tone_map_aces
from pymotion.transition.library import Fade

W_4K = 3840
H_4K = 2160


def _ctx_4k(frame: int = 0) -> RenderContext:
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(W_4K, H_4K),
        time_range=TimeRange(0, 30),
        local_frame=frame,
        progress=frame / 29 if frame < 30 else 1.0,
    )


class TestRender4K:
    """Validate rendering at 3840x2160 resolution."""

    def test_color_clip_4k(self) -> None:
        """ColorClip renders correct shape at 4K."""
        comp = Composition(W_4K, H_4K, fps=30, duration=10)
        bg = ColorClip(color="#1a1a2e", duration=10, width=W_4K, height=H_4K)
        comp.add(bg)
        frame = comp._render_frame(0)
        assert frame.shape == (H_4K, W_4K, 4)
        assert frame.dtype == np.uint8

    def test_gradient_clip_4k(self) -> None:
        """GradientClip renders at 4K."""
        comp = Composition(W_4K, H_4K, fps=30, duration=10)
        clip = GradientClip(color_start="#FF0000", color_end="#0000FF")
        clip.set_duration(10)
        comp.add(clip)
        frame = comp._render_frame(0)
        assert frame.shape == (H_4K, W_4K, 4)

    def test_multi_layer_4k(self) -> None:
        """Multi-layer compositing at 4K."""
        comp = Composition(W_4K, H_4K, fps=30, duration=10)
        bg = ColorClip(color="#111111", duration=10, width=W_4K, height=H_4K)
        comp.add(bg)

        overlay = ColorClip(color="#FF000080", duration=10, width=W_4K, height=H_4K)
        overlay.set_opacity(0.5)
        track = Track(name="overlay")
        track.add(overlay)
        comp.add_track(track)

        frame = comp._render_frame(5)
        assert frame.shape == (H_4K, W_4K, 4)

    def test_effects_at_4k(self) -> None:
        """Effects produce correct shape at 4K."""
        frame = np.full((H_4K, W_4K, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        ctx = _ctx_4k()

        for fx in [
            Brightness(value=1.2),
            Contrast(value=1.1),
            Saturation(value=0.9),
            Vignette(strength=0.5),
            GaussianBlur(radius=2.0),
        ]:
            result = fx.apply(frame, ctx)
            assert result.shape == (H_4K, W_4K, 4), f"{type(fx).__name__} shape mismatch"

    def test_transition_at_4k(self) -> None:
        """Transition renders at 4K."""
        a = np.full((H_4K, W_4K, 4), 100, dtype=np.uint8)
        b = np.full((H_4K, W_4K, 4), 200, dtype=np.uint8)
        result = Fade(duration=10).render_frame(a, b, 0.5)
        assert result.shape == (H_4K, W_4K, 4)

    def test_tone_mapping_at_4k(self) -> None:
        """Tone mapping works at 4K."""
        frame = np.full((H_4K, W_4K, 4), 180, dtype=np.uint8)
        frame[:, :, 3] = 255
        result = tone_map_aces(frame)
        assert result.shape == (H_4K, W_4K, 4)

    def test_color_pipeline_at_4k(self) -> None:
        """Full color pipeline at 4K."""
        frame = np.full((H_4K, W_4K, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        grade = ColorGrade(
            lift=(0.02, 0.0, -0.02),
            gamma=(1.1, 1.0, 0.9),
            gain=(1.0, 1.05, 1.1),
            saturation=1.2,
        )
        result = apply_color_pipeline(frame, grade=grade, tone_map="aces")
        assert result.shape == (H_4K, W_4K, 4)

    def test_particles_at_4k(self) -> None:
        """Particle system works at 4K resolution."""
        ps = sparkles(width=W_4K, height=H_4K)
        for _ in range(5):
            frame = ps.simulate_frame()
        assert frame.shape == (H_4K, W_4K, 4)
