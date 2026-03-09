"""Phase 0.3 exit criteria — validate 3D, particles, audio analysis, color pipeline.

Verifies that all Phase 0.3 components can be created and configured
together for a product showcase scenario.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from pymotion.audio.analysis import BeatDetector, OnsetDetector, WaveformExtractor
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.scene3d import Scene3D, Scene3DClip
from pymotion.particle.system import (
    Emitter,
    ParticleSystem,
    confetti,
    fire,
    sparkles,
)
from pymotion.render.backend_3d import (
    AmbientLight,
    BloomConfig,
    Camera,
    DepthOfFieldConfig,
    DirectionalLight,
    PBRMaterial,
    PointLight,
    SSAOConfig,
)
from pymotion.render.color_pipeline import (
    ColorGrade,
    apply_color_grade,
    apply_color_pipeline,
    apply_lut_trilinear,
    parse_cube_lut,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2, Vec3


def _make_identity_cube(size: int = 2) -> str:
    lines = [f"LUT_3D_SIZE {size}"]
    for b in range(size):
        for g in range(size):
            for r in range(size):
                rv = r / max(size - 1, 1)
                gv = g / max(size - 1, 1)
                bv = b / max(size - 1, 1)
                lines.append(f"{rv:.6f} {gv:.6f} {bv:.6f}")
    return "\n".join(lines)


class TestPhase03Exit:
    """Validate all Phase 0.3 components integrate correctly."""

    def test_3d_scene_creation(self) -> None:
        """Create a 3D scene with camera, lights, and model."""
        scene = Scene3D(width=320, height=240)

        # Set camera for product showcase
        scene.camera = Camera(
            position=Vec3(3.0, 2.0, 3.0),
            target=Vec3(0.0, 0.0, 0.0),
            fov=45.0,
        )

        # Add lights
        scene.add_light(AmbientLight(intensity=0.2))
        scene.add_light(
            DirectionalLight(
                direction=Vec3(-1.0, -1.0, -1.0),
                intensity=1.5,
            )
        )
        scene.add_light(
            PointLight(
                position=Vec3(2.0, 3.0, 2.0),
                intensity=2.0,
                radius=10.0,
            )
        )

        # Add OBJ model
        obj_content = """
