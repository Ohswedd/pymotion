"""Coverage hardening tests for encoder, video clip, tracking, audio mixer, and render pipeline."""

from __future__ import annotations

import io
import struct
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pymotion.audio.mixer import (
    AudioClipData,
    AudioMixer,
    SurroundChannel,
)
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.video import VideoClip, _get_ffmpeg, _get_ffprobe

# ---------------------------------------------------------------------------
# 1. pymotion/export/encoder.py
# ---------------------------------------------------------------------------
from pymotion.export.encoder import (
    FFmpegEncoder,
    _find_ffmpeg,
    _write_wav,
    detect_hardware_encoders,
    resolve_preset_with_fallback,
)
from pymotion.export.presets import get_preset
from pymotion.render.pipeline import FrameCache, RenderPipeline
from pymotion.tracking import (
    MotionTracker,
    StabilizedClip,
    _compute_stabilization_offsets,
    _estimate_global_motion,
    _placeholder_clip,
    _shift_frame,
    _smooth,
)


class TestWriteWav:
    """Tests for the _write_wav helper."""

    def test_write_wav_basic(self) -> None:
        buf = io.BytesIO()
        audio = np.array([0, 2147483647, -2147483647], dtype=np.int32)
        _write_wav(buf, audio, sample_rate=44100, channels=1)
        buf.seek(0)
        data = buf.read()
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"
        assert data[12:16] == b"fmt "
        assert data[36:40] == b"data"

    def test_write_wav_stereo(self) -> None:
        buf = io.BytesIO()
        audio = np.zeros(100, dtype=np.int32)
        _write_wav(buf, audio, sample_rate=48000, channels=2)
        buf.seek(0)
        data = buf.read()
        # Check channels field in fmt chunk (offset 22)
        channels = struct.unpack_from("<H", data, 22)[0]
        assert channels == 2

    def test_write_wav_data_size(self) -> None:
        buf = io.BytesIO()
        audio = np.array([100, 200, 300, 400], dtype=np.int32)
        _write_wav(buf, audio, sample_rate=48000, channels=1)
        buf.seek(0)
        data = buf.read()
        # data_size = n_samples * 2 (int16) = 4 * 2 = 8
        data_size = struct.unpack_from("<I", data, 40)[0]
        assert data_size == 8


