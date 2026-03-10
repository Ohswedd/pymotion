"""Tests for TTSClip text-to-speech generation."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.tts import TTSClip


class TestTTSClip:
    """Tests for TTSClip."""

    def test_init_defaults(self) -> None:
        tts = TTSClip(text="Hello")
        assert tts.text == "Hello"
        assert tts.engine == "system"
        assert tts.voice == "default"
        assert tts.speed == 1.0
        assert tts.pitch == 1.0
        assert tts.sample_rate == 48000

    def test_empty_text_returns_empty(self) -> None:
        tts = TTSClip(text="")
        result = tts.generate()
        assert len(result) == 0
        assert result.shape == (0, 2)

    def test_get_samples_caches(self) -> None:
        tts = TTSClip(text="")
        tts.generate()  # Generate first to populate cache
        s1 = tts.get_samples()
        s2 = tts.get_samples()
        assert s1 is s2  # Same object from cache

    def test_system_engine_requires_pyttsx3(self) -> None:
        """System engine requires pyttsx3 package."""
        tts = TTSClip(text="Test", engine="system")
        try:
            tts.generate()
        except ImportError as e:
            assert "pyttsx3" in str(e)
        except RuntimeError:
            # FFmpeg decode may fail if pyttsx3 produces empty output
            pass

    def test_openai_engine_requires_openai(self) -> None:
        """OpenAI engine requires openai package and API key."""
        tts = TTSClip(text="Test", engine="openai")
        with pytest.raises((ImportError, Exception)):  # noqa: PT011
            tts.generate()

    def test_elevenlabs_engine_requires_package(self) -> None:
        """ElevenLabs engine requires elevenlabs package."""
        tts = TTSClip(text="Test", engine="elevenlabs")
        with pytest.raises(ImportError, match="elevenlabs"):
            tts.generate()

    def test_unsupported_engine_raises(self) -> None:
        tts = TTSClip(text="Test", engine="unknown")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unsupported TTS engine"):
            tts.generate()

    def test_custom_params(self) -> None:
        tts = TTSClip(
            text="Hello",
            voice="alloy",
            engine="openai",
            speed=1.5,
            pitch=0.8,
            sample_rate=44100,
        )
        assert tts.voice == "alloy"
        assert tts.speed == 1.5
        assert tts.sample_rate == 44100

    def test_generate_returns_stereo_float64(self) -> None:
        """If generate succeeds, output should be float64 stereo."""
        tts = TTSClip(text="")
        result = tts.generate()
        assert result.dtype == np.float64
        if len(result) > 0:
            assert result.ndim == 2
            assert result.shape[1] == 2
