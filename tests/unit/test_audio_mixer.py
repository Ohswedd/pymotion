"""Tests for the audio mixing system — AudioMixer, AudioClipData."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.audio.mixer import AudioClipData, AudioMixer


class TestAudioMixer:
    """Tests for AudioMixer."""

    def test_init_defaults(self) -> None:
        mixer = AudioMixer()
        assert mixer.sample_rate == 48000
        assert mixer.bit_depth == 24
        assert mixer.channels == 2

    def test_render_empty(self) -> None:
        """Rendering with no clips returns empty array."""
        mixer = AudioMixer()
        result = mixer.render()
        assert len(result) == 0
        assert result.dtype == np.int32

    def test_add_single_clip(self) -> None:
        """Add a single clip and render."""
        mixer = AudioMixer()
        samples = np.ones(1000, dtype=np.float64) * 0.5
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip)
        result = mixer.render()
        assert len(result) == 1000 * 2  # stereo interleaved
        assert result.dtype == np.int32

    def test_add_stereo_clip(self) -> None:
        """Add a stereo clip and render."""
        mixer = AudioMixer()
        samples = np.ones((1000, 2), dtype=np.float64) * 0.5
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip)
        result = mixer.render()
        assert len(result) == 1000 * 2

    def test_add_multiple_clips_same_track(self) -> None:
        """Multiple clips on the same track should mix."""
        mixer = AudioMixer()
        s1 = np.ones(500, dtype=np.float64) * 0.3
        s2 = np.ones(500, dtype=np.float64) * 0.3
        mixer.add(AudioClipData(samples=s1, start_sample=0))
        mixer.add(AudioClipData(samples=s2, start_sample=0))
        result = mixer.render()
        # Should have additive mix (0.3 + 0.3 = 0.6)
        assert len(result) == 500 * 2

    def test_add_clips_different_tracks(self) -> None:
        """Clips on different tracks should mix independently."""
        mixer = AudioMixer()
        s1 = np.ones(500, dtype=np.float64) * 0.5
        s2 = np.ones(500, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=s1), track="music")
        mixer.add(AudioClipData(samples=s2), track="voice")
        result = mixer.render()
        assert len(result) == 500 * 2

    def test_set_volume(self) -> None:
        """Setting volume should scale the track output."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 1.0
        mixer.add(AudioClipData(samples=samples), track="music")
        mixer.set_volume("music", 0.5)
        result = mixer.render()
        # With volume 0.5, max val should be about half
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        expected = int(0.5 * max_val)
        # Check first sample (left channel)
        assert abs(result[0] - expected) < 2

    def test_set_volume_nonexistent_track(self) -> None:
        """Setting volume on nonexistent track should raise ValueError."""
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="Track.*not found"):
            mixer.set_volume("nonexistent", 0.5)

    def test_offset_clip(self) -> None:
        """Clip with start_sample > 0 should be offset in the mix."""
        mixer = AudioMixer()
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples, start_sample=50))
        result = mixer.render()
        # Total should be 150 samples * 2 channels
        assert len(result) == 150 * 2
        # First 50 samples should be zero
        assert result[0] == 0
        assert result[98] == 0

    def test_clipping_at_boundaries(self) -> None:
        """Samples at ±1.0 should be clamped correctly."""
        mixer = AudioMixer()
        # Deliberately exceed 1.0 by mixing two full-volume clips
        s1 = np.ones(100, dtype=np.float64)
        s2 = np.ones(100, dtype=np.float64)
        mixer.add(AudioClipData(samples=s1))
        mixer.add(AudioClipData(samples=s2))
        result = mixer.render()
        max_val = 2 ** (mixer.bit_depth - 1) - 1
        # Should be clamped to max_val
        assert np.max(result) <= max_val

    def test_mono_mixer(self) -> None:
        """Mono mixer should output correctly."""
        mixer = AudioMixer(channels=1)
        samples = np.ones(100, dtype=np.float64) * 0.5
        mixer.add(AudioClipData(samples=samples))
        result = mixer.render()
        assert len(result) == 100  # 1 channel


class TestAudioClipData:
    """Tests for AudioClipData."""

    def test_init_defaults(self) -> None:
        samples = np.zeros(100, dtype=np.float64)
        clip = AudioClipData(samples=samples)
        assert clip.start_sample == 0
        assert clip.sample_rate == 48000

    def test_init_with_offset(self) -> None:
        samples = np.zeros(100, dtype=np.float64)
        clip = AudioClipData(samples=samples, start_sample=1000)
        assert clip.start_sample == 1000