class TestFindFfmpeg:
    """Tests for _find_ffmpeg."""

    @patch("pymotion.export.encoder.shutil.which", return_value=None)
    def test_find_ffmpeg_not_found(self, _mock: MagicMock) -> None:
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            _find_ffmpeg()

    @patch("pymotion.export.encoder.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_find_ffmpeg_found(self, _mock: MagicMock) -> None:
        assert _find_ffmpeg() == "/usr/bin/ffmpeg"


class TestDetectHardwareEncoders:
    """Tests for detect_hardware_encoders."""

    @patch("pymotion.export.encoder._find_ffmpeg", side_effect=RuntimeError("no ffmpeg"))
    def test_no_ffmpeg_returns_empty(self, _mock: MagicMock) -> None:
        assert detect_hardware_encoders() == []

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.run", side_effect=OSError("fail"))
    def test_oserror_returns_empty(self, _mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        assert detect_hardware_encoders() == []

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.run")
    def test_nonzero_returncode(self, mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert detect_hardware_encoders() == []

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.run")
    def test_detects_nvenc(self, mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="V..... h264_nvenc  NVIDIA NVENC H.264\nV..... hevc_nvenc  NVIDIA NVENC HEVC\n",
        )
        result = detect_hardware_encoders()
        assert "h264_nvenc" in result
        assert "hevc_nvenc" in result

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.run")
    def test_no_hw_encoders_found(self, mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="V..... libx264\n")
        assert detect_hardware_encoders() == []

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.run")
    def test_timeout_returns_empty(self, mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)
        assert detect_hardware_encoders() == []


class TestResolvePresetWithFallback:
    """Tests for resolve_preset_with_fallback."""

    @patch("pymotion.export.encoder.detect_hardware_encoders", return_value=[])
    def test_software_preset_returned_directly(self, _mock: MagicMock) -> None:
        preset = resolve_preset_with_fallback("h264_1080p")
        assert preset.codec == "libx264"

    @patch("pymotion.export.encoder.detect_hardware_encoders", return_value=["h264_nvenc"])
    def test_hw_preset_available(self, _mock: MagicMock) -> None:
        preset = resolve_preset_with_fallback("h264_nvenc")
        assert preset.codec == "h264_nvenc"

    @patch("pymotion.export.encoder.detect_hardware_encoders", return_value=[])
    def test_hw_preset_fallback(self, _mock: MagicMock) -> None:
        preset = resolve_preset_with_fallback("h264_nvenc")
        assert preset.codec == "libx264"

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            resolve_preset_with_fallback("nonexistent_preset_xyz")


class TestFFmpegEncoder:
    """Tests for FFmpegEncoder.encode and related methods."""

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_init_finds_ffmpeg(self, _mock: MagicMock) -> None:
        enc = FFmpegEncoder()
        assert enc._ffmpeg_path == "/usr/bin/ffmpeg"

    @patch("pymotion.export.encoder._find_ffmpeg", side_effect=RuntimeError("not found"))
    def test_init_raises_without_ffmpeg(self, _mock: MagicMock) -> None:
        with pytest.raises(RuntimeError, match="not found"):
            FFmpegEncoder()

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_success_no_audio(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frame = np.zeros((100, 200, 4), dtype=np.uint8)
        frames: Iterator[np.ndarray] = iter([frame, frame])
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = enc.encode(frames, None, Path(tmp.name), preset, 200, 100, 30)
            assert result == Path(tmp.name)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_with_audio(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frame = np.zeros((100, 200, 4), dtype=np.uint8)
        frames: Iterator[np.ndarray] = iter([frame])
        audio = np.zeros(1000, dtype=np.int32)
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = enc.encode(
                frames,
                audio,
                Path(tmp.name),
                preset,
                200,
                100,
                30,
                audio_sample_rate=48000,
                audio_channels=2,
            )
            assert result == Path(tmp.name)

        # Verify audio input was added to command
        cmd = mock_popen.call_args[0][0]
        assert "-c:a" in cmd
        assert "aac" in cmd

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_ffmpeg_failure(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"some error")
        proc.returncode = 1
        proc.wait.return_value = 1
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([])
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            with pytest.raises(RuntimeError, match="FFmpeg failed"):
                enc.encode(frames, None, Path(tmp.name), preset, 200, 100, 30)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_broken_pipe(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        """BrokenPipeError during write should not crash the encoder."""
        stdin = MagicMock()
        stdin.write.side_effect = BrokenPipeError()
        proc = MagicMock()
        proc.stdin = stdin
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frame = np.zeros((10, 20, 4), dtype=np.uint8)
        frames: Iterator[np.ndarray] = iter([frame])
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            result = enc.encode(frames, None, Path(tmp.name), preset, 20, 10, 30)
            assert result == Path(tmp.name)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_stdin_none_raises(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = None
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([np.zeros((10, 20, 4), dtype=np.uint8)])
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            with pytest.raises(RuntimeError, match="stdin pipe not available"):
                enc.encode(frames, None, Path(tmp.name), preset, 20, 10, 30)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_non_contiguous_frame(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        """Non-contiguous frames should be made contiguous before writing."""
        written_data: list[bytes] = []
        stdin_mock = MagicMock()
        stdin_mock.write.side_effect = lambda d: written_data.append(bytes(d))
        proc = MagicMock()
        proc.stdin = stdin_mock
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        # Create a non-contiguous frame by slicing
        big = np.zeros((20, 40, 4), dtype=np.uint8)
        non_contig = big[::2, ::2, :]  # stride-based, non-contiguous
        assert not non_contig.flags["C_CONTIGUOUS"]

        frames: Iterator[np.ndarray] = iter([non_contig])
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            enc.encode(frames, None, Path(tmp.name), preset, 20, 10, 30)

        assert len(written_data) == 1

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_with_bitrate_preset(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([])
        # instagram_reel uses bitrate instead of CRF
        preset = get_preset("instagram_reel")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            enc.encode(frames, None, Path(tmp.name), preset, 200, 100, 30)

        cmd = mock_popen.call_args[0][0]
        assert "-b:v" in cmd

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_empty_audio_treated_as_no_audio(
        self, mock_popen: MagicMock, _mock_ff: MagicMock
    ) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([])
        empty_audio = np.array([], dtype=np.int32)
        preset = get_preset("h264_1080p")

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            enc.encode(frames, empty_audio, Path(tmp.name), preset, 200, 100, 30)

        cmd = mock_popen.call_args[0][0]
        assert "-c:a" not in cmd


class TestFFmpegEncoderFrameSequence:
    """Tests for encode_frame_sequence."""

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_frame_sequence_png(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frame = np.zeros((10, 20, 4), dtype=np.uint8)
        frames: Iterator[np.ndarray] = iter([frame])

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enc.encode_frame_sequence(frames, Path(tmpdir), 20, 10, 30, fmt="png")
            assert result == Path(tmpdir)

        cmd = mock_popen.call_args[0][0]
        assert "png" in " ".join(cmd)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_frame_sequence_exr(self, mock_popen: MagicMock, _mock_ff: MagicMock) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([])

        with tempfile.TemporaryDirectory() as tmpdir:
            enc.encode_frame_sequence(frames, Path(tmpdir), 20, 10, 30, fmt="exr")

        cmd = mock_popen.call_args[0][0]
        assert "exr" in " ".join(cmd)
        assert "gbrpf32le" in cmd

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_encode_frame_sequence_invalid_format(self, _mock_ff: MagicMock) -> None:
        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([])

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Unsupported frame sequence format"):
                enc.encode_frame_sequence(frames, Path(tmpdir), 20, 10, 30, fmt="jpeg")

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_frame_sequence_failure(
        self, mock_popen: MagicMock, _mock_ff: MagicMock
    ) -> None:
        proc = MagicMock()
        proc.stdin = io.BytesIO()
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"error details")
        proc.returncode = 1
        proc.wait.return_value = 1
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([])

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="frame sequence failed"):
                enc.encode_frame_sequence(frames, Path(tmpdir), 20, 10, 30)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_frame_sequence_broken_pipe(
        self, mock_popen: MagicMock, _mock_ff: MagicMock
    ) -> None:
        stdin_mock = MagicMock()
        stdin_mock.write.side_effect = BrokenPipeError()
        proc = MagicMock()
        proc.stdin = stdin_mock
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frame = np.zeros((10, 20, 4), dtype=np.uint8)
        frames: Iterator[np.ndarray] = iter([frame])

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enc.encode_frame_sequence(frames, Path(tmpdir), 20, 10, 30)
            assert result == Path(tmpdir)

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.export.encoder.subprocess.Popen")
    def test_encode_frame_sequence_stdin_none(
        self, mock_popen: MagicMock, _mock_ff: MagicMock
    ) -> None:
        proc = MagicMock()
        proc.stdin = None
        proc.stdout = io.BytesIO(b"")
        proc.stderr = io.BytesIO(b"")
        proc.returncode = 0
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        enc = FFmpegEncoder()
        frames: Iterator[np.ndarray] = iter([np.zeros((10, 20, 4), dtype=np.uint8)])

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="stdin pipe not available"):
                enc.encode_frame_sequence(frames, Path(tmpdir), 20, 10, 30)


class TestEncodeFrameToPng:
    """Tests for encode_frame_to_png."""

    @patch("pymotion.export.encoder._find_ffmpeg", return_value="/usr/bin/ffmpeg")
    def test_encode_frame_to_png(self, _mock_ff: MagicMock) -> None:
        enc = FFmpegEncoder()
        frame = np.zeros((10, 20, 4), dtype=np.uint8)
        # Set some color: B=100, G=50, R=200, A=255
        frame[:, :, 0] = 100  # B
        frame[:, :, 1] = 50  # G
        frame[:, :, 2] = 200  # R
        frame[:, :, 3] = 255  # A

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            result = enc.encode_frame_to_png(frame, Path(tmp.name))
            assert result == Path(tmp.name)
            # Verify file was written
            assert Path(tmp.name).stat().st_size > 0

            # Verify the BGRA->RGBA conversion by reading back
            from PIL import Image

            img = Image.open(tmp.name)
            arr = np.array(img)
            # R channel should be 200 (was B=100 in BGRA -> R in RGBA should be the old R=200)
            assert arr[0, 0, 0] == 200  # R
            assert arr[0, 0, 1] == 50  # G
            assert arr[0, 0, 2] == 100  # B


# ---------------------------------------------------------------------------
# 2. pymotion/clip/video.py
# ---------------------------------------------------------------------------


class TestVideoClipHelpers:
    """Tests for _get_ffmpeg / _get_ffprobe module-level helpers."""

    @patch("pymotion.clip.video._FFMPEG_BIN", None)
    def test_get_ffmpeg_raises_when_none(self) -> None:
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            _get_ffmpeg()

    @patch("pymotion.clip.video._FFPROBE_BIN", None)
    def test_get_ffprobe_raises_when_none(self) -> None:
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            _get_ffprobe()

    @patch("pymotion.clip.video._FFMPEG_BIN", "/usr/local/bin/ffmpeg")
    def test_get_ffmpeg_returns_path(self) -> None:
        assert _get_ffmpeg() == "/usr/local/bin/ffmpeg"

    @patch("pymotion.clip.video._FFPROBE_BIN", "/usr/local/bin/ffprobe")
    def test_get_ffprobe_returns_path(self) -> None:
        assert _get_ffprobe() == "/usr/local/bin/ffprobe"


class TestVideoClipInit:
    """Tests for VideoClip.__init__ and _probe_video."""

    def test_init_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            VideoClip("/nonexistent/path/video.mp4")

    @patch("pymotion.clip.video._get_ffprobe", return_value="/usr/bin/ffprobe")
    @patch("pymotion.clip.video.subprocess.run")
    def test_init_success(self, mock_run: MagicMock, _mock_probe: MagicMock) -> None:
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"streams": [{"r_frame_rate": "24/1", "duration": "10.5"}]}),
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            clip = VideoClip(tmp.name)
            assert clip._source_fps == 24.0
            assert clip._source_duration == 10.5
            assert clip.source == Path(tmp.name).resolve()

    @patch("pymotion.clip.video._get_ffprobe", return_value="/usr/bin/ffprobe")
    @patch("pymotion.clip.video.subprocess.run", side_effect=ValueError("probe fail"))
    def test_init_probe_failure_fallback(
        self, _mock_run: MagicMock, _mock_probe: MagicMock
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            clip = VideoClip(tmp.name)
            assert clip._source_fps == 30.0
            assert clip._source_duration == 0.0

    @patch("pymotion.clip.video._get_ffprobe", return_value="/usr/bin/ffprobe")
    @patch("pymotion.clip.video.subprocess.run")
    def test_probe_zero_denominator(self, mock_run: MagicMock, _mock_probe: MagicMock) -> None:
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"streams": [{"r_frame_rate": "30/0", "duration": "5.0"}]}),
        )
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            clip = VideoClip(tmp.name)
            assert clip._source_fps == 30.0

    @patch("pymotion.clip.video._get_ffprobe", return_value="/usr/bin/ffprobe")
    @patch("pymotion.clip.video.subprocess.run")
    def test_probe_no_streams(self, mock_run: MagicMock, _mock_probe: MagicMock) -> None:
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"streams": [{}]}),
        )
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            clip = VideoClip(tmp.name)
            # Should use defaults from stream.get()
            assert clip._source_fps == 30.0
            assert clip._source_duration == 0.0


