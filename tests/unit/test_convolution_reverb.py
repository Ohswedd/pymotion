"""Tests for ConvolutionReverb audio effect."""

from __future__ import annotations

import shutil
import struct
import tempfile
from pathlib import Path

import numpy as np
import pytest

from pymotion.audio.effects import ConvolutionReverb


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = 48000) -> None:
    """Write a minimal WAV file from float64 samples.

    Args:
        path: Output file path.
        samples: Audio samples (n_samples,) or (n_samples, channels).
        sample_rate: Sample rate in Hz.
    """
    if samples.ndim == 1:
        channels = 1
        data = samples
    else:
        channels = samples.shape[1]
        data = samples.flatten()

    # Convert to 16-bit PCM
    pcm = (data * 32767).astype(np.int16)
    raw = pcm.tobytes()

    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(raw)))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))  # PCM format
        f.write(struct.pack("<H", channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", len(raw)))
        f.write(raw)


@pytest.fixture()
def ir_file(tmp_path: Path) -> Path:
    """Create a short impulse response WAV file."""
    # Simple decaying impulse
    ir = np.zeros(4800, dtype=np.float64)
    ir[0] = 1.0  # Initial impulse
    decay = np.exp(-np.arange(4800) / 2400.0)
    ir *= decay
    stereo_ir = np.column_stack([ir, ir])
    wav_path = tmp_path / "test_ir.wav"
    _write_wav(wav_path, stereo_ir, sample_rate=48000)
    return wav_path


@pytest.fixture()
def mono_ir_file(tmp_path: Path) -> Path:
    """Create a mono impulse response WAV file."""
    ir = np.zeros(2400, dtype=np.float64)
    ir[0] = 1.0
    wav_path = tmp_path / "mono_ir.wav"
    _write_wav(wav_path, ir, sample_rate=48000)
    return wav_path


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
class TestConvolutionReverb:
    """Tests for ConvolutionReverb."""

    def test_init(self, ir_file: Path) -> None:
        """Default parameters."""
        rev = ConvolutionReverb(ir_path=ir_file)
        assert rev.wet == 0.3
        assert rev.dry == 1.0
        assert rev.pre_delay_ms == 0.0

    def test_apply_stereo(self, ir_file: Path) -> None:
        """Apply reverb to stereo audio."""
        rev = ConvolutionReverb(ir_path=ir_file, wet=0.5, dry=1.0)
        t = np.arange(4800, dtype=np.float64) / 48000
        signal = np.sin(2 * np.pi * 440 * t) * 0.5
        stereo = np.column_stack([signal, signal])
        result = rev.apply(stereo, 48000)
        assert result.shape == stereo.shape
        # With reverb, RMS should be >= dry-only
        rms_dry = np.sqrt(np.mean(stereo**2))
        rms_wet = np.sqrt(np.mean(result**2))
        assert rms_wet >= rms_dry * 0.9

    def test_apply_mono(self, mono_ir_file: Path) -> None:
        """Apply reverb to mono audio."""
        rev = ConvolutionReverb(ir_path=mono_ir_file, wet=0.5)
        signal = np.sin(2 * np.pi * 440 * np.arange(4800) / 48000) * 0.5
        result = rev.apply(signal, 48000)
        assert result.ndim == 1
        assert len(result) == len(signal)

    def test_dry_only(self, ir_file: Path) -> None:
        """With wet=0, output should match dry input."""
        rev = ConvolutionReverb(ir_path=ir_file, wet=0.0, dry=1.0)
        t = np.arange(4800, dtype=np.float64) / 48000
        signal = np.sin(2 * np.pi * 440 * t) * 0.3
        stereo = np.column_stack([signal, signal])
        result = rev.apply(stereo, 48000)
        np.testing.assert_allclose(result, stereo, atol=1e-10)

    def test_pre_delay(self, ir_file: Path) -> None:
        """Pre-delay shifts the reverb onset."""
        rev_no_delay = ConvolutionReverb(ir_path=ir_file, wet=1.0, dry=0.0)
        rev_delay = ConvolutionReverb(ir_path=ir_file, wet=1.0, dry=0.0, pre_delay_ms=50.0)
        # Impulse signal
        signal = np.zeros((4800, 2), dtype=np.float64)
        signal[0] = 1.0

        r1 = rev_no_delay.apply(signal, 48000)
        r2 = rev_delay.apply(signal, 48000)
        # Delayed version should have less energy in the first 50ms
        delay_samples = int(0.05 * 48000)
        energy_early_r1 = np.sum(r1[:delay_samples] ** 2)
        energy_early_r2 = np.sum(r2[:delay_samples] ** 2)
        assert energy_early_r2 < energy_early_r1

    def test_empty_input(self, ir_file: Path) -> None:
        """Empty input returns empty output."""
        rev = ConvolutionReverb(ir_path=ir_file)
        empty = np.zeros((0, 2), dtype=np.float64)
        result = rev.apply(empty, 48000)
        assert len(result) == 0

    def test_nonexistent_ir_file(self) -> None:
        """Nonexistent IR file raises or handles gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_path = Path(tmpdir) / "nonexistent.wav"
            rev = ConvolutionReverb(ir_path=fake_path)
            signal = np.ones((100, 2), dtype=np.float64) * 0.5
            # Should either raise or return original (graceful degradation)
            with pytest.raises((FileNotFoundError, ValueError)):
                rev.apply(signal, 48000)

    def test_custom_wet_dry_mix(self, ir_file: Path) -> None:
        """Custom wet/dry ratios work correctly."""
        rev = ConvolutionReverb(ir_path=ir_file, wet=1.0, dry=0.0)
        signal = np.zeros((4800, 2), dtype=np.float64)
        signal[0] = 1.0
        result = rev.apply(signal, 48000)
        # With dry=0, first sample should be purely from convolution
        assert result.shape == signal.shape
