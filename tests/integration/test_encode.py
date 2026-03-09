"""Integration tests for encoding pipeline — composition to MP4 and all presets."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pymotion.clip.color import ColorClip
from pymotion.clip.shape import ShapeClip
from pymotion.composition import Composition
from pymotion.export.presets import get_preset


@pytest.fixture
def has_ffmpeg() -> bool:
    """Check if FFmpeg is available on the system."""
    return shutil.which("ffmpeg") is not None


class TestEncode:
    """Test end-to-end encoding to MP4."""

    def test_render_to_mp4(self, tmp_path: Path, has_ffmpeg: bool) -> None:
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        comp = Composition(width=320, height=240, fps=30, duration=10)
        comp.add(ColorClip("#1A1A2E").set_duration(10))

        output = tmp_path / "test.mp4"
        result = comp.render(str(output), preset="h264_1080p")

        assert result.exists()
        assert result.stat().st_size > 0

    def test_render_with_shapes(self, tmp_path: Path, has_ffmpeg: bool) -> None:
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        comp = Composition(width=320, height=240, fps=30, duration=10)
        comp.add(
            ColorClip("#1A1A2E").set_duration(10),
            ShapeClip.circle(cx=160, cy=120, r=50, fill="#E94560").set_duration(10),
        )

        output = tmp_path / "shapes.mp4"
        result = comp.render(str(output), preset="h264_1080p")

        assert result.exists()
        assert result.stat().st_size > 0

    def test_export_frame_png(self, tmp_path: Path) -> None:
        comp = Composition(width=320, height=240, fps=30, duration=10)
        comp.add(ColorClip("#FF0000").set_duration(10))

        output = tmp_path / "frame.png"
        result = comp.export_frame(0, str(output))

        assert result.exists()
        assert result.stat().st_size > 0

    def test_render_exit_criteria(self, tmp_path: Path, has_ffmpeg: bool) -> None:
        """Test the Phase 0.1 exit criteria script."""
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        comp = Composition(width=320, height=240, fps=30, duration=10)
        comp.add(
            ColorClip("#1A1A2E").set_duration(10),
            ShapeClip.circle(cx=160, cy=120, r=50, fill="#E94560").set_duration(10),
        )
        comp.add(
            ShapeClip.rect(x=10, y=10, w=40, h=20, fill="#0F3460").set_duration(10),
        )

        output = tmp_path / "test_output.mp4"
        result = comp.render(str(output), preset="h264_1080p")

        assert result.exists()
        assert result.stat().st_size > 0

    @pytest.mark.parametrize(
        "preset_name",
        [
            "h264_1080p",
            "h265_1080p",
            "webm_1080p",
            "youtube_1080p",
        ],
    )
    def test_render_presets(self, tmp_path: Path, has_ffmpeg: bool, preset_name: str) -> None:
        """Test rendering with various presets."""
        if not has_ffmpeg:
            pytest.skip("FFmpeg not installed")

        preset = get_preset(preset_name)
        ext = preset.container
        comp = Composition(width=320, height=240, fps=30, duration=5)
        comp.add(ColorClip("#2A2A4E").set_duration(5))

        output = tmp_path / f"test_{preset_name}.{ext}"
        result = comp.render(str(output), preset=preset_name)

        assert result.exists()
        assert result.stat().st_size > 0