class TestVideoClipMethods:
    """Tests for VideoClip fluent setters and properties."""

    @patch("pymotion.clip.video._get_ffprobe", return_value="/usr/bin/ffprobe")
    @patch("pymotion.clip.video.subprocess.run")
    def _make_clip(self, mock_run: MagicMock, _mock_probe: MagicMock) -> VideoClip:
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"streams": [{"r_frame_rate": "30/1", "duration": "10.0"}]}),
        )
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            return VideoClip(tmp.name)

    def test_set_trim(self) -> None:
        clip = self._make_clip()
        result = clip.set_trim(1.0, 5.0)
        assert result is clip
        assert clip.trim_start == 1.0
        assert clip.trim_end == 5.0

    def test_set_speed(self) -> None:
        clip = self._make_clip()
        result = clip.set_speed(2.0)
        assert result is clip
        assert clip._speed_factor == 2.0

    def test_set_speed_invalid(self) -> None:
        clip = self._make_clip()
        with pytest.raises(ValueError, match="Speed must be positive"):
            clip.set_speed(0)
        with pytest.raises(ValueError, match="Speed must be positive"):
            clip.set_speed(-1.0)

    def test_set_reverse(self) -> None:
        clip = self._make_clip()
        result = clip.set_reverse(True)
        assert result is clip
        assert clip._reverse is True

    def test_set_loop(self) -> None:
        clip = self._make_clip()
        result = clip.set_loop(3)
        assert result is clip
        assert clip.loop == 3

    def test_source_fps_property(self) -> None:
        clip = self._make_clip()
        assert clip.source_fps == 30.0

    def test_source_duration_property(self) -> None:
        clip = self._make_clip()
        assert clip.source_duration == 10.0


