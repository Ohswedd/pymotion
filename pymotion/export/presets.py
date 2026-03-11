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
    crf=10,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-preset",
        "medium",
        "-tune",
        "animation",
        "-x264-params",
        "no-dct-decimate=1:no-fast-pskip=1",
        "-movflags",
        "+faststart",
    ],
)

H264_4K = OutputPreset(
    name="h264_4k",
    codec="libx264",
    pixel_format="yuv420p",
    crf=10,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-preset",
        "medium",
        "-tune",
        "animation",
        "-x264-params",
        "no-dct-decimate=1:no-fast-pskip=1",
        "-movflags",
        "+faststart",
    ],
)

H265_1080P = OutputPreset(
    name="h265_1080p",
    codec="libx265",
    pixel_format="yuv420p",
    crf=16,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=["-preset", "medium", "-movflags", "+faststart"],
)

H265_4K = OutputPreset(
    name="h265_4k",
    codec="libx265",
    pixel_format="yuv420p",
    crf=16,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=["-preset", "medium", "-movflags", "+faststart"],
)

WEBM_1080P = OutputPreset(
    name="webm_1080p",
    codec="libvpx-vp9",
    pixel_format="yuv420p",
    crf=31,
    audio_codec="libopus",
    audio_bitrate="128k",
    container="webm",
)

INSTAGRAM_REEL = OutputPreset(
    name="instagram_reel",
    codec="libx264",
    pixel_format="yuv420p",
    bitrate="8M",
    audio_codec="aac",
    audio_bitrate="192k",
    container="mp4",
    extra_flags=["-preset", "medium", "-tune", "animation", "-s", "1080x1920"],
)

YOUTUBE_1080P = OutputPreset(
    name="youtube_1080p",
    codec="libx264",
    pixel_format="yuv420p",
    crf=10,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-preset",
        "medium",
        "-tune",
        "animation",
        "-x264-params",
        "no-dct-decimate=1:no-fast-pskip=1",
        "-movflags",
        "+faststart",
    ],
)

YOUTUBE_4K = OutputPreset(
    name="youtube_4k",
    codec="libx265",
    pixel_format="yuv420p",
    crf=14,
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=["-preset", "medium", "-movflags", "+faststart"],
)

TIKTOK = OutputPreset(
    name="tiktok",
    codec="libx264",
    pixel_format="yuv420p",
    bitrate="8M",
    audio_codec="aac",
    audio_bitrate="192k",
    container="mp4",
    extra_flags=["-preset", "medium", "-tune", "animation", "-s", "1080x1920"],
)

AV1_1080P = OutputPreset(
    name="av1_1080p",
    codec="libaom-av1",
    pixel_format="yuv420p",
    crf=28,
    audio_codec="libopus",
    audio_bitrate="128k",
    container="webm",
    extra_flags=["-cpu-used", "4", "-row-mt", "1"],
)

PRORES_4444 = OutputPreset(
    name="prores_4444",
    codec="prores_ks",
    pixel_format="yuva444p10le",
    audio_codec="pcm_s24le",
    audio_bitrate="0",
    container="mov",
    extra_flags=["-profile:v", "4"],
)

PRORES_HQ = OutputPreset(
    name="prores_hq",
    codec="prores_ks",
    pixel_format="yuv422p10le",
    audio_codec="pcm_s24le",
    audio_bitrate="0",
    container="mov",
    extra_flags=["-profile:v", "3"],
)

DNXHD_1080P = OutputPreset(
    name="dnxhd_1080p",
    codec="dnxhd",
    pixel_format="yuv422p",
    bitrate="185M",
    audio_codec="pcm_s24le",
    audio_bitrate="0",
    container="mov",
)

GIF_1080P = OutputPreset(
    name="gif_1080p",
    codec="gif",
    pixel_format="pal8",
    audio_codec="none",
    audio_bitrate="0",
    container="gif",
    extra_flags=[
        "-vf",
        "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse=dither=sierra2_4a",
    ],
)

FRAME_SEQUENCE_PNG = OutputPreset(
    name="frame_sequence_png",
    codec="png",
    pixel_format="rgba",
    audio_codec="none",
    audio_bitrate="0",
    container="image2",
)

# ── Hardware-accelerated encoding presets ──────────────────────────────

H264_NVENC = OutputPreset(
    name="h264_nvenc",
    codec="h264_nvenc",
    pixel_format="yuv420p",
    bitrate="8M",
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-preset",
        "p4",
        "-rc",
        "vbr",
        "-cq",
        "18",
        "-movflags",
        "+faststart",
    ],
)

H265_NVENC = OutputPreset(
    name="h265_nvenc",
    codec="hevc_nvenc",
    pixel_format="yuv420p",
    bitrate="8M",
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-preset",
        "p4",
        "-rc",
        "vbr",
        "-cq",
        "20",
        "-movflags",
        "+faststart",
    ],
)

H264_QSV = OutputPreset(
    name="h264_qsv",
    codec="h264_qsv",
    pixel_format="nv12",
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-preset",
        "medium",
        "-global_quality",
        "18",
        "-movflags",
        "+faststart",
    ],
)

H264_AMF = OutputPreset(
    name="h264_amf",
    codec="h264_amf",
    pixel_format="nv12",
    audio_codec="aac",
    audio_bitrate="320k",
    container="mp4",
    extra_flags=[
        "-quality",
        "balanced",
        "-rc",
        "vbr_peak",
        "-movflags",
        "+faststart",
    ],
)

_PRESET_REGISTRY: dict[str, OutputPreset] = {
    "h264_1080p": H264_1080P,
    "h264_4k": H264_4K,
    "h265_1080p": H265_1080P,
    "h265_4k": H265_4K,
    "av1_1080p": AV1_1080P,
    "prores_4444": PRORES_4444,
    "prores_hq": PRORES_HQ,
    "dnxhd_1080p": DNXHD_1080P,
    "webm_1080p": WEBM_1080P,
    "gif_1080p": GIF_1080P,
    "instagram_reel": INSTAGRAM_REEL,
    "youtube_1080p": YOUTUBE_1080P,
    "youtube_4k": YOUTUBE_4K,
    "tiktok": TIKTOK,
    "frame_sequence_png": FRAME_SEQUENCE_PNG,
    # Hardware-accelerated presets
    "h264_nvenc": H264_NVENC,
    "h265_nvenc": H265_NVENC,
    "h264_qsv": H264_QSV,
    "h264_amf": H264_AMF,
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
