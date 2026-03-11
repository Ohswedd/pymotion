"""Captions & subtitles — auto-captions, SRT/VTT/ASS import/export.

Provides caption generation from audio (via Whisper), subtitle file
parsing and rendering, and export to SRT/VTT formats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from pymotion.security.validation import validate_path
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

#: Supported caption style presets.
CaptionStyle = Literal["netflix", "youtube", "tiktok", "karaoke"]


@dataclass
class CaptionSegment:
    """A single timed caption segment.

    Args:
        text: The caption text.
        start_sec: Start time in seconds.
        end_sec: End time in seconds.
        words: Optional per-word timestamps for karaoke-style display.
    """

    text: str
    start_sec: float
    end_sec: float
    words: list[WordTimestamp] | None = None


@dataclass
class WordTimestamp:
    """Word-level timestamp for karaoke-style captions.

    Args:
        word: The individual word text.
        start_sec: Word start time in seconds.
        end_sec: Word end time in seconds.
    """

    word: str
    start_sec: float
    end_sec: float


# ── Style Definitions ──────────────────────────────────────────────────

_CAPTION_STYLES: dict[str, dict[str, Any]] = {
    "netflix": {
        "font_size": 42,
        "font_family": "Helvetica",
        "color": Color(1.0, 1.0, 1.0, 1.0),
        "background": Color(0.0, 0.0, 0.0, 0.75),
        "padding": 8,
        "position": "bottom",
    },
    "youtube": {
        "font_size": 36,
        "font_family": "Roboto",
        "color": Color(1.0, 1.0, 1.0, 1.0),
        "background": Color(0.0, 0.0, 0.0, 0.6),
        "padding": 6,
        "position": "bottom",
    },
    "tiktok": {
        "font_size": 48,
        "font_family": "Helvetica",
        "color": Color(1.0, 1.0, 1.0, 1.0),
        "background": Color(0.0, 0.0, 0.0, 0.0),
        "padding": 0,
        "position": "center",
        "stroke_color": Color(0.0, 0.0, 0.0, 1.0),
        "stroke_width": 3,
    },
    "karaoke": {
        "font_size": 44,
        "font_family": "Helvetica",
        "color": Color(0.6, 0.6, 0.6, 1.0),
        "highlight_color": Color(1.0, 1.0, 0.0, 1.0),
        "background": Color(0.0, 0.0, 0.0, 0.5),
        "padding": 8,
        "position": "bottom",
    },
}


def get_caption_style(name: str) -> dict[str, Any]:
    """Get a caption style preset by name.

    Args:
        name: Style name (``"netflix"``, ``"youtube"``, ``"tiktok"``,
              ``"karaoke"``).

    Returns:
        Style configuration dictionary.

    Raises:
        ValueError: If the style name is not recognized.
    """
    if name not in _CAPTION_STYLES:
        valid = ", ".join(sorted(_CAPTION_STYLES.keys()))
        msg = f"Unknown caption style '{name}'. Valid styles: {valid}"
        raise ValueError(msg)
    return dict(_CAPTION_STYLES[name])


# ── Subtitle Parsing ──────────────────────────────────────────────────


def _parse_srt_time(time_str: str) -> float:
    """Parse SRT timestamp to seconds.

    Args:
        time_str: Time string in format ``HH:MM:SS,mmm``.

    Returns:
        Time in seconds.
    """
    time_str = time_str.strip().replace(",", ".")
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    return 0.0


def _parse_vtt_time(time_str: str) -> float:
    """Parse VTT timestamp to seconds.

    Args:
        time_str: Time string in format ``HH:MM:SS.mmm`` or ``MM:SS.mmm``.

    Returns:
        Time in seconds.
    """
    time_str = time_str.strip()
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    if len(parts) == 2:
        m, s = float(parts[0]), float(parts[1])
        return m * 60 + s
    return 0.0


def parse_srt(text: str) -> list[CaptionSegment]:
    """Parse SRT subtitle text into caption segments.

    Args:
        text: Full SRT file content.

    Returns:
        List of CaptionSegment instances.
    """
    segments: list[CaptionSegment] = []
    blocks = re.split(r"\n\n+", text.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # Line 0: index, Line 1: timestamps, Lines 2+: text
        time_line = lines[1]
        match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            time_line,
        )
        if not match:
            continue
        start = _parse_srt_time(match.group(1))
        end = _parse_srt_time(match.group(2))
        caption_text = "\n".join(lines[2:])
        segments.append(CaptionSegment(text=caption_text, start_sec=start, end_sec=end))

    logger.debug("srt_parsed", segments=len(segments))
    return segments


def parse_vtt(text: str) -> list[CaptionSegment]:
    """Parse WebVTT subtitle text into caption segments.

    Args:
        text: Full VTT file content.

    Returns:
        List of CaptionSegment instances.
    """
    segments: list[CaptionSegment] = []
    blocks = re.split(r"\n\n+", text.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        # Find the line with timestamps
        for i, line in enumerate(lines):
            match = re.match(
                r"(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})"
                r"\s*-->\s*"
                r"(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})",
                line,
            )
            if match:
                start = _parse_vtt_time(match.group(1))
                end = _parse_vtt_time(match.group(2))
                caption_text = "\n".join(lines[i + 1 :])
                if caption_text:
                    segments.append(CaptionSegment(text=caption_text, start_sec=start, end_sec=end))
                break

    logger.debug("vtt_parsed", segments=len(segments))
    return segments


def parse_ass(text: str) -> list[CaptionSegment]:
    """Parse ASS/SSA subtitle text into caption segments.

    Extracts dialogue events and converts to CaptionSegment instances.

    Args:
        text: Full ASS/SSA file content.

    Returns:
        List of CaptionSegment instances.
    """
    segments: list[CaptionSegment] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("Dialogue:"):
            continue

        # Format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue

        start_str = parts[1].strip()
        end_str = parts[2].strip()
        caption_text = parts[9].strip()

        # Remove ASS formatting tags
        caption_text = re.sub(r"\{[^}]*\}", "", caption_text)
        # Convert \N to newlines
        caption_text = caption_text.replace("\\N", "\n")

        start = _parse_ass_time(start_str)
        end = _parse_ass_time(end_str)

        if caption_text:
            segments.append(CaptionSegment(text=caption_text, start_sec=start, end_sec=end))

    logger.debug("ass_parsed", segments=len(segments))
    return segments


def _parse_ass_time(time_str: str) -> float:
    """Parse ASS timestamp to seconds.

    Args:
        time_str: Time string in format ``H:MM:SS.cc`` (centiseconds).

    Returns:
        Time in seconds.
    """
    parts = time_str.split(":")
    if len(parts) == 3:
        h = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s
    return 0.0


def import_subtitles(
    path: str | Path,
    base_dirs: list[Path] | None = None,
) -> list[CaptionSegment]:
    """Import subtitles from a file (SRT, VTT, or ASS/SSA).

    Detects format from file extension and parses accordingly.

    Args:
        path: Path to the subtitle file.
        base_dirs: Allowed directories for path validation.

    Returns:
        List of CaptionSegment instances.

    Raises:
        ValueError: If the file format is not supported.
        FileNotFoundError: If the file doesn't exist.
    """
    file_path = Path(path)
    if base_dirs:
        file_path = validate_path(file_path, base_dirs)
    else:
        file_path = file_path.resolve()
        if not file_path.exists():
            msg = f"Subtitle file not found: {file_path}"
            raise FileNotFoundError(msg)

    text = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()

    if suffix == ".srt":
        return parse_srt(text)
    if suffix == ".vtt":
        return parse_vtt(text)
    if suffix in (".ass", ".ssa"):
        return parse_ass(text)

    msg = f"Unsupported subtitle format: {suffix}. Supported: .srt, .vtt, .ass, .ssa"
    raise ValueError(msg)


# ── Subtitle Export ───────────────────────────────────────────────────


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp ``HH:MM:SS,mmm``.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted timestamp string.
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def _format_vtt_time(seconds: float) -> str:
    """Format seconds to VTT timestamp ``HH:MM:SS.mmm``.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted timestamp string.
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d}.{ms:03d}"