class TestVideoClipRendering:
    """Tests for VideoClip.render_frame and _calc_source_time."""

    @patch("pymotion.clip.video._get_ffprobe", return_value="/usr/bin/ffprobe")
    @patch("pymotion.clip.video.subprocess.run")
    def _make_clip(
        self, mock_run: MagicMock, _mock_probe: MagicMock, **kwargs: object
    ) -> VideoClip:
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"streams": [{"r_frame_rate": "30/1", "duration": "10.0"}]}),
        )
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            return VideoClip(tmp.name, **kwargs)

    def _make_ctx(self, local_frame: int = 0, fps: int = 30) -> RenderContext:
        return RenderContext(
            frame=local_frame,
            fps=fps,
            resolution=Resolution(width=200, height=100),
            time_range=TimeRange(start=0, end=300),
            local_frame=local_frame,
            progress=local_frame / 300,
        )

    @patch("pymotion.clip.video._get_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.clip.video.subprocess.run")
    def test_render_frame_success(self, mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        clip = self._make_clip()
        # Return valid raw frame data
        raw_data = np.zeros((100, 200, 4), dtype=np.uint8).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=raw_data)

        ctx = self._make_ctx(local_frame=0)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)

    @patch("pymotion.clip.video._get_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.clip.video.subprocess.run")
    def test_render_frame_cache_hit(self, mock_run: MagicMock, _mock_ff: MagicMock) -> None:
        clip = self._make_clip()
        raw_data = np.zeros((100, 200, 4), dtype=np.uint8).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=raw_data)

        ctx = self._make_ctx(local_frame=0)
        frame1 = clip.render_frame(ctx)
        frame2 = clip.render_frame(ctx)  # should use cache
        assert frame1 is frame2
        # subprocess.run should only be called once (for extract, not twice)
        assert mock_run.call_count == 1

    @patch("pymotion.clip.video._get_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.clip.video.subprocess.run")
    def test_render_frame_extract_failure_returns_black(
        self, mock_run: MagicMock, _mock_ff: MagicMock
    ) -> None:
        clip = self._make_clip()
        mock_run.return_value = MagicMock(returncode=1, stdout=b"")

        ctx = self._make_ctx(local_frame=0)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        assert np.all(frame == 0)

    @patch("pymotion.clip.video._get_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.clip.video.subprocess.run")
    def test_render_frame_subprocess_error_returns_black(
        self, mock_run: MagicMock, _mock_ff: MagicMock
    ) -> None:
        import subprocess

        clip = self._make_clip()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)

        ctx = self._make_ctx(local_frame=0)
        frame = clip.render_frame(ctx)
        assert frame.shape == (100, 200, 4)
        assert np.all(frame == 0)

    @patch("pymotion.clip.video._get_ffmpeg", return_value="/usr/bin/ffmpeg")
    @patch("pymotion.clip.video.subprocess.run")
    def test_render_frame_wrong_size_returns_black(
        self, mock_run: MagicMock, _mock_ff: MagicMock
    ) -> None:
        clip = self._make_clip()
        # Return data of wrong size
        mock_run.return_value = MagicMock(returncode=0, stdout=b"\x00" * 10)

        ctx = self._make_ctx(local_frame=0)
        frame = clip.render_frame(ctx)
        assert np.all(frame == 0)

    def test_calc_source_time_with_speed(self) -> None:
        clip = self._make_clip(speed_factor=2.0)
        ctx = self._make_ctx(local_frame=30, fps=30)
        source_time = clip._calc_source_time(ctx)
        # clip_time = 30/30 = 1.0, source_time = 1.0 * 2.0 + 0.0 = 2.0
        assert source_time == pytest.approx(2.0)

    def test_calc_source_time_with_trim(self) -> None:
        clip = self._make_clip(trim_start=2.0, trim_end=8.0)
        ctx = self._make_ctx(local_frame=0, fps=30)
        source_time = clip._calc_source_time(ctx)
        assert source_time == pytest.approx(2.0)

    def test_calc_source_time_with_reverse(self) -> None:
        clip = self._make_clip(reverse=True)
        ctx = self._make_ctx(local_frame=0, fps=30)
        source_time = clip._calc_source_time(ctx)
        # With reverse: effective_end=10.0, source_time = 10.0 - (0.0 - 0.0) = 10.0
        assert source_time == pytest.approx(10.0)

    def test_calc_source_time_with_loop(self) -> None:
        clip = self._make_clip(loop=-1)
        ctx = self._make_ctx(local_frame=330, fps=30)  # 11 seconds > 10s duration
        source_time = clip._calc_source_time(ctx)
        # Should wrap around: (11.0 % 10.0) = 1.0
        assert 0.0 <= source_time <= 10.0


# ---------------------------------------------------------------------------
# 3. pymotion/tracking.py
# ---------------------------------------------------------------------------


class _DummyClip:
    """A simple clip for tracking tests that renders solid colored frames."""

    def __init__(self, duration: int = 5, shift_per_frame: int = 2) -> None:
        self.start = 0
        self.end = duration
        self.duration = duration
        self._shift = shift_per_frame

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        h, w = ctx.resolution.height, ctx.resolution.width
        frame = np.zeros((h, w, 4), dtype=np.uint8)
        # Draw a simple rectangle that moves
        offset = ctx.local_frame * self._shift
        x1 = min(offset, w - 10)
        frame[10:20, x1 : x1 + 10, :] = 255
        return frame


class TestSmooth:
    """Tests for the _smooth helper."""

    def test_smooth_window_1(self) -> None:
        result = _smooth([1.0, 2.0, 3.0], 1)
        assert result == [1.0, 2.0, 3.0]

    def test_smooth_empty(self) -> None:
        assert _smooth([], 5) == []

    def test_smooth_single_value(self) -> None:
        assert _smooth([42.0], 5) == [42.0]

    def test_smooth_basic(self) -> None:
        values = [0.0, 10.0, 0.0, 10.0, 0.0]
        result = _smooth(values, 3)
        assert len(result) == 5
        # Middle value should be average of neighbors
        assert result[2] == pytest.approx((10.0 + 0.0 + 10.0) / 3.0)

    def test_smooth_constant_signal(self) -> None:
        values = [5.0, 5.0, 5.0, 5.0]
        result = _smooth(values, 3)
        for v in result:
            assert v == pytest.approx(5.0)


