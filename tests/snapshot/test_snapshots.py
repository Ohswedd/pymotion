"""Snapshot tests — compare rendered frames against stored references.

Reference frames are stored as .npy files in tests/snapshot/references/.
On first run with --update-snapshots, they are generated.
Subsequent runs compare against the stored references.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.shape import ShapeClip
from pymotion.effects.color import Brightness, Saturation
from pymotion.effects.distortion import WaveWarp
from pymotion.effects.light import NeonGlow
from pymotion.effects.visual import GaussianBlur, Vignette
from pymotion.particle.system import Emitter, ParticleSystem, sparkles
from pymotion.render.color_pipeline import ColorGrade, apply_color_grade
from pymotion.text.animated import Typewriter
from pymotion.transition.library import CrossDissolve, IrisIn, WipeDiagonal
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

REFS_DIR = Path(__file__).parent / "references"


def _make_ctx(
    width: int = 64,
    height: int = 48,
    frame: int = 0,
    duration: int = 30,
) -> RenderContext:
    """Create a test RenderContext."""
    return RenderContext(
        frame=frame,
        fps=30,
        resolution=Resolution(width, height),
        time_range=TimeRange(0, duration),
        local_frame=frame,
        progress=frame / max(duration, 1),
    )


def _save_or_compare(name: str, frame: np.ndarray, update: bool = False) -> None:
    """Save a new reference or compare against existing one.

    Args:
        name: Reference name (without extension).
        frame: BGRA frame to compare.
        update: If True, save as new reference.
    """
    ref_path = REFS_DIR / f"{name}.npy"

    if update or not ref_path.exists():
        REFS_DIR.mkdir(parents=True, exist_ok=True)
        np.save(ref_path, frame)
        return

    ref = np.load(ref_path)
    np.testing.assert_array_equal(
        frame,
        ref,
        err_msg=f"Snapshot mismatch for '{name}'. Run with --update-snapshots to regenerate.",
    )


class TestColorClipSnapshots:
    def test_solid_red(self) -> None:
        clip = ColorClip(color=Color(1.0, 0.0, 0.0))
        clip.set_duration(30)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        _save_or_compare("color_solid_red", frame)

    def test_solid_blue(self) -> None:
        clip = ColorClip(color=Color(0.0, 0.0, 1.0))
        clip.set_duration(30)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        _save_or_compare("color_solid_blue", frame)


class TestGradientClipSnapshots:
    def test_linear_gradient(self) -> None:
        clip = GradientClip(
            color_start=Color(1.0, 0.0, 0.0),
            color_end=Color(0.0, 0.0, 1.0),
            gradient_type="linear",
            direction=0.0,
        )
        clip.set_duration(30)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        _save_or_compare("gradient_linear_rb", frame)

    def test_radial_gradient(self) -> None:
        clip = GradientClip(
            color_start=Color(1.0, 1.0, 1.0),
            color_end=Color(0.0, 0.0, 0.0),
            gradient_type="radial",
        )
        clip.set_duration(30)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        _save_or_compare("gradient_radial_wb", frame)


class TestParticleSnapshots:
    def test_sparkles_frame5(self) -> None:
        ps = sparkles(width=64, height=48)
        for _ in range(5):
            frame = ps.simulate_frame()
        _save_or_compare("particles_sparkles_f5", frame)

    def test_particle_custom(self) -> None:
        ps = ParticleSystem(64, 48)
        ps.add_emitter(
            Emitter(
                position=Vec2(32.0, 24.0),
                rate=20.0,
                lifetime=(10.0, 20.0),
                speed=(1.0, 3.0),
                size=(2.0, 4.0),
                color_over_life=[Color(1.0, 0.5, 0.0), Color(1.0, 0.0, 0.0)],
            )
        )
        for _ in range(10):
            frame = ps.simulate_frame()
        _save_or_compare("particles_custom_f10", frame)


class TestColorGradeSnapshots:
    def test_warm_grade(self) -> None:
        # Create a neutral gray frame
        frame = np.full((48, 64, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        grade = ColorGrade(
            gain=(1.2, 1.0, 0.8),
            saturation=1.2,
        )
        result = apply_color_grade(frame, grade)
        _save_or_compare("grade_warm", result)

    def test_desaturated(self) -> None:
        frame = np.zeros((48, 64, 4), dtype=np.uint8)
        frame[:, :, 0] = 50  # B
        frame[:, :, 1] = 100  # G
        frame[:, :, 2] = 200  # R
        frame[:, :, 3] = 255
        grade = ColorGrade(saturation=0.0)
        result = apply_color_grade(frame, grade)
        _save_or_compare("grade_desaturated", result)


class TestShapeClipSnapshots:
    def test_circle(self) -> None:
        clip = ShapeClip(
            shape_type="circle",
            fill_color=Color(0.0, 1.0, 0.0),
            params={"radius": 20.0},
        )
        clip.set_duration(30)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        _save_or_compare("shape_circle_green", frame)

    def test_rect(self) -> None:
        clip = ShapeClip(
            shape_type="rect",
            fill_color=Color(1.0, 1.0, 0.0),
            params={"width": 50.0, "height": 30.0},
        )
        clip.set_duration(30)
        ctx = _make_ctx()
        frame = clip.render_frame(ctx)
        _save_or_compare("shape_rect_yellow", frame)


class TestEffectSnapshots:
    def test_gaussian_blur(self) -> None:
        frame = np.zeros((48, 64, 4), dtype=np.uint8)
        frame[20:28, 28:36, 2] = 255  # Red square
        frame[:, :, 3] = 255
        ctx = _make_ctx()
        result = GaussianBlur(radius=3.0).apply(frame, ctx)
        _save_or_compare("effect_gaussian_blur", result)

    def test_vignette(self) -> None:
        frame = np.full((48, 64, 4), 200, dtype=np.uint8)
        frame[:, :, 3] = 255
        ctx = _make_ctx()
        result = Vignette(strength=0.8).apply(frame, ctx)
        _save_or_compare("effect_vignette", result)

    def test_neon_glow(self) -> None:
        frame = np.zeros((48, 64, 4), dtype=np.uint8)
        frame[20:28, 28:36] = [255, 0, 255, 255]  # Magenta square
        ctx = _make_ctx()
        result = NeonGlow(strength=1.0, radius=3.0).apply(frame, ctx)
        _save_or_compare("effect_neon_glow", result)

    def test_brightness(self) -> None:
        frame = np.full((48, 64, 4), 100, dtype=np.uint8)
        frame[:, :, 3] = 255
        ctx = _make_ctx()
        result = Brightness(value=1.5).apply(frame, ctx)
        _save_or_compare("effect_brightness", result)

    def test_saturation(self) -> None:
        frame = np.zeros((48, 64, 4), dtype=np.uint8)
        frame[:, :, 0] = 50
        frame[:, :, 1] = 100
        frame[:, :, 2] = 200
        frame[:, :, 3] = 255
        ctx = _make_ctx()
        result = Saturation(value=0.0).apply(frame, ctx)
        _save_or_compare("effect_desaturated", result)

    def test_wave_warp(self) -> None:
        frame = np.zeros((48, 64, 4), dtype=np.uint8)
        for y in range(48):
            frame[y, :, 1] = int(y / 48 * 255)
        frame[:, :, 3] = 255
        ctx = _make_ctx(frame=5)
        result = WaveWarp(amplitude=5.0, frequency=2.0).apply(frame, ctx)
        _save_or_compare("effect_wave_warp", result)


class TestTransitionSnapshots:
    def test_cross_dissolve_50(self) -> None:
        a = np.zeros((48, 64, 4), dtype=np.uint8)
        a[:, :, 2] = 255  # Red
        a[:, :, 3] = 255
        b = np.zeros((48, 64, 4), dtype=np.uint8)
        b[:, :, 0] = 255  # Blue
        b[:, :, 3] = 255
        result = CrossDissolve().render_frame(a, b, 0.5)
        _save_or_compare("transition_dissolve_50", result)

    def test_iris_in_30(self) -> None:
        a = np.full((48, 64, 4), 100, dtype=np.uint8)
        a[:, :, 3] = 255
        b = np.full((48, 64, 4), 200, dtype=np.uint8)
        b[:, :, 3] = 255
        result = IrisIn().render_frame(a, b, 0.3)
        _save_or_compare("transition_iris_in_30", result)

    def test_wipe_diagonal_50(self) -> None:
        a = np.zeros((48, 64, 4), dtype=np.uint8)
        a[:, :, 2] = 255
        a[:, :, 3] = 255
        b = np.zeros((48, 64, 4), dtype=np.uint8)
        b[:, :, 1] = 255
        b[:, :, 3] = 255
        result = WipeDiagonal().render_frame(a, b, 0.5)
        _save_or_compare("transition_wipe_diag_50", result)


class TestAnimatedTextSnapshots:
    def test_typewriter(self) -> None:
        clip = Typewriter(text="Hello")
        ctx = _make_ctx(width=120, height=60, frame=10, duration=60)
        frame = clip.render_frame(ctx)
        _save_or_compare("text_typewriter", frame)
