"""Tests for hardware encoding presets and auto-detection."""

from __future__ import annotations

from pymotion.export.encoder import (
    detect_hardware_encoders,
    resolve_preset_with_fallback,
)
from pymotion.export.presets import (
    H264_AMF,
    H264_NVENC,
    H264_QSV,
    H265_NVENC,
    get_preset,
)


class TestHardwarePresets:
    """Tests for hardware encoding preset definitions."""

    def test_h264_nvenc_preset_exists(self) -> None:
        preset = get_preset("h264_nvenc")
        assert preset.codec == "h264_nvenc"
        assert preset.container == "mp4"

    def test_h265_nvenc_preset_exists(self) -> None:
        preset = get_preset("h265_nvenc")
        assert preset.codec == "hevc_nvenc"
        assert preset.container == "mp4"

    def test_h264_qsv_preset_exists(self) -> None:
        preset = get_preset("h264_qsv")
        assert preset.codec == "h264_qsv"

    def test_h264_amf_preset_exists(self) -> None:
        preset = get_preset("h264_amf")
        assert preset.codec == "h264_amf"

    def test_nvenc_preset_has_vbr_flags(self) -> None:
        assert "-rc" in H264_NVENC.extra_flags
        assert "vbr" in H264_NVENC.extra_flags

    def test_h265_nvenc_has_cq_flag(self) -> None:
        assert "-cq" in H265_NVENC.extra_flags

    def test_qsv_preset_pixel_format(self) -> None:
        assert H264_QSV.pixel_format == "nv12"

    def test_amf_preset_quality(self) -> None:
        assert "-quality" in H264_AMF.extra_flags
        assert "balanced" in H264_AMF.extra_flags

    def test_preset_constants_match_registry(self) -> None:
        assert get_preset("h264_nvenc") is H264_NVENC
        assert get_preset("h265_nvenc") is H265_NVENC
        assert get_preset("h264_qsv") is H264_QSV
        assert get_preset("h264_amf") is H264_AMF


class TestHardwareDetection:
    """Tests for hardware encoder auto-detection."""

    def test_detect_returns_list(self) -> None:
        result = detect_hardware_encoders()
        assert isinstance(result, list)
        # All entries should be strings
        for codec in result:
            assert isinstance(codec, str)

    def test_detect_only_known_codecs(self) -> None:
        known = {
            "h264_videotoolbox",
            "hevc_videotoolbox",
            "h264_nvenc",
            "hevc_nvenc",
            "h264_qsv",
            "hevc_qsv",
            "h264_amf",
            "hevc_amf",
        }
        result = detect_hardware_encoders()
        for codec in result:
            assert codec in known


class TestResolvePresetWithFallback:
    """Tests for preset resolution with hardware fallback."""

    def test_software_preset_resolves(self) -> None:
        preset = resolve_preset_with_fallback("h264_1080p")
        # May auto-upgrade to hardware encoder on supported systems
        assert preset.codec in (
            "libx264",
            "h264_videotoolbox",
            "h264_nvenc",
            "h264_qsv",
            "h264_amf",
        )

    def test_software_preset_no_hardware(self) -> None:
        preset = resolve_preset_with_fallback("h264_1080p", try_hardware=False)
        assert preset.codec == "libx264"

    def test_nvenc_falls_back_if_unavailable(self) -> None:
        """On systems without NVENC, should fall back to software h264."""
        preset = resolve_preset_with_fallback("h264_nvenc")
        # Either NVENC is available (codec="h264_nvenc") or fell back (codec="libx264")
        assert preset.codec in ("h264_nvenc", "libx264")

    def test_h265_nvenc_falls_back_if_unavailable(self) -> None:
        preset = resolve_preset_with_fallback("h265_nvenc")
        assert preset.codec in ("hevc_nvenc", "libx265")

    def test_qsv_falls_back_if_unavailable(self) -> None:
        preset = resolve_preset_with_fallback("h264_qsv")
        assert preset.codec in ("h264_qsv", "libx264")

    def test_amf_falls_back_if_unavailable(self) -> None:
        preset = resolve_preset_with_fallback("h264_amf")
        assert preset.codec in ("h264_amf", "libx264")

    def test_unknown_preset_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Unknown preset"):
            resolve_preset_with_fallback("nonexistent_preset")
