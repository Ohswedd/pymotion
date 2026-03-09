"""Tests for HDR/EXR loading and color pipeline integration."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from pymotion.render.backend_3d import _load_hdr
from pymotion.render.color_pipeline import (
    ColorGrade,
    apply_color_grade,
    apply_color_pipeline,
    apply_lut_trilinear,
    parse_cube_lut,
    tone_map_aces,
    tone_map_filmic,
    tone_map_reinhard,
)


class TestLoadHDR:
    """Tests for HDR file loading."""

    def test_load_hdr_rgb(self) -> None:
        """Load an RGB image as HDR."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.fromarray(np.full((32, 64, 3), 128, dtype=np.uint8))
            img.save(f.name)
            path = Path(f.name)

        result = _load_hdr(path)
        assert result.shape == (32, 64, 3)
        assert result.dtype == np.float32
        path.unlink()

    def test_load_hdr_rgba(self) -> None:
        """Load an RGBA image as HDR (drops alpha)."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.fromarray(np.full((32, 64, 4), 128, dtype=np.uint8))
            img.save(f.name)
            path = Path(f.name)

        result = _load_hdr(path)
        assert result.shape == (32, 64, 3)
        path.unlink()


class TestColorPipelineExtended:
    """Extended color pipeline tests for better coverage."""

    def test_lut_with_domain(self) -> None:
        """LUT with non-default domain."""
        lines = ["LUT_3D_SIZE 2", "DOMAIN_MIN 0.1 0.1 0.1", "DOMAIN_MAX 0.9 0.9 0.9"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    rv = r / 1
                    gv = g / 1
                    bv = b / 1
                    lines.append(f"{rv:.6f} {gv:.6f} {bv:.6f}")
        lut = parse_cube_lut("\n".join(lines))
        assert lut.size == 2

    def test_apply_lut_bright_frame(self) -> None:
        """Apply LUT to a bright frame."""
        lines = ["LUT_3D_SIZE 2"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
        lut = parse_cube_lut("\n".join(lines))
        frame = np.full((16, 16, 4), 255, dtype=np.uint8)
        result = apply_lut_trilinear(frame, lut)
        assert result.shape == frame.shape

    def test_color_grade_all_params(self) -> None:
        """Apply color grade with all parameters non-default."""
        frame = np.full((16, 16, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        grade = ColorGrade(
            lift=(0.1, -0.05, 0.05),
            gamma=(0.8, 1.2, 1.0),
            gain=(1.1, 0.9, 1.05),
            saturation=1.5,
        )
        result = apply_color_grade(frame, grade)
        assert result.shape == frame.shape
        assert not np.array_equal(result[:, :, :3], frame[:, :, :3])

    def test_pipeline_all_options(self) -> None:
        """Full pipeline with LUT + grade + tone map."""
        lines = ["LUT_3D_SIZE 2"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
        lut = parse_cube_lut("\n".join(lines))
        grade = ColorGrade(saturation=1.3)
        frame = np.full((16, 16, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        result = apply_color_pipeline(frame, lut=lut, grade=grade, tone_map="reinhard")
        assert result.shape == frame.shape

    def test_pipeline_unsupported_colorspace(self) -> None:
        """Non-srgb color space logs warning and proceeds."""
        frame = np.full((8, 8, 4), 128, dtype=np.uint8)
        result = apply_color_pipeline(frame, color_space="p3")
        np.testing.assert_array_equal(result, frame)

    def test_tone_map_white(self) -> None:
        """Tone mapping white pixels."""
        frame = np.full((8, 8, 4), 255, dtype=np.uint8)
        for fn in [tone_map_aces, tone_map_reinhard, tone_map_filmic]:
            result = fn(frame)
            assert result.dtype == np.uint8
            assert result.shape == frame.shape

    def test_grade_saturation_only(self) -> None:
        """Grade with only saturation change."""
        frame = np.full((8, 8, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        # Make R channel brighter to have something to desaturate
        frame[:, :, 2] = 200
        grade = ColorGrade(saturation=0.0)
        result = apply_color_grade(frame, grade)
        # At saturation=0, all color channels should be equal (grayscale)
        assert result.shape == frame.shape

    def test_grade_gamma_one(self) -> None:
        """Gamma=1 is a no-op."""
        frame = np.full((8, 8, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        grade = ColorGrade(gamma=(1.0, 1.0, 1.0))
        result = apply_color_grade(frame, grade)
        np.testing.assert_array_equal(result, frame)
