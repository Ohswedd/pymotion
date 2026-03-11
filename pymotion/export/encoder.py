"""FFmpegEncoder — secure FFmpeg subprocess wrapper for video encoding.

Wraps FFmpeg with security constraints: shell=False, validated paths,
explicit argument lists, no user input in command strings.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

from pymotion.export.presets import OutputPreset
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


def _write_wav(
    f: Any,
    audio: np.ndarray,
    sample_rate: int,
    channels: int,
) -> None:
    """Write interleaved int32 audio to a WAV file.

    Args:
        f: Open file handle to write to.
        audio: Interleaved int32 audio samples.
        sample_rate: Sample rate in Hz.
        channels: Number of channels.
    """
    # Convert int32 to int16 for WAV compatibility
    audio_16 = (audio.astype(np.float64) / 2147483647.0 * 32767.0).astype(np.int16)
    data = audio_16.tobytes()
    n_samples = len(audio_16)
    bytes_per_sample = 2  # int16
    data_size = n_samples * bytes_per_sample
    # WAV header
    f.write(b"RIFF")
    f.write(struct.pack("<I", 36 + data_size))
    f.write(b"WAVE")
    f.write(b"fmt ")
    f.write(struct.pack("<I", 16))  # chunk size
    f.write(struct.pack("<H", 1))  # PCM
    f.write(struct.pack("<H", channels))
    f.write(struct.pack("<I", sample_rate))
    f.write(struct.pack("<I", sample_rate * channels * bytes_per_sample))
    f.write(struct.pack("<H", channels * bytes_per_sample))
    f.write(struct.pack("<H", bytes_per_sample * 8))
    f.write(b"data")
    f.write(struct.pack("<I", data_size))
    f.write(data)


def _find_ffmpeg() -> str:
    """Find the FFmpeg binary on the system.

    Returns:
        Path to the FFmpeg binary.

    Raises:
        RuntimeError: If FFmpeg is not found.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        msg = (
            "FFmpeg not found on PATH. Please install FFmpeg "
            "(https://ffmpeg.org/) and ensure it is in your PATH."
        )
        raise RuntimeError(msg)
    return ffmpeg


