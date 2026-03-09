"""Unit tests for particle/system.py — ParticleSystem, Emitter, presets."""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import BlendMode, RenderContext, Resolution, TimeRange
from pymotion.particle.system import (
    Emitter,
    ParticleClip,
    ParticleSystem,
    confetti,
    fire,
    rain,
    smoke,
    sparkles,
)
from pymotion.utils.math import Vec2


class TestEmitter:
    def test_defaults(self) -> None:
        e = Emitter()
        assert e.rate == 10.0
        assert e.drag == 0.0
        assert e.turbulence == 0.0
        assert e.blend_mode == BlendMode.ADD

    def test_custom(self) -> None:
        e = Emitter(
            position=Vec2(100.0, 200.0),
            rate=50.0,
            lifetime=(10.0, 20.0),
            speed=(3.0, 8.0),
            gravity=Vec2(0.0, 0.5),
            drag=0.05,
        )
        assert e.position == Vec2(100.0, 200.0)
        assert e.gravity == Vec2(0.0, 0.5)


class TestParticleSystem:
    def test_creation(self) -> None:
        ps = ParticleSystem(320, 240)
        assert ps._width == 320
        assert ps._height == 240
        assert ps.particle_count == 0

    def test_add_emitter(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(rate=5.0))
        assert len(ps._emitters) == 1

    def test_simulate_spawns_particles(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(position=Vec2(160.0, 120.0), rate=10.0))
        ps.simulate_frame()
        assert ps.particle_count == 10

    def test_simulate_multiple_frames(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(rate=5.0, lifetime=(100.0, 100.0)))
        for _ in range(10):
            ps.simulate_frame()
        assert ps.particle_count == 50

    def test_particles_die(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(rate=10.0, lifetime=(5.0, 5.0)))
        for _ in range(20):
            ps.simulate_frame()
        # After 20 frames, particles from early frames should be dead
        assert ps.particle_count < 200

    def test_simulate_frame_returns_bgra(self) -> None:
        ps = ParticleSystem(64, 48)
        ps.add_emitter(
            Emitter(
                position=Vec2(32.0, 24.0),
                rate=5.0,
                size=(2.0, 4.0),
            )
        )
        frame = ps.simulate_frame()
        assert frame.shape == (48, 64, 4)
        assert frame.dtype == np.uint8

    def test_gravity_moves_particles(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(
            Emitter(
                position=Vec2(160.0, 10.0),
                rate=1.0,
                lifetime=(100.0, 100.0),
                speed=(0.0, 0.0),
                gravity=Vec2(0.0, 1.0),
            )
        )
        ps.simulate_frame()  # spawn
        initial_y = ps._pos[0, 1]
        ps.simulate_frame()  # update
        assert ps._pos[0, 1] > initial_y

    def test_drag_slows_particles(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(
            Emitter(
                position=Vec2(160.0, 120.0),
                rate=1.0,
                lifetime=(100.0, 100.0),
                speed=(10.0, 10.0),
                angle=(0.0, 0.0),
                drag=0.5,
            )
        )
        ps.simulate_frame()
        vel_before = float(np.sqrt(ps._vel[0, 0] ** 2 + ps._vel[0, 1] ** 2))
        ps.simulate_frame()
        vel_after = float(np.sqrt(ps._vel[0, 0] ** 2 + ps._vel[0, 1] ** 2))
        assert vel_after < vel_before

    def test_reset(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(rate=10.0))
        ps.simulate_frame()
        assert ps.particle_count > 0
        ps.reset()
        assert ps.particle_count == 0

    def test_empty_system_renders_black(self) -> None:
        ps = ParticleSystem(64, 48)
        frame = ps.simulate_frame()
        assert frame.shape == (48, 64, 4)
        np.testing.assert_array_equal(frame, np.zeros_like(frame))

    def test_to_clip(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(rate=5.0))
        clip = ps.to_clip(duration=60)
        assert isinstance(clip, ParticleClip)
        assert clip.duration == 60

    def test_max_particles_cap(self) -> None:
        """Should not exceed _MAX_PARTICLES."""
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(rate=10000.0, lifetime=(1000.0, 1000.0)))
        for _ in range(20):
            ps.simulate_frame()
        assert ps.particle_count <= 100_000

    def test_multiple_emitters(self) -> None:
        ps = ParticleSystem(320, 240)
        ps.add_emitter(Emitter(position=Vec2(100.0, 100.0), rate=5.0))
        ps.add_emitter(Emitter(position=Vec2(200.0, 200.0), rate=3.0))
        ps.simulate_frame()
        assert ps.particle_count == 8


class TestParticleClip:
    def test_render_frame(self) -> None:
        ps = ParticleSystem(64, 48)
        ps.add_emitter(Emitter(position=Vec2(32.0, 24.0), rate=5.0))
        clip = ps.to_clip(duration=30)
        ctx = RenderContext(
            frame=5,
            fps=30,
            resolution=Resolution(64, 48),
            time_range=TimeRange(0, 30),
            local_frame=5,
            progress=5 / 30,
        )
        frame = clip.render_frame(ctx)
        assert frame.shape == (48, 64, 4)
        assert frame.dtype == np.uint8

    def test_deterministic(self) -> None:
        """Same frame number should produce same output."""
        ps = ParticleSystem(64, 48)
        ps.add_emitter(Emitter(position=Vec2(32.0, 24.0), rate=5.0))
        clip = ps.to_clip(duration=30)
        ctx = RenderContext(
            frame=10,
            fps=30,
            resolution=Resolution(64, 48),
            time_range=TimeRange(0, 30),
            local_frame=10,
            progress=10 / 30,
        )
        frame1 = clip.render_frame(ctx)
        frame2 = clip.render_frame(ctx)
        np.testing.assert_array_equal(frame1, frame2)


class TestPresets:
    def test_sparkles(self) -> None:
        ps = sparkles(width=64, height=48)
        assert len(ps._emitters) == 1
        frame = ps.simulate_frame()
        assert frame.shape == (48, 64, 4)

    def test_confetti(self) -> None:
        ps = confetti(width=64, height=48)
        assert len(ps._emitters) == 1

    def test_fire(self) -> None:
        ps = fire(width=64, height=48)
        assert len(ps._emitters) == 1

    def test_smoke(self) -> None:
        ps = smoke(width=64, height=48)
        assert len(ps._emitters) == 1

    def test_rain(self) -> None:
        ps = rain(width=64, height=48)
        assert len(ps._emitters) == 1

    def test_all_presets_render(self) -> None:
        """All presets should produce valid BGRA frames after simulation."""
        for preset_fn in [sparkles, confetti, fire, smoke, rain]:
            ps = preset_fn(width=64, height=48)
            for _ in range(5):
                frame = ps.simulate_frame()
            assert frame.shape == (48, 64, 4)
            assert frame.dtype == np.uint8
