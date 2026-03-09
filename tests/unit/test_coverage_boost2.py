"""Coverage-boost tests for audio, video, visual effects, pipeline, composition, and easing."""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from pymotion.animation.easing import (
    cubic_bezier,
    ease_in_back,
    ease_in_bounce,
    ease_in_circ,
    ease_in_elastic,
    ease_in_expo,
    ease_in_out_back,
    ease_in_out_bounce,
    ease_in_out_circ,
    ease_in_out_elastic,
    ease_in_out_expo,
    ease_in_out_sine,
    ease_in_quart,
    ease_in_quint,
    ease_out_back,
    ease_out_bounce,
    ease_out_circ,
    ease_out_elastic,
    ease_out_expo,
    ease_out_quart,
    ease_out_quint,
    ease_out_sine,
    get_easing,
    linear,
    steps,
)
from pymotion.clip.base import BlendMode, RenderContext, Resolution, TimeRange
from pymotion.composition import Composition, Track
from pymotion.effects.visual import GaussianBlur, Vignette
from pymotion.render.pipeline import RenderPipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav(
    path: Path, *, sample_rate: int = 48000, duration_sec: float = 0.1, channels: int = 2
) -> Path:
    """Create a small WAV file with a sine tone."""
    n_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, n_samples, dtype=np.float64)
    tone = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float64)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        int_data = (tone * 32767).astype(np.int16)
        if channels == 2:
            stereo = np.column_stack([int_data, int_data])
            wf.writeframes(stereo.tobytes())
        else:
            wf.writeframes(int_data.tobytes())
    return path


def _make_ctx(
    *,
    frame: int = 0,
    fps: int = 30,
    width: int = 64,
    height: int = 64,
    local_frame: int = 0,
    progress: float = 0.0,
) -> RenderContext:
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=Resolution(width=width, height=height),
        time_range=TimeRange(start=0, end=90),
        local_frame=local_frame,
        progress=progress,
    )


def _make_bgra_frame(h: int = 64, w: int = 64) -> np.ndarray:
    frame = np.random.default_rng(42).integers(0, 256, (h, w, 4), dtype=np.uint8)
    return frame


# ===========================================================================
# AudioClip tests
# ===========================================================================


