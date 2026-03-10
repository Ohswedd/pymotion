"""Tests for audio visualization clips."""

from __future__ import annotations

import numpy as np

from pymotion.clip.audio_viz import (
    AudioReactiveEffect,
    SpectrogramClip,
    SpectrumClip,
    WaveformClip,
)
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.effects.visual import GaussianBlur


def _ctx(frame: int = 0, w: int = 320, h: int = 240, fps: int = 30) -> RenderContext:
    """Create a test render context."""
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=Resolution(w, h),
        time_range=TimeRange(0, 100),
        local_frame=frame,
        progress=frame / 100.0,
    )


def _sine_audio(freq: float = 440.0, duration: float = 1.0, sr: int = 48000) -> np.ndarray:
    """Generate a mono sine wave."""
    t = np.arange(int(duration * sr), dtype=np.float64) / sr
    return np.sin(2 * np.pi * freq * t) * 0.5


class TestWaveformClip:
    """Tests for WaveformClip."""

    def test_render_bars(self) -> None:
        """Render a bars-style waveform."""
        audio = _sine_audio()
        clip = WaveformClip(audio=audio, style="bars")
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)
        assert frame.dtype == np.uint8

    def test_render_line(self) -> None:
        """Render a line-style waveform."""
        audio = _sine_audio()
        clip = WaveformClip(audio=audio, style="line")
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_render_empty_audio(self) -> None:
        """Empty audio renders background only."""
        clip = WaveformClip()
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_render_stereo(self) -> None:
        """Stereo audio is averaged to mono for display."""
        mono = _sine_audio()
        stereo = np.column_stack([mono, mono])
        clip = WaveformClip(audio=stereo)
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_render_at_different_frames(self) -> None:
        """Renders at different time positions without error."""
        audio = _sine_audio(duration=2.0)
        clip = WaveformClip(audio=audio)
        f1 = clip.render_frame(_ctx(frame=0))
        f2 = clip.render_frame(_ctx(frame=30))
        assert f1.shape == f2.shape
        # Both frames should be valid BGRA
        assert f1.dtype == np.uint8
        assert f2.dtype == np.uint8


class TestSpectrumClip:
    """Tests for SpectrumClip."""

    def test_render_bars(self) -> None:
        """Render a bars-style spectrum."""
        audio = _sine_audio()
        clip = SpectrumClip(audio=audio, bands=16, style="bars")
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)
        assert frame.dtype == np.uint8

    def test_render_smooth(self) -> None:
        """Render a smooth-style spectrum."""
        audio = _sine_audio()
        clip = SpectrumClip(audio=audio, bands=32, style="smooth")
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_render_empty_audio(self) -> None:
        """Empty audio renders background only."""
        clip = SpectrumClip()
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_custom_color_map(self) -> None:
        """Custom color map is used."""
        from pymotion.utils.color import Color

        audio = _sine_audio()
        clip = SpectrumClip(
            audio=audio,
            color_map=[Color.parse("#FF0000"), Color.parse("#0000FF")],
        )
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_has_content_with_audio(self) -> None:
        """Frame should contain non-background pixels with audio."""
        audio = _sine_audio(440.0, duration=1.0)
        clip = SpectrumClip(audio=audio, bands=16)
        frame = clip.render_frame(_ctx(frame=5))
        # Check that not all pixels are pure background
        assert np.any(frame[:, :, :3] > 20)


class TestSpectrogramClip:
    """Tests for SpectrogramClip."""

    def test_render(self) -> None:
        """Render a spectrogram frame."""
        audio = _sine_audio(duration=2.0)
        clip = SpectrogramClip(audio=audio)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (240, 320, 4)
        assert frame.dtype == np.uint8

    def test_render_empty_audio(self) -> None:
        """Empty audio renders colored background."""
        clip = SpectrogramClip()
        frame = clip.render_frame(_ctx())
        assert frame.shape == (240, 320, 4)

    def test_has_frequency_content(self) -> None:
        """Frame should show frequency content for a sine wave."""
        audio = _sine_audio(1000.0, duration=2.0)
        clip = SpectrogramClip(audio=audio, fft_size=1024)
        frame = clip.render_frame(_ctx(frame=15))
        # Should have variation (not uniform color)
        assert np.std(frame[:, :, 2].astype(float)) > 1.0


class TestAudioReactiveEffect:
    """Tests for AudioReactiveEffect."""

    def test_get_value_full_band(self) -> None:
        """get_value returns a value in [min, max] range."""
        audio = _sine_audio()
        effect = GaussianBlur(radius=5.0)
        reactive = AudioReactiveEffect(
            effect=effect,
            audio=audio,
            property_name="radius",
            band="full",
            sensitivity=1.0,
            min_value=0.0,
            max_value=10.0,
        )
        val = reactive.get_value(frame=5, fps=30)
        assert 0.0 <= val <= 10.0

    def test_get_value_low_band(self) -> None:
        """Low band reacts to bass frequencies."""
        # Low frequency sine
        audio_low = _sine_audio(100.0)
        effect = GaussianBlur(radius=5.0)
        reactive = AudioReactiveEffect(effect=effect, audio=audio_low, band="low", sensitivity=2.0)
        val = reactive.get_value(frame=5, fps=30)
        assert 0.0 <= val <= 1.0

    def test_get_value_high_band(self) -> None:
        """High band reacts to high frequencies."""
        audio_high = _sine_audio(8000.0)
        effect = GaussianBlur(radius=5.0)
        reactive = AudioReactiveEffect(
            effect=effect, audio=audio_high, band="high", sensitivity=2.0
        )
        val = reactive.get_value(frame=5, fps=30)
        assert 0.0 <= val <= 1.0

    def test_get_value_empty_audio(self) -> None:
        """Empty audio returns min_value."""
        effect = GaussianBlur(radius=5.0)
        reactive = AudioReactiveEffect(effect=effect, min_value=0.5)
        val = reactive.get_value(frame=0, fps=30)
        assert val == 0.5

    def test_sensitivity_affects_output(self) -> None:
        """Higher sensitivity produces higher values."""
        audio = _sine_audio()
        effect = GaussianBlur(radius=5.0)
        low_sens = AudioReactiveEffect(effect=effect, audio=audio, sensitivity=0.1)
        high_sens = AudioReactiveEffect(effect=effect, audio=audio, sensitivity=10.0)
        val_low = low_sens.get_value(frame=5, fps=30)
        val_high = high_sens.get_value(frame=5, fps=30)
        assert val_high >= val_low

    def test_apply_to_frame(self) -> None:
        """apply_to_frame processes a frame through the effect."""
        audio = _sine_audio()
        effect = GaussianBlur(radius=5.0)
        reactive = AudioReactiveEffect(
            effect=effect,
            audio=audio,
            property_name="radius",
            min_value=0.0,
            max_value=20.0,
        )
        frame = np.random.default_rng(42).integers(0, 255, (240, 320, 4), dtype=np.uint8)
        result = reactive.apply_to_frame(frame, frame=5, fps=30)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_stereo_audio_handled(self) -> None:
        """Stereo audio is averaged to mono."""
        mono = _sine_audio()
        stereo = np.column_stack([mono, mono])
        effect = GaussianBlur(radius=5.0)
        reactive = AudioReactiveEffect(effect=effect, audio=stereo)
        val = reactive.get_value(frame=5, fps=30)
        assert 0.0 <= val <= 1.0
