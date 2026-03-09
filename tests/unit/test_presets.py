"""Tests for export presets — all 15 presets registered."""

from __future__ import annotations

import pytest

from pymotion.export.presets import (
    _PRESET_REGISTRY,
    AV1_1080P,
    DNXHD_1080P,
    FRAME_SEQUENCE_PNG,
    GIF_1080P,
    PRORES_4444,
    PRORES_HQ,
    OutputPreset,
    get_preset,
)


class TestPresetRegistry:
    """Test preset registry completeness and lookup."""

    def test_15_presets_registered(self) -> None:
        assert len(_PRESET_REGISTRY) == 15

    @pytest.mark.parametrize(
        "name",
        [
            "h264_1080p",
            "h264_4k",
            "h265_1080p",
            "h265_4k",
            "av1_1080p",
            "prores_4444",
            "prores_hq",
            "dnxhd_1080p",
            "webm_1080p",
            "gif_1080p",
            "instagram_reel",
            "youtube_1080p",
            "youtube_4k",
            "tiktok",
            "frame_sequence_png",
        ],
    )
    def test_all_presets_exist(self, name: str) -> None:
        preset = get_preset(name)
        assert isinstance(preset, OutputPreset)
        assert preset.name == name

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent")


class TestNewPresets:
    """Test the 6 newly added presets."""

    def test_av1_codec(self) -> None:
        assert AV1_1080P.codec == "libaom-av1"
        assert AV1_1080P.crf == 28
        assert AV1_1080P.container == "webm"

    def test_prores_4444(self) -> None:
        assert PRORES_4444.codec == "prores_ks"
        assert PRORES_4444.pixel_format == "yuva444p10le"
        assert PRORES_4444.container == "mov"
        assert "-profile:v" in PRORES_4444.extra_flags
        assert "4" in PRORES_4444.extra_flags

    def test_prores_hq(self) -> None:
        assert PRORES_HQ.codec == "prores_ks"
        assert PRORES_HQ.pixel_format == "yuv422p10le"
        assert "3" in PRORES_HQ.extra_flags

    def test_dnxhd(self) -> None:
        assert DNXHD_1080P.codec == "dnxhd"
        assert DNXHD_1080P.bitrate == "185M"
        assert DNXHD_1080P.container == "mov"

    def test_gif(self) -> None:
        assert GIF_1080P.codec == "gif"
        assert GIF_1080P.pixel_format == "pal8"
        assert GIF_1080P.container == "gif"

    def test_frame_sequence_png(self) -> None:
        assert FRAME_SEQUENCE_PNG.codec == "png"
        assert FRAME_SEQUENCE_PNG.pixel_format == "rgba"
        assert FRAME_SEQUENCE_PNG.container == "image2"