v -1.0 -1.0  1.0
v  1.0 -1.0  1.0
v  1.0  1.0  1.0
v -1.0  1.0  1.0
v -1.0 -1.0 -1.0
v  1.0 -1.0 -1.0
v  1.0  1.0 -1.0
v -1.0  1.0 -1.0
vn  0.0  0.0  1.0
vn  1.0  0.0  0.0
vn  0.0  0.0 -1.0
vn -1.0  0.0  0.0
vn  0.0  1.0  0.0
vn  0.0 -1.0  0.0
f 1//1 2//1 3//1 4//1
f 2//2 6//2 7//2 3//2
f 6//3 5//3 8//3 7//3
f 5//4 1//4 4//4 8//4
f 4//5 3//5 7//5 8//5
f 5//6 6//6 2//6 1//6
"""
        with tempfile.NamedTemporaryFile(suffix=".obj", mode="w", delete=False) as f:
            f.write(obj_content)
            f.flush()
            path = Path(f.name)

        material = PBRMaterial(
            albedo=Color(0.8, 0.2, 0.1),
            metallic=0.7,
            roughness=0.3,
            emissive=Color(0.0, 0.0, 0.0),
        )
        model = scene.load_model(path, material=material)
        assert model is not None
        path.unlink()

        # Add post-effects
        scene.add_effect(BloomConfig(threshold=0.8, intensity=1.0))
        scene.add_effect(SSAOConfig(radius=0.5, samples=16))
        scene.add_effect(DepthOfFieldConfig(focus_distance=5.0, aperture=0.1))

        # Convert to clip
        clip = scene.to_clip(duration=90)
        assert clip.duration == 90
        assert isinstance(clip, Scene3DClip)

    def test_three_particle_effects(self) -> None:
        """Create 3 distinct particle effects for the showcase."""
        # Effect 1: Sparkles around product
        ps1 = sparkles(width=320, height=240)
        for _ in range(10):
            frame1 = ps1.simulate_frame()
        assert frame1.shape == (240, 320, 4)
        assert frame1.dtype == np.uint8

        # Effect 2: Fire
        ps2 = fire(width=320, height=240)
        for _ in range(10):
            frame2 = ps2.simulate_frame()
        assert frame2.shape == (240, 320, 4)

        # Effect 3: Confetti
        ps3 = confetti(width=320, height=240)
        for _ in range(10):
            frame3 = ps3.simulate_frame()
        assert frame3.shape == (240, 320, 4)

        # All should have active particles
        assert ps1.particle_count > 0
        assert ps2.particle_count > 0
        assert ps3.particle_count > 0

    def test_audio_analysis(self) -> None:
        """Analyze audio for beat-synchronized effects."""
        sr = 22050
        duration = 4.0
        n = int(sr * duration)

        # Create synthetic audio with beats
        audio = np.zeros(n, dtype=np.float32)
        bpm = 120
        beat_interval = int(sr * 60 / bpm)
        for i in range(0, n, beat_interval):
            end = min(i + 200, n)
            audio[i:end] = 0.8

        # Beat detection
        beats = BeatDetector().detect(audio, sample_rate=sr, fps=30)
        assert isinstance(beats, list)
        assert len(beats) > 0

        # Onset detection
        onsets = OnsetDetector().detect(audio, sample_rate=sr, fps=30)
        assert isinstance(onsets, list)

        # Waveform extraction
        envelope = WaveformExtractor().extract(audio, n_points=100)
        assert envelope.shape == (100,)
        assert float(np.max(envelope)) == 1.0

    def test_color_pipeline_integration(self) -> None:
        """Apply LUT and color grade to a frame."""
        # Create test frame
        frame = np.zeros((240, 320, 4), dtype=np.uint8)
        frame[:, :, 0] = 60  # B
        frame[:, :, 1] = 120  # G
        frame[:, :, 2] = 200  # R
        frame[:, :, 3] = 255  # A

        # Apply LUT
        lut = parse_cube_lut(_make_identity_cube(3))
        result = apply_lut_trilinear(frame, lut)
        assert result.shape == frame.shape

        # Apply grade
        grade = ColorGrade(
            lift=(0.02, 0.0, -0.02),
            gamma=(1.1, 1.0, 0.9),
            gain=(1.0, 1.05, 1.1),
            saturation=1.2,
        )
        graded = apply_color_grade(result, grade)
        assert graded.shape == frame.shape

        # Full pipeline
        final = apply_color_pipeline(frame, lut=lut, grade=grade)
        assert final.shape == frame.shape
        assert final.dtype == np.uint8

    def test_particle_clip_rendering(self) -> None:
        """ParticleClip produces valid BGRA frames via RenderContext."""
        ps = ParticleSystem(320, 240)
        ps.add_emitter(
            Emitter(
                position=Vec2(160.0, 120.0),
                rate=20.0,
                lifetime=(30.0, 60.0),
                speed=(2.0, 5.0),
                size=(2.0, 6.0),
                color_over_life=[Color(1.0, 0.8, 0.0), Color(1.0, 0.0, 0.0)],
                opacity_over_life=[1.0, 0.5, 0.0],
            )
        )
        clip = ps.to_clip(duration=90)

        ctx = RenderContext(
            frame=30,
            fps=30,
            resolution=Resolution(320, 240),
            time_range=TimeRange(0, 90),
            local_frame=30,
            progress=30 / 90,
        )
        frame = clip.render_frame(ctx)
        assert frame.shape == (240, 320, 4)
        assert frame.dtype == np.uint8
        # Should have some non-zero pixels
        assert np.any(frame > 0)
