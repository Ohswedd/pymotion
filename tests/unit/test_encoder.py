"""Tests for FFmpegEncoder and frame sequence encoding."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

from pymotion.export.encoder import FFmpegEncoder


@pytest.fixture
def has_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    return shutil.which("ffmpeg") is not None


class TestFrameSequence:
    """Test frame sequence encoding."""

    def test_invalid_format_raises(self, tmp_path: Path, has_ffmpeg: bool) -> None:
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        encoder = FFmpegEncoder()
        frames = iter([np.zeros((240, 320, 4), dtype=np.uint8)])
        with pytest.raises(ValueError, match="Unsupported"):
            encoder.encode_frame_sequence(frames, tmp_path / "out", 320, 240, 30, fmt="bmp")

    def test_png_sequence(self, tmp_path: Path, has_ffmpeg: bool) -> None:
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        encoder = FFmpegEncoder()
        frame = np.zeros((240, 320, 4), dtype=np.uint8)
        frame[:, :, 0] = 255  # blue channel
        frame[:, :, 3] = 255  # alpha
        frames = iter([frame, frame, frame])

        out_dir = tmp_path / "seq"
        result = encoder.encode_frame_sequence(frames, out_dir, 320, 240, 30, fmt="png")

        assert result == out_dir
        assert out_dir.is_dir()
        pngs = list(out_dir.glob("frame_*.png"))
        assert len(pngs) == 3

    def test_encode_frame_to_png(self, tmp_path: Path, has_ffmpeg: bool) -> None:
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        encoder = FFmpegEncoder()
        frame = np.zeros((240, 320, 4), dtype=np.uint8)
        frame[:, :, 2] = 255  # red in BGRA
        frame[:, :, 3] = 255

        out = tmp_path / "test.png"
        result = encoder.encode_frame_to_png(frame, out)
        assert result.exists()
        assert result.stat().st_size > 0