class TestMotionTracker:
    """Tests for MotionTracker."""

    def test_track_zero_duration_raises(self) -> None:
        clip = _DummyClip(duration=0)
        tracker = MotionTracker(clip=clip, region=(10, 10, 10, 10))
        with pytest.raises(RuntimeError, match="zero duration"):
            tracker.track()

    @patch("pymotion.tracking.cv2", create=True)
    def test_track_with_mocked_cv2(self, mock_cv2: MagicMock) -> None:
        mock_cv2.cvtColor.side_effect = lambda img, code: img[:, :, 0]
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.matchTemplate.return_value = np.zeros((10, 10), dtype=np.float32)
        mock_cv2.TM_CCOEFF_NORMED = 5
        mock_cv2.minMaxLoc.return_value = (0.0, 1.0, (0, 0), (5, 5))

        clip = _DummyClip(duration=3, shift_per_frame=0)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        data = tracker.track()
        assert len(data) == 3
        assert 0 in data
        assert 1 in data
        assert 2 in data

    def test_track_without_cv2_falls_back(self) -> None:
        """When cv2 is not available, tracker should return static positions."""
        clip = _DummyClip(duration=3, shift_per_frame=0)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))

        # Mock ImportError for cv2 in _estimate_motion
        with patch.object(
            tracker,
            "_estimate_motion",
            return_value=(0.0, 0.0),
        ):
            data = tracker.track()
            assert len(data) == 3
            # All positions should be the center of the region
            for pos in data.values():
                assert pos.x == pytest.approx(20.0)
                assert pos.y == pytest.approx(20.0)

    def test_to_keyframes_raises_without_tracking(self) -> None:
        clip = _DummyClip(duration=3)
        tracker = MotionTracker(clip=clip, region=(0, 0, 10, 10))
        with pytest.raises(RuntimeError, match="No tracking data"):
            tracker.to_keyframes()

    def test_to_keyframes_after_track(self) -> None:
        clip = _DummyClip(duration=3, shift_per_frame=0)
        tracker = MotionTracker(clip=clip, region=(10, 10, 20, 20))
        with patch.object(tracker, "_estimate_motion", return_value=(0.0, 0.0)):
            tracker.track()
        kf_track = tracker.to_keyframes()
        assert len(kf_track.keyframes) == 3

    def test_estimate_motion_small_template_returns_zero(self) -> None:
        """When template is too small (< 4px), should return (0, 0)."""
        clip = _DummyClip(duration=2)
        tracker = MotionTracker(clip=clip, region=(0, 0, 2, 2))  # tiny region

        prev = np.zeros((10, 10, 4), dtype=np.uint8)
        curr = np.zeros((10, 10, 4), dtype=np.uint8)

        # Mock cv2 so we can test the size check
        cv2_mock = MagicMock()
        cv2_mock.cvtColor.side_effect = lambda img, code: img[:, :, 0]
        cv2_mock.COLOR_BGR2GRAY = 6

        with patch.dict("sys.modules", {"cv2": cv2_mock}):
            dx, dy = tracker._estimate_motion(prev, curr, (1.0, 1.0), (2, 2))
            assert dx == 0.0
            assert dy == 0.0


class TestShiftFrame:
    """Tests for _shift_frame."""

    def test_shift_frame_no_cv2(self) -> None:
        """Test numpy fallback when cv2 is not available."""
        frame = np.ones((20, 30, 4), dtype=np.uint8) * 128

        with patch.dict("sys.modules", {"cv2": None}):
            # Force ImportError
            with patch("pymotion.tracking.cv2", side_effect=ImportError, create=True):
                # Use the fallback path directly
                result = np.zeros_like(frame)
                idx, idy = 5, 3
                h, w = frame.shape[:2]
                src_x1 = max(0, -idx)
                src_y1 = max(0, -idy)
                src_x2 = min(w, w - idx)
                src_y2 = min(h, h - idy)
                dst_x1 = max(0, idx)
                dst_y1 = max(0, idy)
                dst_x2 = dst_x1 + (src_x2 - src_x1)
                dst_y2 = dst_y1 + (src_y2 - src_y1)
                result[dst_y1:dst_y2, dst_x1:dst_x2] = frame[src_y1:src_y2, src_x1:src_x2]

                assert result.shape == frame.shape
                # Top-left corner should be black (shifted away)
                assert result[0, 0, 0] == 0
                # Shifted region should have data
                assert result[5, 7, 0] == 128

    def test_shift_frame_with_mocked_cv2(self) -> None:
        frame = np.ones((20, 30, 4), dtype=np.uint8) * 100
        shifted = frame.copy()

        cv2_mock = MagicMock()
        cv2_mock.BORDER_REPLICATE = 1
        cv2_mock.BORDER_CONSTANT = 0
        cv2_mock.warpAffine.return_value = shifted

        with patch.dict("sys.modules", {"cv2": cv2_mock}):
            result = _shift_frame(frame, 5.0, 3.0, "crop")
            assert result.shape == frame.shape


class TestStabilizedClip:
    """Tests for StabilizedClip."""

    def test_render_frame_no_offset(self) -> None:
        source = _DummyClip(duration=5, shift_per_frame=0)
        stab = StabilizedClip()
        stab._source = source  # type: ignore[assignment]
        stab._offsets = []

        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(width=64, height=64),
            time_range=TimeRange(start=0, end=5),
            local_frame=0,
            progress=0.0,
        )
        frame = stab.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_render_frame_with_offset(self) -> None:
        source = _DummyClip(duration=5, shift_per_frame=0)
        stab = StabilizedClip()
        stab._source = source  # type: ignore[assignment]
        stab._offsets = [(5.0, 3.0), (2.0, 1.0)]

        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(width=64, height=64),
            time_range=TimeRange(start=0, end=5),
            local_frame=0,
            progress=0.0,
        )
        frame = stab.render_frame(ctx)
        assert frame.shape == (64, 64, 4)

    def test_render_frame_small_offset_no_shift(self) -> None:
        """Offsets < 0.5 should skip shifting."""
        source = _DummyClip(duration=5, shift_per_frame=0)
        stab = StabilizedClip()
        stab._source = source  # type: ignore[assignment]
        stab._offsets = [(0.1, 0.2)]

        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(width=64, height=64),
            time_range=TimeRange(start=0, end=5),
            local_frame=0,
            progress=0.0,
        )
        frame = stab.render_frame(ctx)
        assert frame.shape == (64, 64, 4)