class TestAudioClip:
    """Tests for pymotion.clip.audio.AudioClip."""

    def test_init_with_valid_file(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        assert clip.source == wav.resolve()
        assert clip.volume == 1.0
        assert clip.pan == 0.0

    def test_init_file_not_found(self) -> None:
        from pymotion.clip.audio import AudioClip

        with pytest.raises(FileNotFoundError):
            AudioClip("/nonexistent/audio.wav")

    def test_trim_sets_fields(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        result = clip.trim(0.5, 1.5)
        assert result is clip  # fluent
        assert clip._trim_start_sec == 0.5
        assert clip._trim_end_sec == 1.5

    def test_trim_invalidates_cache(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        clip._samples = np.zeros((10, 2))
        clip.trim(0.1)
        assert clip._samples is None

    def test_fade_in(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        result = clip.fade_in(0.5, "ease_in_quad")
        assert result is clip
        assert clip._fade_in_sec == 0.5
        assert clip._fade_in_curve == "ease_in_quad"

    def test_fade_out(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        result = clip.fade_out(0.3, "linear")
        assert result is clip
        assert clip._fade_out_sec == 0.3

    def test_loop(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        result = clip.loop(3)
        assert result is clip
        assert clip._loop_count == 3

    def test_loop_infinite(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        clip.loop(-1)
        assert clip._loop_count == -1

    def test_at(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        result = clip.at(10)
        assert result is clip
        assert clip.start_frame == 10

    def test_at_seconds(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        result = clip.at_seconds(2.0, fps=30)
        assert result is clip
        assert clip.start_frame == 60

    def test_sample_rate_property(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav, sample_rate=44100)
        assert clip.sample_rate == 44100

    def test_get_samples_decodes(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav", duration_sec=0.05)
        clip = AudioClip(wav)
        samples = clip.get_samples()
        assert isinstance(samples, np.ndarray)
        # Second call returns cached
        assert clip.get_samples() is samples

    def test_apply_effects_empty(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        empty = np.zeros((0, 2), dtype=np.float64)
        result = clip._apply_effects(empty)
        assert len(result) == 0

    def test_apply_effects_volume(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav, volume=0.5)
        samples = np.ones((100, 2), dtype=np.float64)
        result = clip._apply_effects(samples)
        np.testing.assert_allclose(result, 0.5)

    def test_apply_effects_fade_in(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        clip._fade_in_sec = 0.01  # short fade
        samples = np.ones((4800, 2), dtype=np.float64)
        result = clip._apply_effects(samples)
        # First sample should be near zero (faded in)
        assert result[0, 0] < 0.01

    def test_apply_effects_fade_out(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        clip._fade_out_sec = 0.01
        samples = np.ones((4800, 2), dtype=np.float64)
        result = clip._apply_effects(samples)
        # Last sample should be near zero
        assert result[-1, 0] < 0.01

    def test_apply_effects_pan_left(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav, pan=-1.0)
        samples = np.ones((100, 2), dtype=np.float64)
        result = clip._apply_effects(samples)
        # Full left pan: right channel should be near zero
        assert result[50, 1] < 0.01

    def test_apply_effects_loop_count(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav)
        clip._loop_count = 3
        samples = np.ones((100, 2), dtype=np.float64)
        result = clip._apply_effects(samples)
        assert result.shape[0] == 300

    def test_get_ffmpeg_missing(self) -> None:
        from pymotion.clip import audio

        original = audio._FFMPEG_BIN
        try:
            audio._FFMPEG_BIN = None
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                audio._get_ffmpeg()
        finally:
            audio._FFMPEG_BIN = original

    def test_init_with_custom_volume_and_pan(self, tmp_path: Path) -> None:
        from pymotion.clip.audio import AudioClip

        wav = _make_wav(tmp_path / "tone.wav")
        clip = AudioClip(wav, volume=0.7, pan=0.5)
        assert clip.volume == 0.7
        assert clip.pan == 0.5


# ===========================================================================
# VideoClip tests
# ===========================================================================


class TestVideoClip:
    """Tests for pymotion.clip.video.VideoClip — parameter methods only."""

    def test_init_file_not_found(self) -> None:
        from pymotion.clip.video import VideoClip

        with pytest.raises(FileNotFoundError):
            VideoClip("/nonexistent/video.mp4")

    def test_get_ffmpeg_missing(self) -> None:
        from pymotion.clip import video

        original = video._FFMPEG_BIN
        try:
            video._FFMPEG_BIN = None
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                video._get_ffmpeg()
        finally:
            video._FFMPEG_BIN = original

    def test_get_ffprobe_missing(self) -> None:
        from pymotion.clip import video

        original = video._FFPROBE_BIN
        try:
            video._FFPROBE_BIN = None
            with pytest.raises(RuntimeError, match="ffprobe not found"):
                video._get_ffprobe()
        finally:
            video._FFPROBE_BIN = original

    def test_set_trim(self, tmp_path: Path) -> None:
        """Test set_trim via a mocked VideoClip (bypass __init__ file check)."""
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip.source = Path("dummy.mp4")
        clip.trim_start = 0.0
        clip.trim_end = None
        clip.speed = 1.0
        clip._reverse = False
        clip.loop = 1
        clip._frame_cache = {0: np.zeros((1,))}
        clip._source_fps = 30.0
        clip._source_duration = 10.0

        result = clip.set_trim(1.0, 5.0)
        assert result is clip
        assert clip.trim_start == 1.0
        assert clip.trim_end == 5.0
        assert clip._frame_cache == {}

    def test_set_speed_valid(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip._frame_cache = {}
        clip.speed = 1.0
        result = clip.set_speed(2.0)
        assert result is clip
        assert clip.speed == 2.0

    def test_set_speed_invalid(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip._frame_cache = {}
        clip.speed = 1.0
        with pytest.raises(ValueError, match="Speed must be positive"):
            clip.set_speed(0)
        with pytest.raises(ValueError, match="Speed must be positive"):
            clip.set_speed(-1.0)

    def test_set_reverse(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip._frame_cache = {}
        clip._reverse = False
        result = clip.set_reverse(True)
        assert result is clip
        assert clip._reverse is True

    def test_set_loop(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip._frame_cache = {}
        clip.loop = 1
        result = clip.set_loop(5)
        assert result is clip
        assert clip.loop == 5

    def test_source_fps_property(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip._source_fps = 24.0
        assert clip.source_fps == 24.0

    def test_source_duration_property(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip._source_duration = 5.5
        assert clip.source_duration == 5.5

    def test_calc_source_time_basic(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip.trim_start = 0.0
        clip.trim_end = 10.0
        clip.speed = 1.0
        clip._reverse = False
        clip.loop = 1
        clip._source_duration = 10.0

        ctx = _make_ctx(local_frame=30, fps=30)
        t = clip._calc_source_time(ctx)
        assert pytest.approx(t, abs=0.01) == 1.0

    def test_calc_source_time_reverse(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip.trim_start = 0.0
        clip.trim_end = 10.0
        clip.speed = 1.0
        clip._reverse = True
        clip.loop = 1
        clip._source_duration = 10.0

        ctx = _make_ctx(local_frame=0, fps=30)
        t = clip._calc_source_time(ctx)
        assert t == 10.0  # reversed: frame 0 maps to end

    def test_calc_source_time_loop(self) -> None:
        from pymotion.clip.video import VideoClip

        clip = VideoClip.__new__(VideoClip)
        clip.trim_start = 0.0
        clip.trim_end = 2.0
        clip.speed = 1.0
        clip._reverse = False
        clip.loop = -1
        clip._source_duration = 2.0

        # frame 90 at 30fps = 3.0s, looped over 2s duration -> 1.0s
        ctx = _make_ctx(local_frame=90, fps=30)
        t = clip._calc_source_time(ctx)
        assert pytest.approx(t, abs=0.01) == 1.0


# ===========================================================================
# Visual effects tests
# ===========================================================================


class TestGaussianBlur:
    def test_apply_positive_radius(self) -> None:
        frame = _make_bgra_frame()
        ctx = _make_ctx()
        blur = GaussianBlur(radius=3.0)
        result = blur.apply(frame, ctx)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_apply_zero_radius_returns_copy(self) -> None:
        frame = _make_bgra_frame()
        ctx = _make_ctx()
        blur = GaussianBlur(radius=0.0)
        result = blur.apply(frame, ctx)
        np.testing.assert_array_equal(result, frame)
        assert result is not frame

    def test_apply_negative_radius_returns_copy(self) -> None:
        frame = _make_bgra_frame()
        ctx = _make_ctx()
        blur = GaussianBlur(radius=-1.0)
        result = blur.apply(frame, ctx)
        np.testing.assert_array_equal(result, frame)

    def test_preserves_alpha(self) -> None:
        frame = _make_bgra_frame()
        ctx = _make_ctx()
        blur = GaussianBlur(radius=5.0)
        result = blur.apply(frame, ctx)
        # Alpha is not blurred — the code only blurs channels 0-2
        # so alpha should remain the same
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])


class TestVignette:
    def test_apply_default(self) -> None:
        frame = _make_bgra_frame()
        ctx = _make_ctx()
        vig = Vignette()
        result = vig.apply(frame, ctx)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_corners_darker(self) -> None:
        frame = np.full((64, 64, 4), 200, dtype=np.uint8)
        ctx = _make_ctx()
        vig = Vignette(strength=1.0, radius=0.3, feather=0.3)
        result = vig.apply(frame, ctx)
        # Corners should be darker than center
        corner_brightness = int(result[0, 0, 0])
        center_brightness = int(result[32, 32, 0])
        assert corner_brightness < center_brightness

    def test_strength_zero_no_change(self) -> None:
        frame = np.full((64, 64, 4), 128, dtype=np.uint8)
        ctx = _make_ctx()
        vig = Vignette(strength=0.0)
        result = vig.apply(frame, ctx)
        np.testing.assert_array_equal(result, frame)

    def test_preserves_alpha(self) -> None:
        frame = _make_bgra_frame()
        ctx = _make_ctx()
        vig = Vignette(strength=0.8)
        result = vig.apply(frame, ctx)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])


# ===========================================================================
# RenderPipeline tests
# ===========================================================================


class TestRenderPipeline:
    def test_init_creates_backends(self) -> None:
        pipeline = RenderPipeline()
        assert len(pipeline.backends) == 1

    def test_backend_is_cairo(self) -> None:
        from pymotion.render.backend_2d import CairoRenderer

        pipeline = RenderPipeline()
        assert isinstance(pipeline.backends[0], CairoRenderer)


# ===========================================================================
# Composition & Track tests
# ===========================================================================


class TestTrack:
    def test_default_values(self) -> None:
        track = Track()
        assert track.name == "default"
        assert track.clips == []
        assert track.visible is True
        assert track.opacity == 1.0
        assert track.blend_mode == BlendMode.NORMAL

    def test_add_clips(self) -> None:
        track = Track(name="fg")
        mock_clip = MagicMock()
        result = track.add(mock_clip)
        assert result is track
        assert len(track.clips) == 1

    def test_add_multiple_clips(self) -> None:
        track = Track()
        c1, c2 = MagicMock(), MagicMock()
        track.add(c1, c2)
        assert len(track.clips) == 2


class TestComposition:
    def test_default_init(self) -> None:
        comp = Composition()
        assert comp.resolution.width == 1920
        assert comp.resolution.height == 1080
        assert comp.fps == 30
        assert comp.duration == 90
        assert len(comp.tracks) == 1  # default track

    def test_custom_init(self) -> None:
        comp = Composition(width=1280, height=720, fps=60, duration=120, background="#ff0000")
        assert comp.resolution.width == 1280
        assert comp.fps == 60

    def test_add_clip_to_default_track(self) -> None:
        comp = Composition()
        mock_clip = MagicMock()
        result = comp.add(mock_clip)
        assert result is comp
        assert len(comp._default_track.clips) == 1

    def test_add_track(self) -> None:
        comp = Composition()
        track = Track(name="overlay")
        result = comp.add_track(track)
        assert result is comp
        assert len(comp.tracks) == 2

    def test_render_frame_empty(self) -> None:
        comp = Composition(width=64, height=64, duration=10)
        frame = comp._render_frame(0)
        assert frame.shape == (64, 64, 4)
        assert frame.dtype == np.uint8

    def test_render_frame_invisible_track(self) -> None:
        comp = Composition(width=64, height=64, duration=10)
        track = Track(name="hidden", visible=False)
        mock_clip = MagicMock()
        mock_clip.start = 0
        mock_clip.end = 10
        track.add(mock_clip)
        comp.add_track(track)
        # Should not call render_frame on the invisible track's clip
        comp._render_frame(0)
        mock_clip.render_frame.assert_not_called()

    def test_frame_iterator(self) -> None:
        comp = Composition(width=64, height=64, duration=5)
        frames = list(comp._frame_iterator(0, 3))
        assert len(frames) == 3
        assert all(f.shape == (64, 64, 4) for f in frames)

    def test_frame_iterator_default_end(self) -> None:
        comp = Composition(width=64, height=64, duration=3)
        frames = list(comp._frame_iterator())
        assert len(frames) == 3


# ===========================================================================
# Easing tests
# ===========================================================================


class TestEasing:
    """Test easing functions that are likely uncovered at 72%."""

    def test_linear_boundaries(self) -> None:
        assert linear(0.0) == 0.0
        assert linear(1.0) == 1.0
        assert linear(0.5) == 0.5

    # --- Quart/Quint ---
    def test_ease_in_quart(self) -> None:
        assert ease_in_quart(0.0) == 0.0
        assert ease_in_quart(1.0) == 1.0
        assert 0.0 < ease_in_quart(0.5) < 0.5

    def test_ease_out_quart(self) -> None:
        assert ease_out_quart(0.0) == 0.0
        assert ease_out_quart(1.0) == 1.0
        assert ease_out_quart(0.5) > 0.5

    def test_ease_in_quint(self) -> None:
        assert ease_in_quint(0.0) == 0.0
        assert ease_in_quint(1.0) == 1.0

    def test_ease_out_quint(self) -> None:
        assert ease_out_quint(0.0) == 0.0
        assert ease_out_quint(1.0) == 1.0

    # --- Sine ---
    def test_ease_out_sine(self) -> None:
        assert ease_out_sine(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_out_sine(1.0) == pytest.approx(1.0, abs=1e-9)

    def test_ease_in_out_sine(self) -> None:
        assert ease_in_out_sine(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_out_sine(1.0) == pytest.approx(1.0, abs=1e-9)
        assert ease_in_out_sine(0.5) == pytest.approx(0.5, abs=1e-9)

    # --- Expo ---
    def test_ease_in_expo(self) -> None:
        assert ease_in_expo(0.0) == 0.0
        assert ease_in_expo(1.0) == pytest.approx(1.0, abs=0.01)

    def test_ease_out_expo(self) -> None:
        assert ease_out_expo(0.0) == pytest.approx(0.0, abs=0.01)
        assert ease_out_expo(1.0) == 1.0

    def test_ease_in_out_expo(self) -> None:
        assert ease_in_out_expo(0.0) == 0.0
        assert ease_in_out_expo(1.0) == 1.0
        assert ease_in_out_expo(0.25) < 0.5
        assert ease_in_out_expo(0.75) > 0.5

    # --- Circ ---
    def test_ease_in_circ(self) -> None:
        assert ease_in_circ(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_circ(1.0) == pytest.approx(1.0, abs=1e-9)

    def test_ease_out_circ(self) -> None:
        assert ease_out_circ(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_out_circ(1.0) == pytest.approx(1.0, abs=1e-9)

    def test_ease_in_out_circ(self) -> None:
        assert ease_in_out_circ(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_out_circ(1.0) == pytest.approx(1.0, abs=1e-9)
        assert ease_in_out_circ(0.5) == pytest.approx(0.5, abs=1e-9)

    # --- Back ---
    def test_ease_in_back(self) -> None:
        assert ease_in_back(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_back(1.0) == pytest.approx(1.0, abs=1e-9)
        # Overshoots below 0 at start
        assert ease_in_back(0.3) < 0.0

    def test_ease_out_back(self) -> None:
        assert ease_out_back(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_out_back(1.0) == pytest.approx(1.0, abs=1e-9)
        # Overshoots above 1 near end
        assert ease_out_back(0.7) > 1.0

    def test_ease_in_out_back(self) -> None:
        assert ease_in_out_back(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_out_back(1.0) == pytest.approx(1.0, abs=1e-9)
        # Test both halves
        v1 = ease_in_out_back(0.25)
        v2 = ease_in_out_back(0.75)
        assert v1 < 0.5
        assert v2 > 0.5

    # --- Elastic ---
    def test_ease_in_elastic(self) -> None:
        assert ease_in_elastic(0.0) == 0.0
        assert ease_in_elastic(1.0) == 1.0
        # Mid-value oscillates
        v = ease_in_elastic(0.5)
        assert isinstance(v, float)

    def test_ease_out_elastic(self) -> None:
        assert ease_out_elastic(0.0) == 0.0
        assert ease_out_elastic(1.0) == 1.0

    def test_ease_in_out_elastic(self) -> None:
        assert ease_in_out_elastic(0.0) == 0.0
        assert ease_in_out_elastic(1.0) == 1.0
        # Test both halves
        v1 = ease_in_out_elastic(0.25)
        v2 = ease_in_out_elastic(0.75)
        assert isinstance(v1, float)
        assert isinstance(v2, float)

    # --- Bounce ---
    def test_ease_in_bounce(self) -> None:
        assert ease_in_bounce(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_bounce(1.0) == pytest.approx(1.0, abs=1e-9)

    def test_ease_out_bounce_all_branches(self) -> None:
        # Branch 1: t < 1/2.75
        v = ease_out_bounce(0.1)
        assert 0.0 <= v <= 1.0
        # Branch 2: t < 2/2.75
        v = ease_out_bounce(0.5)
        assert 0.0 <= v <= 1.0
        # Branch 3: t < 2.5/2.75
        v = ease_out_bounce(0.92)
        assert 0.0 <= v <= 1.0
        # Branch 4: else
        v = ease_out_bounce(0.99)
        assert 0.0 <= v <= 1.0

    def test_ease_in_out_bounce(self) -> None:
        assert ease_in_out_bounce(0.0) == pytest.approx(0.0, abs=1e-9)
        assert ease_in_out_bounce(1.0) == pytest.approx(1.0, abs=1e-9)
        v1 = ease_in_out_bounce(0.25)
        v2 = ease_in_out_bounce(0.75)
        assert isinstance(v1, float)
        assert isinstance(v2, float)

    # --- cubic_bezier ---
    def test_cubic_bezier_linear(self) -> None:
        ease_fn = cubic_bezier(0.0, 0.0, 1.0, 1.0)
        assert ease_fn(0.0) == 0.0
        assert ease_fn(1.0) == 1.0
        assert ease_fn(0.5) == pytest.approx(0.5, abs=0.05)

    def test_cubic_bezier_ease(self) -> None:
        ease_fn = cubic_bezier(0.25, 0.1, 0.25, 1.0)
        assert ease_fn(0.0) == 0.0
        assert ease_fn(1.0) == 1.0
        v = ease_fn(0.5)
        assert 0.0 < v < 1.0

    def test_cubic_bezier_boundaries(self) -> None:
        ease_fn = cubic_bezier(0.42, 0.0, 0.58, 1.0)
        assert ease_fn(-0.1) == 0.0
        assert ease_fn(1.5) == 1.0

    # --- steps ---
    def test_steps_end(self) -> None:
        fn = steps(4, "end")
        assert fn(0.0) == 0.0
        assert fn(0.24) == 0.0
        assert fn(0.25) == 0.25
        assert fn(0.99) == 0.75

    def test_steps_start(self) -> None:
        fn = steps(4, "start")
        assert fn(0.0) == 0.0
        # Just above 0 should jump to 0.25
        assert fn(0.01) == 0.25
        assert fn(1.0) == 1.0

    def test_steps_invalid_n(self) -> None:
        with pytest.raises(ValueError, match="n >= 1"):
            steps(0)

    def test_steps_invalid_direction(self) -> None:
        with pytest.raises(ValueError, match="direction"):
            steps(4, "middle")

    # --- get_easing ---
    def test_get_easing_valid(self) -> None:
        fn = get_easing("linear")
        assert fn is linear

    def test_get_easing_invalid(self) -> None:
        with pytest.raises(ValueError, match="Unknown easing"):
            get_easing("nonexistent_easing")