def export_subtitles(
    segments: list[CaptionSegment],
    path: str | Path,
    fmt: str = "srt",
) -> None:
    """Export caption segments to a subtitle file.

    Args:
        segments: List of caption segments.
        path: Output file path.
        fmt: Output format (``"srt"`` or ``"vtt"``).

    Raises:
        ValueError: If the format is not supported.
    """
    output = Path(path)

    if fmt == "srt":
        lines: list[str] = []
        for i, seg in enumerate(segments, 1):
            lines.append(str(i))
            lines.append(f"{_format_srt_time(seg.start_sec)} --> {_format_srt_time(seg.end_sec)}")
            lines.append(seg.text)
            lines.append("")
        output.write_text("\n".join(lines), encoding="utf-8")
    elif fmt == "vtt":
        lines = ["WEBVTT", ""]
        for seg in segments:
            lines.append(f"{_format_vtt_time(seg.start_sec)} --> {_format_vtt_time(seg.end_sec)}")
            lines.append(seg.text)
            lines.append("")
        output.write_text("\n".join(lines), encoding="utf-8")
    else:
        msg = f"Unsupported export format: {fmt}. Supported: srt, vtt"
        raise ValueError(msg)

    logger.debug("subtitles_exported", path=str(output), format=fmt, segments=len(segments))


