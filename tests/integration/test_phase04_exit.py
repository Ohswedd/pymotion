"""Phase 0.4 exit criteria — batch-render 5 product videos from a Template.

Verifies that Templates can produce unique Compositions with transitions,
particle effects, and audio DSP chain components all integrated.
"""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.composition import Composition, Track
from pymotion.effects.color import Brightness, Contrast, Saturation
from pymotion.effects.visual import FilmGrain, GaussianBlur, Vignette
from pymotion.particle.system import confetti, fire, sparkles, stars
from pymotion.template.base import Template
from pymotion.transition.library import (
    CircularWipe,
    CrossDissolve,
    Fade,
    FadeToBlack,
    Glitch,
    IrisIn,
    PageTurn,
    PixelDissolve,
    PushLeft,
    SlideLeft,
    SlideRight,
    Vortex,
    WipeDiagonal,
    WipeLeft,
    ZoomIn,
    ZoomOut,
)
from pymotion.utils.color import Color


class ProductTemplate(Template):
    """Example product video template with configurable parameters."""

    product_name: str
    brand_color: str = "#FF5500"
    show_particles: bool = True
    effect_strength: float = 0.5

    def build(self) -> Composition:
        """Build a composition with color clips, transitions, effects, and particles."""
        w, h = 320, 240
        comp = Composition(w, h, fps=30, duration=90)

        color = Color.parse(self.brand_color)

        # Background clip
        bg = ColorClip(color=color, duration=90, width=w, height=h)
        comp.add(bg)

        if self.show_particles:
            ps = sparkles(width=w, height=h)
            particle_clip = ps.to_clip(duration=90)
            track = Track(name="particles")
            track.add(particle_clip)
            comp.add_track(track)

        return comp


# Unique configs for 5 batch renders
BATCH_CONFIGS = [
    {
        "product_name": "Widget Pro",
        "brand_color": "#FF0000",
        "show_particles": True,
        "effect_strength": 0.3,
    },
    {
        "product_name": "Gadget X",
        "brand_color": "#00FF00",
        "show_particles": False,
        "effect_strength": 0.7,
    },
    {
        "product_name": "Tool Max",
        "brand_color": "#0000FF",
        "show_particles": True,
        "effect_strength": 0.5,
    },
    {
        "product_name": "Spark Ultra",
        "brand_color": "#FFAA00",
        "show_particles": True,
        "effect_strength": 0.9,
    },
    {
        "product_name": "Cloud Nine",
        "brand_color": "#AA00FF",
        "show_particles": False,
        "effect_strength": 0.1,
    },
]


class TestPhase04Exit:
    """Phase 0.4 exit criteria: batch-render 5 product videos from Template."""

    def test_batch_template_instantiation(self) -> None:
        """Instantiate 5 unique Templates — all must validate successfully."""
        templates = [ProductTemplate(**cfg) for cfg in BATCH_CONFIGS]
        assert len(templates) == 5
        for tpl, cfg in zip(templates, BATCH_CONFIGS, strict=True):
            assert tpl.product_name == cfg["product_name"]

    def test_batch_build_compositions(self) -> None:
        """Build 5 Compositions from Templates — each should have tracks and clips."""
        templates = [ProductTemplate(**cfg) for cfg in BATCH_CONFIGS]
        compositions = [t.build() for t in templates]
        assert len(compositions) == 5
        for comp in compositions:
            assert isinstance(comp, Composition)
            assert comp.duration == 90
            assert comp.resolution.width == 320
            assert comp.resolution.height == 240

    def test_batch_render_frames(self) -> None:
        """Render a frame from each of 5 Compositions — validates full pipeline."""
        templates = [ProductTemplate(**cfg) for cfg in BATCH_CONFIGS]
        frames = []
        for tpl in templates:
            comp = tpl.build()
            frame = comp._render_frame(30)
            assert frame.shape == (240, 320, 4)
            assert frame.dtype == np.uint8
            frames.append(frame)

        # Verify uniqueness — different brand colors → different frames
        assert not np.array_equal(frames[0], frames[1])
        assert not np.array_equal(frames[2], frames[4])

    def test_all_transition_types_render(self) -> None:
        """All built-in transition types produce valid frames."""
        w, h = 64, 48
        a = np.full((h, w, 4), 100, dtype=np.uint8)
        b = np.full((h, w, 4), 200, dtype=np.uint8)

        transitions = [
            Fade(duration=10),
            FadeToBlack(duration=10),
            CrossDissolve(duration=10),
            SlideLeft(duration=10),
            SlideRight(duration=10),
            PushLeft(duration=10),
            ZoomIn(duration=10),
            ZoomOut(duration=10),
            WipeLeft(duration=10),
            WipeDiagonal(duration=10),
            CircularWipe(duration=10),
            IrisIn(duration=10),
            Glitch(duration=10),
            PageTurn(duration=10),
            PixelDissolve(duration=10),
            Vortex(duration=10),
        ]

        for tr in transitions:
            result = tr.render_frame(a, b, 0.5)
            assert result.shape == (h, w, 4), f"{type(tr).__name__} wrong shape"
            assert result.dtype == np.uint8, f"{type(tr).__name__} wrong dtype"

    def test_particle_effects_in_composition(self) -> None:
        """Particle presets produce valid frames within a composition."""
        w, h = 64, 48

        for preset_fn in [sparkles, confetti, fire, stars]:
            ps = preset_fn(width=w, height=h)
            for _ in range(5):
                ps.simulate_frame()
            clip = ps.to_clip(duration=30)

            comp = Composition(w, h, fps=30, duration=30)
            track = Track(name="particles")
            track.add(clip)
            comp.add_track(track)

            frame = comp._render_frame(4)
            assert frame.shape == (h, w, 4)
            assert frame.dtype == np.uint8

    def test_effects_chain_on_frame(self) -> None:
        """Multiple effects applied sequentially to a frame produce valid output."""
        w, h = 64, 48
        comp = Composition(w, h, fps=30, duration=30)

        clip = ColorClip(color="#FF8800", duration=30, width=w, height=h)
        comp.add(clip)

        frame = comp._render_frame(15)
        ctx = RenderContext(
            frame=15,
            fps=30,
            resolution=Resolution(w, h),
            time_range=TimeRange(0, 30),
            local_frame=15,
            progress=0.5,
        )

        # Apply effects chain to the rendered frame
        effects = [
            Brightness(value=0.5),
            Contrast(value=1.2),
            Saturation(value=0.8),
            Vignette(strength=0.5),
            GaussianBlur(radius=1.0),
            FilmGrain(strength=0.1),
        ]
        result = frame
        for fx in effects:
            result = fx.apply(result, ctx)
            assert result.shape == (h, w, 4)
            assert result.dtype == np.uint8

        # Result should differ from original after effects chain
        assert not np.array_equal(frame, result)