def detect_hardware_encoders() -> list[str]:
    """Detect available hardware encoders by probing FFmpeg.

    Checks for NVENC, QSV, and AMF encoders by running ``ffmpeg -encoders``
    and parsing the output.

    Returns:
        List of available hardware encoder codec names
        (e.g. ``["h264_nvenc", "hevc_nvenc", "h264_qsv"]``).
    """
    try:
        ffmpeg = _find_ffmpeg()
    except RuntimeError:
        return []

    try:
        result = subprocess.run(  # noqa: S603
            [ffmpeg, "-encoders", "-hide_banner"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []

    if result.returncode != 0:
        return []

    hw_codecs = [
        "h264_videotoolbox",
        "hevc_videotoolbox",
        "h264_nvenc",
        "hevc_nvenc",
        "h264_qsv",
        "hevc_qsv",
        "h264_amf",
        "hevc_amf",
    ]
    available: list[str] = []
    for line in result.stdout.splitlines():
        for codec in hw_codecs:
            if codec in line:
                available.append(codec)

    logger.info("hardware_encoders_detected", encoders=available)
    return available


# Software fallback mapping: hardware preset -> software preset name
_HW_FALLBACK_MAP: dict[str, str] = {
    "h264_nvenc": "h264_1080p",
    "h265_nvenc": "h265_1080p",
    "h264_qsv": "h264_1080p",
    "h264_amf": "h264_1080p",
    "h264_videotoolbox": "h264_1080p",
}

# Hardware encoder preference order by codec family
_HW_CODEC_PREFERENCE: dict[str, list[str]] = {
    "libx264": [
        "h264_videotoolbox",
        "h264_nvenc",
        "h264_qsv",
        "h264_amf",
    ],
    "libx265": [
        "hevc_videotoolbox",
        "hevc_nvenc",
        "hevc_qsv",
        "hevc_amf",
    ],
}


def resolve_preset_with_fallback(preset_name: str, *, try_hardware: bool = True) -> OutputPreset:
    """Resolve a preset name, with automatic hardware encoder detection.

    For software presets (e.g. ``h264_1080p``), if ``try_hardware`` is True,
    attempts to find and use a compatible hardware encoder on this system.
    For hardware presets, falls back to software if the encoder is unavailable.

    Args:
        preset_name: Name of the requested preset.
        try_hardware: If True, automatically upgrade software presets to
            hardware encoders when available. Defaults to True.

    Returns:
        The resolved OutputPreset (hardware or software fallback).

    Raises:
        ValueError: If the preset name is unknown.
    """
    from pymotion.export.presets import OutputPreset as _OutputPreset
    from pymotion.export.presets import get_preset

    preset = get_preset(preset_name)

    # Check if this is an explicit hardware preset
    fallback_name = _HW_FALLBACK_MAP.get(preset_name)
    if fallback_name is not None:
        available = detect_hardware_encoders()
        if preset.codec in available:
            logger.info("using_hardware_encoder", codec=preset.codec)
            return preset
        logger.info(
            "hardware_encoder_unavailable",
            requested=preset.codec,
            fallback=fallback_name,
        )
        return get_preset(fallback_name)

    # Auto-detect hardware encoder for software presets
    if try_hardware and preset.codec in _HW_CODEC_PREFERENCE:
        available = detect_hardware_encoders()
        for hw_codec in _HW_CODEC_PREFERENCE[preset.codec]:
            if hw_codec in available:
                logger.info(
                    "auto_hardware_encoder",
                    software=preset.codec,
                    hardware=hw_codec,
                )
                # Build a hardware-accelerated version of the preset
                hw_flags = ["-movflags", "+faststart"]
                if hw_codec == "h264_videotoolbox":
                    hw_flags = ["-q:v", "65", "-allow_sw", "1"] + hw_flags
                elif "nvenc" in hw_codec:
                    hw_flags = ["-preset", "p4", "-rc", "vbr", "-cq", "18"] + hw_flags
                elif "qsv" in hw_codec:
                    hw_flags = ["-preset", "medium", "-global_quality", "18"] + hw_flags
                pix_fmt = "nv12" if hw_codec != "h264_videotoolbox" else "nv12"
                return _OutputPreset(
                    name=f"{preset.name}_auto_hw",
                    codec=hw_codec,
                    pixel_format=pix_fmt,
                    audio_codec=preset.audio_codec,
                    audio_bitrate=preset.audio_bitrate,
                    container=preset.container,
                    extra_flags=hw_flags,
                )

    return preset


class FFmpegEncoder:
    """Encodes rendered frames to video using FFmpeg subprocess.

    Receives raw BGRA frames via stdin pipe and produces the output
    video file. All subprocess calls use shell=False for security.
    """

    def __init__(self) -> None:
        """Initialize the encoder and locate FFmpeg."""
        self._ffmpeg_path: str = _find_ffmpeg()
        logger.debug("ffmpeg_found", path=self._ffmpeg_path)

    def encode(
        self,
        frame_iter: Iterator[np.ndarray],
        audio: np.ndarray | None,
        output: Path,
        preset: OutputPreset,
        width: int,
        height: int,
        fps: int,
        audio_sample_rate: int = 48000,
        audio_channels: int = 2,
    ) -> Path:
        """Encode frames to a video file, optionally with audio.

        Args:
            frame_iter: Iterator yielding BGRA numpy arrays.
            audio: Interleaved int32 audio data, or None for no audio.
            output: Output file path.
            preset: Output preset configuration.
            width: Frame width.
            height: Frame height.
            fps: Frames per second.
            audio_sample_rate: Audio sample rate in Hz.
            audio_channels: Number of audio channels (2=stereo, 6=5.1).

        Returns:
            Path to the output file.

        Raises:
            RuntimeError: If FFmpeg exits with an error.
        """
        output_str = str(output.resolve())

        # Use available CPU threads for encoding (cap at 8)
        threads = str(min(os.cpu_count() or 2, 8))

        # Write audio to a temp WAV file if provided
        audio_wav_path: str | None = None
        audio_tmpfile: Any = None
        if audio is not None and len(audio) > 0:
            audio_tmpfile = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio_wav_path = audio_tmpfile.name
            _write_wav(audio_tmpfile, audio, audio_sample_rate, audio_channels)
            audio_tmpfile.close()

        cmd = [
            self._ffmpeg_path,
            "-y",  # overwrite output
            "-threads",
            threads,
            # Input: raw video from pipe
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
        ]

        # Add audio input if available
        if audio_wav_path is not None:
            cmd.extend(["-i", audio_wav_path])

        cmd.extend(
            [
                # Chroma scaling for text/graphics
                "-sws_flags",
                "bilinear+accurate_rnd",
                # Output codec
                "-c:v",
                preset.codec,
                "-pix_fmt",
                preset.pixel_format,
                "-threads",
                threads,
            ]
        )

        # Add CRF or bitrate
        if preset.crf is not None:
            cmd.extend(["-crf", str(preset.crf)])
        if preset.bitrate is not None:
            cmd.extend(["-b:v", preset.bitrate])

        # Add extra flags
        cmd.extend(preset.extra_flags)

        # Add audio encoding flags
        if audio_wav_path is not None:
            cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ac", str(audio_channels)])

        # Output file
        cmd.append(output_str)

        logger.info("ffmpeg_start", output=output_str, codec=preset.codec)

        process = subprocess.Popen(  # noqa: S603
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )

        frame_count = 0
        try:
            if process.stdin is None:
                msg = "FFmpeg stdin pipe not available"
                raise RuntimeError(msg)
            stdin = process.stdin
            for frame in frame_iter:
                # Ensure contiguous memory for efficient pipe writes
                if not frame.flags["C_CONTIGUOUS"]:
                    frame = np.ascontiguousarray(frame)
                stdin.write(frame.data)
                frame_count += 1
            stdin.close()
        except BrokenPipeError:
            pass

        process.wait()
        _stdout = process.stdout.read() if process.stdout else b""
        stderr = process.stderr.read() if process.stderr else b""

        # Clean up temp audio file
        if audio_wav_path is not None:
            try:
                os.unlink(audio_wav_path)
            except OSError:
                pass

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")
            msg = f"FFmpeg failed with return code {process.returncode}: {error_msg}"
            raise RuntimeError(msg)

        logger.info(
            "ffmpeg_complete",
            output=output_str,
            frames=frame_count,
        )
        return output

    def encode_frame_sequence(
        self,
        frame_iter: Iterator[np.ndarray],
        output_dir: Path,
        width: int,
        height: int,
        fps: int,
        fmt: str = "png",
    ) -> Path:
        """Encode frames as an image sequence to a directory.

        Args:
            frame_iter: Iterator yielding BGRA numpy arrays.
            output_dir: Directory to write frame files to.
            width: Frame width.
            height: Frame height.
            fps: Frames per second (stored in metadata if supported).
            fmt: Image format ("png" or "exr").

        Returns:
            Path to the output directory.

        Raises:
            RuntimeError: If FFmpeg exits with an error.
            ValueError: If format is not supported.
        """
        if fmt not in ("png", "exr"):
            msg = f"Unsupported frame sequence format: {fmt}. Use 'png' or 'exr'."
            raise ValueError(msg)

        output_dir.mkdir(parents=True, exist_ok=True)
        pattern = str(output_dir / f"frame_%06d.{fmt}")

        if fmt == "png":
            codec = "png"
            pix_fmt = "rgba"
        else:
            codec = "exr"
            pix_fmt = "gbrpf32le"

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-c:v",
            codec,
            "-pix_fmt",
            pix_fmt,
            pattern,
        ]

        logger.info("ffmpeg_frame_seq_start", output_dir=str(output_dir), fmt=fmt)

        process = subprocess.Popen(  # noqa: S603
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )

        frame_count = 0
        try:
            if process.stdin is None:
                msg = "FFmpeg stdin pipe not available"
                raise RuntimeError(msg)
            for frame in frame_iter:
                process.stdin.write(frame.tobytes())
                frame_count += 1
            process.stdin.close()
        except BrokenPipeError:
            pass

        process.wait()
        _stdout = process.stdout.read() if process.stdout else b""
        stderr = process.stderr.read() if process.stderr else b""

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")
            msg = f"FFmpeg frame sequence failed with code {process.returncode}: {error_msg}"
            raise RuntimeError(msg)

        logger.info(
            "ffmpeg_frame_seq_complete",
            output_dir=str(output_dir),
            frames=frame_count,
            fmt=fmt,
        )
        return output_dir

    def encode_frame_to_png(
        self,
        frame: np.ndarray,
        output: Path,
    ) -> Path:
        """Encode a single frame to PNG.

        Args:
            frame: BGRA numpy array.
            output: Output PNG path.

        Returns:
            Path to the output PNG file.
        """
        from PIL import Image

        # Convert BGRA to RGBA
        rgba = frame.copy()
        rgba[:, :, 0] = frame[:, :, 2]
        rgba[:, :, 2] = frame[:, :, 0]

        img = Image.fromarray(rgba, "RGBA")
        img.save(str(output))
        return output