# ── SubtitleClip ─────────────────────────────────────────────────────


@dataclass
class SubtitleClip:
    """Render subtitles from an SRT file as a clip overlay.

    Parses the SRT file and renders the appropriate caption text for
    each frame based on the timeline.

    Args:
        srt_path: Path to the SRT subtitle file.
        style: Caption style preset name.
        fps: Frames per second for time-to-frame conversion.
    """

    srt_path: str | Path
    style: str = "netflix"
    fps: int = 30
    _segments: list[CaptionSegment] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Load and parse the subtitle file."""
        self._segments = import_subtitles(self.srt_path)

    @property
    def segments(self) -> list[CaptionSegment]:
        """Get the parsed caption segments."""
        return self._segments

    def get_text_at(self, time_sec: float) -> str | None:
        """Get the caption text visible at a given time.

        Args:
            time_sec: Time in seconds.

        Returns:
            Caption text or None if no caption is active.
        """
        for seg in self._segments:
            if seg.start_sec <= time_sec < seg.end_sec:
                return seg.text
        return None

    def get_text_at_frame(self, frame: int) -> str | None:
        """Get the caption text visible at a given frame.

        Args:
            frame: Frame number.

        Returns:
            Caption text or None if no caption is active.
        """
        return self.get_text_at(frame / self.fps)


# ── AutoCaptions (Whisper) ───────────────────────────────────────────


@dataclass
class AutoCaptions:
    """Auto-generate captions from audio using OpenAI Whisper.

    Requires the ``openai-whisper`` package (optional dependency).
    Transcribes audio and produces word-level timestamps for animated
    subtitle overlays.

    Args:
        audio: Float64 audio samples or path to audio file.
        model: Whisper model size (``"tiny"``, ``"base"``, ``"small"``,
               ``"medium"``, ``"large"``).
        style: Caption style preset name.
        sample_rate: Audio sample rate (used when audio is an ndarray).
    """

    audio: np.ndarray | str | Path
    model: str = "base"
    style: str = "netflix"
    sample_rate: int = 16000
    _segments: list[CaptionSegment] = field(default_factory=list, repr=False)

    def transcribe(self) -> list[CaptionSegment]:
        """Run Whisper transcription and return caption segments.

        Returns:
            List of CaptionSegment instances with word-level timestamps
            when available.

        Raises:
            ImportError: If ``openai-whisper`` is not installed.
        """
        try:
            import whisper  # noqa: PLC0415
        except ImportError:
            msg = (
                "openai-whisper is required for AutoCaptions. "
                "Install it with: pip install openai-whisper"
            )
            raise ImportError(msg)  # noqa: B904

        whisper_model: Any = whisper.load_model(self.model)

        if isinstance(self.audio, np.ndarray):
            # Whisper expects float32 mono at 16kHz
            audio_data = self.audio.astype(np.float32)
            if audio_data.ndim == 2:
                audio_data = audio_data.mean(axis=1)
            result: dict[str, Any] = whisper_model.transcribe(audio_data, word_timestamps=True)
        else:
            audio_path = str(Path(self.audio).resolve())
            result = whisper_model.transcribe(audio_path, word_timestamps=True)

        segments: list[CaptionSegment] = []
        for seg in result.get("segments", []):
            words: list[WordTimestamp] = []
            for w in seg.get("words", []):
                words.append(
                    WordTimestamp(
                        word=w.get("word", "").strip(),
                        start_sec=float(w.get("start", 0)),
                        end_sec=float(w.get("end", 0)),
                    )
                )
            segments.append(
                CaptionSegment(
                    text=seg.get("text", "").strip(),
                    start_sec=float(seg.get("start", 0)),
                    end_sec=float(seg.get("end", 0)),
                    words=words if words else None,
                )
            )

        self._segments = segments
        logger.debug("whisper_transcribed", segments=len(segments), model=self.model)
        return segments

    @property
    def segments(self) -> list[CaptionSegment]:
        """Get the transcribed caption segments."""
        return self._segments
