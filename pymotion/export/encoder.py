"""FFmpegEncoder — secure FFmpeg subprocess wrapper for video encoding.

Wraps FFmpeg with security constraints: shell=False, validated paths,
explicit argument lists, no user input in command strings.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from pymotion.export.presets import OutputPreset
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


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
    ) -> Path:
        """Encode frames to a video file.

        Args:
            frame_iter: Iterator yielding BGRA numpy arrays.
            audio: Audio data (None for no audio in Phase 0.1).
            output: Output file path.
            preset: Output preset configuration.
            width: Frame width.
            height: Frame height.
            fps: Frames per second.

        Returns:
            Path to the output file.

        Raises:
            RuntimeError: If FFmpeg exits with an error.
        """
        output_str = str(output.resolve())

        # Use available CPU threads for encoding (cap at 8)
        threads = str(min(os.cpu_count() or 2, 8))

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
            # High-quality chroma scaling for text/graphics
            "-sws_flags",
            "lanczos+accurate_rnd+full_chroma_int",
            # Output codec
            "-c:v",
            preset.codec,
            "-pix_fmt",
            preset.pixel_format,
            "-threads",
            threads,
        ]

        # Add CRF or bitrate
        if preset.crf is not None:
            cmd.extend(["-crf", str(preset.crf)])
        if preset.bitrate is not None:
            cmd.extend(["-b:v", preset.bitrate])

        # Add extra flags
        cmd.extend(preset.extra_flags)

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