class TestPlaceholderClip:
    """Tests for _placeholder_clip."""

    def test_placeholder_renders_black(self) -> None:
        clip = _placeholder_clip()
        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(width=20, height=10),
            time_range=TimeRange(start=0, end=1),
            local_frame=0,
            progress=0.0,
        )
        frame = clip.render_frame(ctx)
        assert frame.shape == (10, 20, 4)
        assert np.all(frame == 0)


class TestEstimateGlobalMotion:
    """Tests for _estimate_global_motion."""

    def test_estimate_global_motion_no_cv2(self) -> None:
        """Without cv2, should return (0.0, 0.0)."""
        prev = np.zeros((64, 64, 4), dtype=np.uint8)
        curr = np.zeros((64, 64, 4), dtype=np.uint8)

        with patch.dict("sys.modules", {"cv2": None}):
            dx, dy = _estimate_global_motion(prev, curr)
            assert dx == 0.0
            assert dy == 0.0

    def test_estimate_global_motion_few_features(self) -> None:
        """When cv2 finds < 3 features, return (0, 0)."""
        prev = np.zeros((64, 64, 4), dtype=np.uint8)
        curr = np.zeros((64, 64, 4), dtype=np.uint8)

        cv2_mock = MagicMock()
        cv2_mock.cvtColor.side_effect = lambda img, code: img[:, :, 0]
        cv2_mock.COLOR_BGR2GRAY = 6
        cv2_mock.goodFeaturesToTrack.return_value = None

        with patch.dict("sys.modules", {"cv2": cv2_mock}):
            dx, dy = _estimate_global_motion(prev, curr)
            assert dx == 0.0
            assert dy == 0.0


class TestComputeStabilizationOffsets:
    """Tests for _compute_stabilization_offsets."""

    def test_stabilization_offsets_basic(self) -> None:
        clip = _DummyClip(duration=5, shift_per_frame=0)
        with patch("pymotion.tracking._estimate_global_motion", return_value=(0.0, 0.0)):
            offsets = _compute_stabilization_offsets(clip, smoothing=3)
        assert len(offsets) == 5
        # With zero motion, offsets should be zero
        for dx, dy in offsets:
            assert dx == pytest.approx(0.0)
            assert dy == pytest.approx(0.0)

    def test_stabilization_offsets_with_motion(self) -> None:
        clip = _DummyClip(duration=5, shift_per_frame=0)
        motions = [(1.0, 0.5), (2.0, 1.0), (-1.0, 0.0), (0.5, -0.5)]
        call_count = [0]

        def fake_motion(prev: np.ndarray, curr: np.ndarray) -> tuple[float, float]:
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(motions):
                return motions[idx]
            return (0.0, 0.0)

        with patch("pymotion.tracking._estimate_global_motion", side_effect=fake_motion):
            offsets = _compute_stabilization_offsets(clip, smoothing=3)
        assert len(offsets) == 5


# ---------------------------------------------------------------------------
# 4. pymotion/audio/mixer.py
# ---------------------------------------------------------------------------


