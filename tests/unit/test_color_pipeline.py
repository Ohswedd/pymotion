"""Unit tests for render/color_pipeline.py — LUT, color grade, pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from pymotion.render.color_pipeline import (
    ColorGrade,
    apply_color_grade,
    apply_color_pipeline,
    apply_lut_trilinear,
    load_cube_lut,
    parse_cube_lut,
)


def _make_identity_cube(size: int = 2) -> str:
    """Generate a minimal identity .cube LUT string."""
    lines = [f"LUT_3D_SIZE {size}"]
    for b in range(size):
        for g in range(size):
            for r in range(size):
                rv = r / max(size - 1, 1)
                gv = g / max(size - 1, 1)
                bv = b / max(size - 1, 1)
                lines.append(f"{rv:.6f} {gv:.6f} {bv:.6f}")
    return "\n".join(lines)


def _make_bgra_frame(w: int = 8, h: int = 8) -> np.ndarray:
    """Create a test BGRA frame with known values."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[:, :, 0] = 50  # B
    frame[:, :, 1] = 100  # G
    frame[:, :, 2] = 200  # R
    frame[:, :, 3] = 255  # A
    return frame


class TestParseCubeLut:
    def test_identity_lut(self) -> None:
        cube = _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        assert lut.size == 2
        assert lut.data.shape == (2, 2, 2, 3)

    def test_with_title(self) -> None:
        cube = 'TITLE "My LUT"\n' + _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        assert lut.title == "My LUT"

    def test_with_comments(self) -> None:
        cube = "# comment\n" + _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        assert lut.size == 2

    def test_missing_size_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing LUT_3D_SIZE"):
            parse_cube_lut("0.0 0.0 0.0\n1.0 1.0 1.0")

    def test_wrong_entry_count_raises(self) -> None:
        cube = "LUT_3D_SIZE 2\n0.0 0.0 0.0\n"
        with pytest.raises(ValueError, match="Expected 8"):
            parse_cube_lut(cube)

    def test_size_3_lut(self) -> None:
        cube = _make_identity_cube(3)
        lut = parse_cube_lut(cube)
        assert lut.size == 3
        assert lut.data.shape == (3, 3, 3, 3)

    def test_domain_min_max(self) -> None:
        cube = "DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n" + _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        assert lut.size == 2


class TestLoadCubeLut:
    def test_load_from_file(self) -> None:
        cube = _make_identity_cube(2)
        with tempfile.NamedTemporaryFile(suffix=".cube", mode="w", delete=False) as f:
            f.write(cube)
            f.flush()
            path = Path(f.name)
        lut = load_cube_lut(path)
        assert lut.size == 2
        path.unlink()

    def test_path_traversal_blocked(self) -> None:
        tmpdir = Path(tempfile.gettempdir())
        with pytest.raises((ValueError, FileNotFoundError)):
            load_cube_lut("/etc/passwd", base_dirs=[tmpdir])


class TestApplyLutTrilinear:
    def test_identity_lut_preserves(self) -> None:
        cube = _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        frame = _make_bgra_frame()
        result = apply_lut_trilinear(frame, lut)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8
        # Identity LUT should approximately preserve values
        np.testing.assert_allclose(result[:, :, :3], frame[:, :, :3], atol=2)

    def test_alpha_preserved(self) -> None:
        cube = _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        frame = _make_bgra_frame()
        result = apply_lut_trilinear(frame, lut)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])

    def test_output_shape_matches_input(self) -> None:
        cube = _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        frame = np.zeros((16, 32, 4), dtype=np.uint8)
        result = apply_lut_trilinear(frame, lut)
        assert result.shape == (16, 32, 4)


class TestColorGrade:
    def test_defaults(self) -> None:
        grade = ColorGrade()
        assert grade.saturation == 1.0
        assert grade.lift == (0.0, 0.0, 0.0)
        assert grade.gamma == (1.0, 1.0, 1.0)
        assert grade.gain == (1.0, 1.0, 1.0)

    def test_identity_grade_preserves(self) -> None:
        frame = _make_bgra_frame()
        result = apply_color_grade(frame, ColorGrade())
        np.testing.assert_allclose(result[:, :, :3], frame[:, :, :3], atol=1)

    def test_gain_brightens(self) -> None:
        frame = _make_bgra_frame()
        grade = ColorGrade(gain=(1.5, 1.5, 1.5))
        result = apply_color_grade(frame, grade)
        # R channel (idx 2) should be brighter
        assert np.mean(result[:, :, 2]) > np.mean(frame[:, :, 2])

    def test_zero_saturation_is_mono(self) -> None:
        frame = _make_bgra_frame()
        grade = ColorGrade(saturation=0.0)
        result = apply_color_grade(frame, grade)
        # All RGB channels should be similar (grayscale)
        r = result[:, :, 2].astype(float)
        g = result[:, :, 1].astype(float)
        b = result[:, :, 0].astype(float)
        assert np.allclose(r, g, atol=2)
        assert np.allclose(g, b, atol=2)

    def test_lift_offsets_shadows(self) -> None:
        frame = np.zeros((8, 8, 4), dtype=np.uint8)
        frame[:, :, 3] = 255  # fully opaque, black image
        grade = ColorGrade(lift=(0.2, 0.0, 0.0))
        result = apply_color_grade(frame, grade)
        # R channel should be lifted from 0
        assert np.mean(result[:, :, 2]) > 0

    def test_alpha_preserved(self) -> None:
        frame = _make_bgra_frame()
        grade = ColorGrade(gain=(2.0, 2.0, 2.0))
        result = apply_color_grade(frame, grade)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])


class TestApplyColorPipeline:
    def test_passthrough(self) -> None:
        frame = _make_bgra_frame()
        result = apply_color_pipeline(frame)
        np.testing.assert_array_equal(result, frame)

    def test_with_lut(self) -> None:
        cube = _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        frame = _make_bgra_frame()
        result = apply_color_pipeline(frame, lut=lut)
        assert result.shape == frame.shape

    def test_with_grade(self) -> None:
        frame = _make_bgra_frame()
        grade = ColorGrade(saturation=0.5)
        result = apply_color_pipeline(frame, grade=grade)
        assert result.shape == frame.shape

    def test_with_both(self) -> None:
        cube = _make_identity_cube(2)
        lut = parse_cube_lut(cube)
        grade = ColorGrade(gain=(1.2, 1.2, 1.2))
        frame = _make_bgra_frame()
        result = apply_color_pipeline(frame, lut=lut, grade=grade)
        assert result.shape == frame.shape

    def test_unsupported_color_space_warns(self) -> None:
        frame = _make_bgra_frame()
        # Should not raise, just warn
        result = apply_color_pipeline(frame, color_space="rec709")
        assert result.shape == frame.shape
