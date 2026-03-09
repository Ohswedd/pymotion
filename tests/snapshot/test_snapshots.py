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
from pymotion.particle.system import Emitter, ParticleSystem, sparkles
from pymotion.render.color_pipeline import ColorGrade, apply_color_grade
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
