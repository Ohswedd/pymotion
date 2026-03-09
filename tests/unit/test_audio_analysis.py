"""Unit tests for audio/analysis.py — BeatDetector, OnsetDetector, WaveformExtractor."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.audio.analysis import BeatDetector, OnsetDetector, WaveformExtractor


class TestBeatDetector:
    def test_detect_returns_list_of_ints(self) -> None:
        """BeatDetector.detect should return a list of integer frame numbers."""
        # Generate a simple click track — impulses at regular intervals
        sr = 22050
        duration = 4.0  # seconds
        n_samples = int(sr * duration)
        audio = np.zeros(n_samples, dtype=np.float32)
        # Place impulses every 0.5 seconds (120 BPM)
        for i in range(int(duration / 0.5)):
            idx = int(i * 0.5 * sr)
            if idx < n_samples:
                audio[idx : idx + 100] = 0.8

        detector = BeatDetector()
        beats = detector.detect(audio, sample_rate=sr, fps=30)
        assert isinstance(beats, list)
        assert all(isinstance(b, int) for b in beats)

    def test_detect_stereo_input(self) -> None:
        """BeatDetector should handle stereo audio by converting to mono."""
        sr = 22050
        n_samples = sr * 2
        stereo = np.random.default_rng(42).random((n_samples, 2)).astype(np.float32)
        detector = BeatDetector()
        beats = detector.detect(stereo, sample_rate=sr, fps=30)
        assert isinstance(beats, list)

    def test_detect_silent_audio(self) -> None:
        """Silent audio should return empty or minimal beats."""
        sr = 22050
        audio = np.zeros(sr * 2, dtype=np.float32)
        detector = BeatDetector()
        beats = detector.detect(audio, sample_rate=sr, fps=30)
        assert isinstance(beats, list)


class TestOnsetDetector:
    def test_detect_returns_list_of_ints(self) -> None:
        sr = 22050
        duration = 2.0
        n_samples = int(sr * duration)
        audio = np.zeros(n_samples, dtype=np.float32)
        # Place sharp onsets
        for i in range(4):
            idx = int(i * 0.5 * sr)
            if idx < n_samples:
                audio[idx : idx + 50] = 0.9

        detector = OnsetDetector()
        onsets = detector.detect(audio, sample_rate=sr, fps=30)
        assert isinstance(onsets, list)
        assert all(isinstance(o, int) for o in onsets)

    def test_detect_stereo_input(self) -> None:
        sr = 22050
        n_samples = sr * 2
        stereo = np.random.default_rng(42).random((n_samples, 2)).astype(np.float32)
        detector = OnsetDetector()
        onsets = detector.detect(stereo, sample_rate=sr, fps=30)
        assert isinstance(onsets, list)


class TestWaveformExtractor:
    def test_extract_shape(self) -> None:
        audio = np.random.default_rng(42).random(44100).astype(np.float32)
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=100)
        assert envelope.shape == (100,)
        assert envelope.dtype == np.float32

    def test_extract_normalized(self) -> None:
        """Output should be normalized to 0-1 range."""
        audio = np.random.default_rng(42).random(44100).astype(np.float32) * 5.0
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=50)
        assert float(np.max(envelope)) == pytest.approx(1.0, abs=0.01)
        assert float(np.min(envelope)) >= 0.0

    def test_extract_silent(self) -> None:
        audio = np.zeros(44100, dtype=np.float32)
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=10)
        np.testing.assert_array_equal(envelope, np.zeros(10, dtype=np.float32))

    def test_extract_empty(self) -> None:
        audio = np.array([], dtype=np.float32)
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=5)
        assert envelope.shape == (5,)
        np.testing.assert_array_equal(envelope, np.zeros(5, dtype=np.float32))

    def test_extract_stereo(self) -> None:
        audio = np.random.default_rng(42).random((44100, 2)).astype(np.float32)
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=50)
        assert envelope.shape == (50,)

    def test_extract_invalid_n_points(self) -> None:
        audio = np.zeros(100, dtype=np.float32)
        extractor = WaveformExtractor()
        with pytest.raises(ValueError, match="n_points must be >= 1"):
            extractor.extract(audio, n_points=0)

    def test_extract_single_point(self) -> None:
        audio = np.ones(1000, dtype=np.float32) * 0.5
        extractor = WaveformExtractor()
        envelope = extractor.extract(audio, n_points=1)
        assert envelope.shape == (1,)
        assert envelope[0] == pytest.approx(1.0)
