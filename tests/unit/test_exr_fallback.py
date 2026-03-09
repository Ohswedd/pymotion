"""Tests for EXR loading fallback and additional coverage."""

from __future__ import annotations

import numpy as np

from pymotion.render.backend_3d import (
    AmbientLight,
    BloomConfig,
    DepthOfFieldConfig,
    DirectionalLight,
    PointLight,
    SpotLight,
    SSAOConfig,
    ToneMappingMode,
    _load_exr,
)
from pymotion.render.color_pipeline import load_cube_lut, parse_cube_lut
from pymotion.utils.math import Vec3


class TestExrFallback:
    """Test EXR loading fallback when OpenEXR is not installed."""

    def test_load_exr_fallback(self) -> None:
        """Without OpenEXR, returns gray fallback."""
        # This will hit the ImportError branch since OpenEXR is optional
        result = _load_exr("/nonexistent/file.exr")
        assert result.shape == (64, 128, 3)
        assert result.dtype == np.float32
        assert np.allclose(result, 0.2)


class TestLightDataclasses:
    """Test light dataclass construction."""

    def test_point_light_defaults(self) -> None:
        pl = PointLight(position=Vec3(0, 0, 0))
        assert pl.intensity == 1.0
        assert pl.radius == 10.0

    def test_directional_light_shadows(self) -> None:
        dl = DirectionalLight(direction=Vec3(0, -1, 0), cast_shadows=True)
        assert dl.cast_shadows is True

    def test_spot_light_angles(self) -> None:
        sl = SpotLight(position=Vec3(0, 5, 0), direction=Vec3(0, -1, 0))
        assert sl.inner_angle == 30.0
        assert sl.outer_angle == 45.0

    def test_ambient_light(self) -> None:
        al = AmbientLight(intensity=0.5)
        assert al.intensity == 0.5


class TestPostFXConfigs:
    """Test post-FX configuration dataclasses."""

    def test_ssao_defaults(self) -> None:
        cfg = SSAOConfig()
        assert cfg.radius == 0.5
        assert cfg.samples == 16

    def test_bloom_custom(self) -> None:
        cfg = BloomConfig(threshold=0.5, radius=3, intensity=2.0)
        assert cfg.threshold == 0.5

    def test_dof_custom(self) -> None:
        cfg = DepthOfFieldConfig(focus_distance=10.0, aperture=0.2)
        assert cfg.focus_distance == 10.0


class TestToneMappingMode:
    """Test ToneMappingMode enum."""

    def test_all_modes(self) -> None:
        assert ToneMappingMode.ACES.value == "aces"
        assert ToneMappingMode.FILMIC.value == "filmic"
        assert ToneMappingMode.REINHARD.value == "reinhard"
        assert ToneMappingMode.LINEAR.value == "linear"


class TestCubeLUTEdgeCases:
    """Edge case tests for .cube LUT parsing."""

    def test_lut_with_title(self) -> None:
        lines = ['TITLE "Test LUT"', "LUT_3D_SIZE 2"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
        lut = parse_cube_lut("\n".join(lines))
        assert lut.title == "Test LUT"

    def test_lut_with_comments(self) -> None:
        lines = ["# This is a comment", "LUT_3D_SIZE 2"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
        lut = parse_cube_lut("\n".join(lines))
        assert lut.size == 2

    def test_lut_missing_size_raises(self) -> None:
        try:
            parse_cube_lut("0.0 0.0 0.0")
            assert False, "Should raise"  # noqa: B011
        except ValueError:
            pass

    def test_lut_wrong_count_raises(self) -> None:
        try:
            parse_cube_lut("LUT_3D_SIZE 2\n0.0 0.0 0.0")
            assert False, "Should raise"  # noqa: B011
        except ValueError:
            pass

    def test_lut_1d_size_ignored(self) -> None:
        """LUT_1D_SIZE line is skipped."""
        lines = ["LUT_1D_SIZE 256", "LUT_3D_SIZE 2"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
        lut = parse_cube_lut("\n".join(lines))
        assert lut.size == 2

    def test_load_cube_lut_from_file(self) -> None:
        """load_cube_lut reads from disk."""
        import tempfile
        from pathlib import Path

        lines = ["LUT_3D_SIZE 2"]
        for b in range(2):
            for g in range(2):
                for r in range(2):
                    lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
        content = "\n".join(lines)

        with tempfile.NamedTemporaryFile(suffix=".cube", mode="w", delete=False) as f:
            f.write(content)
            path = Path(f.name)

        lut = load_cube_lut(path)
        assert lut.size == 2
        path.unlink()
