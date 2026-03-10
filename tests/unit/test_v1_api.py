"""Tests for v1.0 API additions — Silence, animate, Align, audio effects."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.animation.keyframe import KeyframeTrack, animate
from pymotion.audio.effects import (
    Delay,
    HighPassFilter,
    LowPassFilter,
    NoiseReduction,
    PitchShift,
    Reverb,
)
from pymotion.clip.audio import Silence
from pymotion.clip.base import Align


class TestSilence:
    """Tests for the Silence helper."""

    def test_default_silence(self) -> None:
        s = Silence()
        samples = s.get_samples()
        assert samples.shape == (48000, 2)
        assert np.all(samples == 0.0)

    def test_custom_duration(self) -> None:
        s = Silence(duration_sec=0.5, sample_rate=44100, channels=1)
        samples = s.get_samples()
        assert samples.shape == (22050, 1)
        assert samples.dtype == np.float64

    def test_zero_duration(self) -> None:
        s = Silence(duration_sec=0.0)
        samples = s.get_samples()
        assert len(samples) == 0


class TestAnimate:
    """Tests for the animate() shorthand."""

    def test_basic_float(self) -> None:
        track = animate(0.0, 1.0, duration=30)
        assert isinstance(track, KeyframeTrack)
        assert len(track.keyframes) == 2
        assert track.keyframes[0].frame == 0
        assert track.keyframes[1].frame == 30

    def test_with_delay(self) -> None:
        track = animate(0.0, 100.0, duration=60, delay=10)
        assert track.keyframes[0].frame == 10
        assert track.keyframes[1].frame == 70

    def test_easing(self) -> None:
        track = animate(0.0, 1.0, duration=10, easing="ease_in_quad")
        assert track.keyframes[0].easing == "ease_in_quad"

    def test_interpolation(self) -> None:
        track = animate(0.0, 100.0, duration=100)
        assert track.value_at(50) == pytest.approx(50.0)
        assert track.value_at(0) == pytest.approx(0.0)
        assert track.value_at(100) == pytest.approx(100.0)

    def test_invalid_duration(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            animate(0.0, 1.0, duration=0)

    def test_negative_duration(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            animate(0.0, 1.0, duration=-5)


class TestAlign:
    """Tests for the Align enum."""

    def test_values_exist(self) -> None:
        assert Align.LEFT.value == "left"
        assert Align.CENTER.value == "center"
        assert Align.RIGHT.value == "right"
        assert Align.TOP.value == "top"
        assert Align.BOTTOM.value == "bottom"

    def test_compound_values(self) -> None:
        assert Align.TOP_LEFT.value == "top_left"
        assert Align.BOTTOM_RIGHT.value == "bottom_right"
        assert Align.CENTER_LEFT.value == "center_left"

    def test_all_members(self) -> None:
        assert len(Align) == 13


class TestReverb:
    """Tests for the Reverb effect."""

    def test_defaults(self) -> None:
        r = Reverb()
        assert r.room_size == 0.5
        assert r.damping == 0.5

    def test_custom_params(self) -> None:
        r = Reverb(room_size=0.8, wet_level=0.5)
        assert r.room_size == 0.8
        assert r.wet_level == 0.5


class TestDelay:
    """Tests for the Delay effect."""

    def test_defaults(self) -> None:
        d = Delay()
        assert d.delay_seconds == 0.25
        assert d.feedback == 0.3
        assert d.mix == 0.5

    def test_custom_params(self) -> None:
        d = Delay(delay_seconds=0.5, feedback=0.5, mix=0.7)
        assert d.delay_seconds == 0.5


class TestPitchShift:
    """Tests for the PitchShift effect."""

    def test_defaults(self) -> None:
        ps = PitchShift()
        assert ps.semitones == 0.0

    def test_custom(self) -> None:
        ps = PitchShift(semitones=5.0)
        assert ps.semitones == 5.0


class TestNoiseReduction:
    """Tests for the NoiseReduction effect."""

    def test_defaults(self) -> None:
        nr = NoiseReduction()
        assert nr.threshold_db == -40.0
        assert nr.ratio == 10.0


class TestLowPassFilter:
    """Tests for the LowPassFilter effect."""

    def test_defaults(self) -> None:
        lpf = LowPassFilter()
        assert lpf.cutoff_hz == 5000.0

    def test_custom(self) -> None:
        lpf = LowPassFilter(cutoff_hz=1000.0)
        assert lpf.cutoff_hz == 1000.0


class TestHighPassFilter:
    """Tests for the HighPassFilter effect."""

    def test_defaults(self) -> None:
        hpf = HighPassFilter()
        assert hpf.cutoff_hz == 200.0

    def test_custom(self) -> None:
        hpf = HighPassFilter(cutoff_hz=500.0)
        assert hpf.cutoff_hz == 500.0


class TestPublicAPIImports:
    """Tests that all PRD §8.2 symbols are importable from pymotion."""

    def test_composition(self) -> None:
        from pymotion import Composition, Track  # noqa: F401

    def test_clips(self) -> None:
        from pymotion import (  # noqa: F401
            AudioClip,
            ColorClip,
            GradientClip,
            ImageClip,
            Scene3DClip,
            ShapeClip,
            TextClip,
            VideoClip,
        )

    def test_helpers(self) -> None:
        from pymotion import Keyframe, Silence, animate  # noqa: F401

    def test_3d(self) -> None:
        from pymotion import (  # noqa: F401
            AmbientLight,
            Camera,
            DirectionalLight,
            HDRIEnvironment,
            PBRMaterial,
            PointLight,
            Scene3D,
            SpotLight,
        )

    def test_animation(self) -> None:
        from pymotion import cubic_bezier, spring, steps  # noqa: F401

    def test_visual_effects(self) -> None:
        from pymotion import (  # noqa: F401
            Bloom,
            Brightness,
            ChromaticAberration,
            Contrast,
            Curves,
            Fisheye,
            GaussianBlur,
            Glow,
            HueSaturationLuminance,
            LUTEffect,
            Saturation,
            Vignette,
            WaveWarp,
        )

    def test_audio_effects(self) -> None:
        from pymotion import (  # noqa: F401
            EQ,
            Compressor,
            Delay,
            HighPassFilter,
            Limiter,
            LowPassFilter,
            NoiseReduction,
            PitchShift,
            Reverb,
        )

    def test_transitions(self) -> None:
        from pymotion import (  # noqa: F401
            CrossDissolve,
            Fade,
            FadeToBlack,
            FilmBurn,
            Glitch,
            PageTurn,
            Shatter,
            SlideLeft,
            SlideRight,
            ZoomIn,
            ZoomOut,
        )

    def test_particles(self) -> None:
        from pymotion import (  # noqa: F401
            Confetti,
            Emitter,
            Fire,
            ParticleSystem,
            Rain,
            Smoke,
            Sparkles,
            Stars,
        )

    def test_text(self) -> None:
        from pymotion import (  # noqa: F401
            CountUp,
            KineticText,
            ScrambleText,
            Typewriter,
            WordByWord,
        )

    def test_enums(self) -> None:
        from pymotion import Align, BlendMode  # noqa: F401

    def test_template(self) -> None:
        from pymotion import Template  # noqa: F401

    def test_types(self) -> None:
        from pymotion import Color, Resolution, Vec2, Vec3  # noqa: F401

    def test_version(self) -> None:
        import pymotion

        assert pymotion.__version__ == "1.2.0"