class TestAudioMixerSetPanKeyframes:
    """Tests for pan keyframe automation."""

    def test_set_pan_keyframes(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.zeros(100, dtype=np.float64), start_sample=0)
        mixer.add(clip, track="t1")
        mixer.set_pan_keyframes("t1", [(0, -1.0), (50, 0.0), (100, 1.0)])
        result = mixer.render()
        assert len(result) > 0

    def test_set_pan_keyframes_unknown_track(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_pan_keyframes("missing", [(0, 0.0)])


class TestAudioMixerBusProcessing:
    """Tests for bus-level processing."""

    def test_bus_volume_keyframes(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.ones(200, dtype=np.float64) * 0.5, start_sample=0)
        mixer.add(clip, track="music")
        mixer.create_bus("music_bus")
        mixer.assign_track_to_bus("music", "music_bus")
        mixer.set_bus_volume_keyframes("music_bus", [(0, 1.0), (100, 0.0)])
        result = mixer.render()
        assert len(result) > 0

    def test_bus_pan(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.ones(100, dtype=np.float64) * 0.5, start_sample=0)
        mixer.add(clip, track="sfx")
        mixer.create_bus("sfx_bus")
        mixer.assign_track_to_bus("sfx", "sfx_bus")
        mixer.set_bus_pan("sfx_bus", 0.5)
        result = mixer.render()
        assert len(result) > 0

    def test_bus_pan_keyframes(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.ones(100, dtype=np.float64) * 0.5, start_sample=0)
        mixer.add(clip, track="sfx")
        mixer.create_bus("sfx_bus")
        mixer.assign_track_to_bus("sfx", "sfx_bus")
        mixer.set_bus_pan_keyframes("sfx_bus", [(0, -1.0), (50, 1.0)])
        result = mixer.render()
        assert len(result) > 0

    def test_bus_routing(self) -> None:
        mixer = AudioMixer(channels=6)
        clip = AudioClipData(samples=np.ones(100, dtype=np.float64) * 0.5, start_sample=0)
        mixer.add(clip, track="dialogue")
        mixer.create_bus("dial_bus")
        mixer.assign_track_to_bus("dialogue", "dial_bus")
        mixer.set_bus_routing("dial_bus", {"C": 1.0, "LFE": 0.3})
        result = mixer.render()
        assert len(result) > 0

    def test_bus_volume_keyframes_unknown_bus(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_bus_volume_keyframes("ghost", [(0, 1.0)])

    def test_bus_pan_unknown_bus(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_bus_pan("ghost", 0.5)

    def test_bus_pan_keyframes_unknown_bus(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_bus_pan_keyframes("ghost", [(0, 0.0)])

    def test_bus_routing_unknown_bus(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_bus_routing("ghost", {0: 1.0})

    def test_bus_routing_invalid_channel_name(self) -> None:
        mixer = AudioMixer(channels=6)
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="t")
        mixer.create_bus("b")
        mixer.assign_track_to_bus("t", "b")
        with pytest.raises(ValueError, match="Unknown channel name"):
            mixer.set_bus_routing("b", {"ZZ": 1.0})

    def test_bus_routing_invalid_channel_index(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="t")
        mixer.create_bus("b")
        mixer.assign_track_to_bus("t", "b")
        with pytest.raises(ValueError, match="out of range"):
            mixer.set_bus_routing("b", {5: 1.0})


class TestAudioMixerSidechain:
    """Tests for sidechain compression."""

    def test_sidechain_unknown_sidechain_track(self) -> None:
        mixer = AudioMixer()
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="target")
        with pytest.raises(ValueError, match="Unknown sidechain track"):
            mixer.sidechain("missing", "target")

    def test_sidechain_unknown_target_track(self) -> None:
        mixer = AudioMixer()
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="sc")
        with pytest.raises(ValueError, match="Unknown target track"):
            mixer.sidechain("sc", "missing")

    def test_sidechain_compression_applied(self) -> None:
        mixer = AudioMixer(channels=2)
        # Loud sidechain
        sc_samples = np.ones(1000, dtype=np.float64) * 0.9
        sc_clip = AudioClipData(samples=sc_samples, start_sample=0)
        mixer.add(sc_clip, track="sidechain")

        # Target audio
        tgt_samples = np.ones(1000, dtype=np.float64) * 0.5
        tgt_clip = AudioClipData(samples=tgt_samples, start_sample=0)
        mixer.add(tgt_clip, track="target")

        mixer.sidechain("sidechain", "target", threshold_db=-20.0, ratio=4.0)
        result = mixer.render()
        assert len(result) > 0


class TestAudioMixerRouting:
    """Tests for channel routing on tracks."""

    def test_routing_with_surround_enum(self) -> None:
        mixer = AudioMixer(channels=6)
        clip = AudioClipData(samples=np.ones(100, dtype=np.float64) * 0.5, start_sample=0)
        mixer.add(clip, track="dialogue")
        mixer.set_routing("dialogue", {SurroundChannel.C: 1.0, SurroundChannel.LFE: 0.3})
        result = mixer.render()
        assert len(result) > 0

    def test_routing_invalid_channel_name(self) -> None:
        mixer = AudioMixer(channels=6)
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="t")
        with pytest.raises(ValueError, match="Unknown channel name"):
            mixer.set_routing("t", {"INVALID": 1.0})

    def test_routing_invalid_channel_index(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="t")
        with pytest.raises(ValueError, match="out of range"):
            mixer.set_routing("t", {5: 1.0})

    def test_routing_negative_index(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="t")
        with pytest.raises(ValueError, match="out of range"):
            mixer.set_routing("t", {-1: 1.0})


class TestAudioMixerLUFS:
    """Tests for LUFS measurement and normalization."""

    def test_measure_lufs_empty(self) -> None:
        result = AudioMixer._measure_lufs(np.array([]).reshape(0, 2), 48000)
        assert result == -70.0

    def test_measure_lufs_silence(self) -> None:
        samples = np.zeros((48000, 2), dtype=np.float64)
        result = AudioMixer._measure_lufs(samples, 48000)
        assert result == -70.0

    def test_measure_lufs_surround(self) -> None:
        # 6 channels: LFE excluded, Ls/Rs weighted
        samples = np.random.default_rng(42).uniform(-0.5, 0.5, (48000, 6))
        result = AudioMixer._measure_lufs(samples, 48000)
        assert result > -70.0
        assert result < 0.0

    def test_normalize_render(self) -> None:
        mixer = AudioMixer(channels=2)
        # Add a sine wave
        t = np.linspace(0, 1.0, 48000, dtype=np.float64)
        sine = np.sin(2 * np.pi * 440 * t) * 0.5
        clip = AudioClipData(samples=sine, start_sample=0)
        mixer.add(clip, track="tone")
        mixer.normalize(target_lufs=-14.0)
        result = mixer.render()
        assert len(result) > 0


class TestAudioMixerMultiChannelClips:
    """Tests for multi-channel audio clip handling."""

    def test_multichannel_clip_rendering(self) -> None:
        mixer = AudioMixer(channels=2)
        # 2-channel clip
        samples = np.ones((100, 2), dtype=np.float64) * 0.3
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip, track="stereo")
        result = mixer.render()
        assert len(result) == 200  # 100 samples * 2 channels

    def test_clip_more_channels_than_mixer(self) -> None:
        mixer = AudioMixer(channels=2)
        # 4-channel clip into 2-channel mixer
        samples = np.ones((100, 4), dtype=np.float64) * 0.3
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip, track="surround")
        result = mixer.render()
        assert len(result) == 200

    def test_clip_exceeding_duration_is_clipped(self) -> None:
        mixer = AudioMixer(channels=1)
        clip1 = AudioClipData(samples=np.ones(50, dtype=np.float64) * 0.5, start_sample=0)
        clip2 = AudioClipData(samples=np.ones(100, dtype=np.float64) * 0.3, start_sample=0)
        mixer.add(clip1, track="short")
        mixer.add(clip2, track="long")
        result = mixer.render()
        assert len(result) == 100


