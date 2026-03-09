"""OutputPreset definitions for common video encoding targets.

Each preset defines FFmpeg arguments for a specific output format and quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OutputPreset:
    """Configuration for a video output format.

    Args:
        name: Human-readable preset name.
        codec: FFmpeg codec name (e.g., "libx264").
        pixel_format: FFmpeg pixel format (e.g., "yuv420p").
        crf: Constant rate factor for quality-based encoding.
        bitrate: Target bitrate (e.g., "8M") for CBR/VBR.
        audio_codec: Audio codec name.
        audio_bitrate: Audio bitrate (e.g., "320k").
        container: Output container format.
        extra_flags: Additional FFmpeg flags.
    """

    name: str
    codec: str
    pixel_format: str
    crf: int | None = None
    bitrate: str | None = None
    audio_codec: str = "aac"
    audio_bitrate: str = "320k"
    container: str = "mp4"
    extra_flags: list[str] = field(default_factory=list)


# Built-in presets
H264_1080P = OutputPreset(
    name="h264_1080p",
    codec="libx264",
    pixel_format="yuv420p",
    crf=18,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=["-preset", "medium"],
)

H264_4K = OutputPreset(
    name="h264_4k",
    codec="libx264",
    pixel_format="yuv420p",
    crf=18,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=["-preset", "medium"],
)

_PRESET_REGISTRY: dict[str, OutputPreset] = {
    "h264_1080p": H264_1080P,
    "h264_4k": H264_4K,
}


def get_preset(name: str) -> OutputPreset:
    """Look up an output preset by name.

    Args:
        name: Preset name.

    Returns:
        The OutputPreset configuration.

    Raises:
        ValueError: If the preset name is not found.
    """
    preset = _PRESET_REGISTRY.get(name)
    if preset is None:
        available = ", ".join(sorted(_PRESET_REGISTRY.keys()))
        msg = f"Unknown preset '{name}'. Available: {available}"
        raise ValueError(msg)
    return preset