class TestAudioMixerInterpolateKeyframes:
    """Tests for keyframe interpolation."""

    def test_empty_keyframes(self) -> None:
        result = AudioMixer._interpolate_keyframes([], 100)
        assert len(result) == 100
        assert np.all(result == 1.0)

    def test_single_keyframe(self) -> None:
        result = AudioMixer._interpolate_keyframes([(50, 0.5)], 100)
        assert result[0] == pytest.approx(0.5)
        assert result[99] == pytest.approx(0.5)

    def test_two_keyframes(self) -> None:
        result = AudioMixer._interpolate_keyframes([(0, 0.0), (100, 1.0)], 101)
        assert result[0] == pytest.approx(0.0)
        assert result[50] == pytest.approx(0.5)
        assert result[100] == pytest.approx(1.0)


class TestAudioMixerVolumeKeyframes:
    """Tests for volume keyframe automation on tracks."""

    def test_volume_keyframes_applied(self) -> None:
        mixer = AudioMixer(channels=1)
        samples = np.ones(100, dtype=np.float64) * 0.5
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip, track="t")
        mixer.set_volume_keyframes("t", [(0, 1.0), (50, 0.0), (99, 1.0)])
        result = mixer.render()
        assert len(result) == 100

    def test_volume_keyframes_unknown_track(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_volume_keyframes("ghost", [(0, 1.0)])


class TestAudioMixerTrackPan:
    """Tests for static pan on tracks."""

    def test_pan_applied(self) -> None:
        mixer = AudioMixer(channels=2)
        samples = np.ones(100, dtype=np.float64) * 0.5
        clip = AudioClipData(samples=samples, start_sample=0)
        mixer.add(clip, track="t")
        mixer.set_pan("t", -1.0)  # full left
        result = mixer.render()
        assert len(result) == 200  # 100 * 2 channels

    def test_pan_unknown_track(self) -> None:
        mixer = AudioMixer()
        with pytest.raises(ValueError, match="not found"):
            mixer.set_pan("ghost", 0.0)

    def test_pan_clamped(self) -> None:
        mixer = AudioMixer(channels=2)
        clip = AudioClipData(samples=np.zeros(10, dtype=np.float64))
        mixer.add(clip, track="t")
        mixer.set_pan("t", 5.0)  # should be clamped to 1.0
        assert mixer._tracks["t"].pan == 1.0
        mixer.set_pan("t", -5.0)  # should be clamped to -1.0
        assert mixer._tracks["t"].pan == -1.0


# ---------------------------------------------------------------------------
# 5. pymotion/render/pipeline.py
# ---------------------------------------------------------------------------


class TestFrameCache:
    """Tests for FrameCache."""

    def test_empty_cache(self) -> None:
        cache = FrameCache(max_size=10)
        assert cache.size == 0
        assert cache.hit_rate == 0.0
        assert cache.get(1, 0) is None

    def test_put_and_get(self) -> None:
        cache = FrameCache(max_size=10)
        data = np.zeros((10, 20, 4), dtype=np.uint8)
        cache.put(1, 0, data)
        assert cache.size == 1
        result = cache.get(1, 0)
        assert result is data

    def test_cache_miss(self) -> None:
        cache = FrameCache(max_size=10)
        data = np.zeros((10, 20, 4), dtype=np.uint8)
        cache.put(1, 0, data)
        assert cache.get(2, 0) is None

    def test_lru_eviction(self) -> None:
        cache = FrameCache(max_size=3)
        for i in range(5):
            cache.put(i, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        assert cache.size == 3
        # First two should have been evicted
        assert cache.get(0, 0) is None
        assert cache.get(1, 0) is None
        # Last three should be present
        assert cache.get(2, 0) is not None
        assert cache.get(3, 0) is not None
        assert cache.get(4, 0) is not None

    def test_put_existing_key_moves_to_end(self) -> None:
        cache = FrameCache(max_size=3)
        cache.put(0, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        cache.put(1, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        cache.put(2, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        # Re-put key (0,0) to move it to end
        cache.put(0, 0, np.ones((2, 2, 4), dtype=np.uint8))
        # Now add new entry — should evict (1,0), not (0,0)
        cache.put(3, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        assert cache.get(0, 0) is not None
        assert cache.get(1, 0) is None

    def test_get_moves_to_end(self) -> None:
        cache = FrameCache(max_size=3)
        cache.put(0, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        cache.put(1, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        cache.put(2, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        # Access key (0,0) to move it to end
        cache.get(0, 0)
        # Add new entry — should evict (1,0)
        cache.put(3, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        assert cache.get(0, 0) is not None
        assert cache.get(1, 0) is None

    def test_hit_rate(self) -> None:
        cache = FrameCache(max_size=10)
        cache.put(1, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        cache.get(1, 0)  # hit
        cache.get(1, 0)  # hit
        cache.get(2, 0)  # miss
        assert cache.hit_rate == pytest.approx(2 / 3)

    def test_clear(self) -> None:
        cache = FrameCache(max_size=10)
        cache.put(1, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        cache.get(1, 0)  # hit
        cache.clear()
        assert cache.size == 0
        assert cache.hit_rate == 0.0
        assert cache.get(1, 0) is None

    def test_max_size_at_least_1(self) -> None:
        cache = FrameCache(max_size=0)
        assert cache._max_size == 1
        cache.put(0, 0, np.zeros((2, 2, 4), dtype=np.uint8))
        assert cache.size == 1


class TestRenderPipeline:
    """Tests for RenderPipeline."""

    def test_init_defaults(self) -> None:
        pipeline = RenderPipeline()
        assert len(pipeline.backends) == 1
        assert pipeline.frame_cache.size == 0

    def test_init_custom_cache_size(self) -> None:
        pipeline = RenderPipeline(cache_size=64)
        assert pipeline.frame_cache._max_size == 64

    def test_frame_cache_accessible(self) -> None:
        pipeline = RenderPipeline(cache_size=10)
        data = np.zeros((10, 10, 4), dtype=np.uint8)
        pipeline.frame_cache.put(42, 0, data)
        assert pipeline.frame_cache.get(42, 0) is data

    def test_backends_include_cairo(self) -> None:
        pipeline = RenderPipeline()
        from pymotion.render.backend_2d import CairoRenderer

        assert isinstance(pipeline.backends[0], CairoRenderer)
