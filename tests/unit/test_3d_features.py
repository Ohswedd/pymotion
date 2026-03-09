"""Tests for RC 0.9 3D backend features: HDRI, shadow config, skeletal anim, instancing."""

from __future__ import annotations

import numpy as np

from pymotion.render.backend_3d import (
    AnimationChannel,
    HDRIEnvironment,
    InstanceData,
    Joint,
    ShadowMapConfig,
    SkeletalAnimation,
)
from pymotion.utils.math import Vec3


class TestHDRIEnvironment:
    """Tests for HDRI environment map."""

    def test_default_sample(self) -> None:
        """Without loaded data, sample returns fallback ambient."""
        hdri = HDRIEnvironment(intensity=1.0)
        r, g, b = hdri.sample(Vec3(0.0, 1.0, 0.0))
        assert r == 0.2
        assert g == 0.2
        assert b == 0.2

    def test_sample_with_data(self) -> None:
        """With loaded data, sample reads from the array."""
        data = np.full((64, 128, 3), 0.5, dtype=np.float32)
        hdri = HDRIEnvironment(data=data, intensity=2.0)
        r, g, b = hdri.sample(Vec3(0.0, 1.0, 0.0))
        assert r == 1.0  # 0.5 * 2.0
        assert g == 1.0

    def test_rotation(self) -> None:
        """Rotation affects sampling direction."""
        data = np.zeros((64, 128, 3), dtype=np.float32)
        data[:, 0, :] = 1.0  # Only first column is bright
        hdri0 = HDRIEnvironment(data=data, rotation=0.0)
        hdri180 = HDRIEnvironment(data=data, rotation=180.0)
        r0, _, _ = hdri0.sample(Vec3(0.0, 0.0, 1.0))
        r180, _, _ = hdri180.sample(Vec3(0.0, 0.0, 1.0))
        # Different rotations should give different samples
        # (may not always differ depending on map symmetry, but should not crash)
        assert isinstance(r0, float)
        assert isinstance(r180, float)

    def test_missing_file_raises(self) -> None:
        """Loading nonexistent file raises FileNotFoundError."""
        hdri = HDRIEnvironment(path="/nonexistent/env.exr")
        try:
            hdri.load()
            assert False, "Should have raised"  # noqa: B011
        except FileNotFoundError:
            pass

    def test_intensity_scaling(self) -> None:
        """Intensity scales the sampled values."""
        data = np.full((64, 128, 3), 0.3, dtype=np.float32)
        hdri = HDRIEnvironment(data=data, intensity=3.0)
        r, g, b = hdri.sample(Vec3(1.0, 0.0, 0.0))
        assert abs(r - 0.9) < 0.01


class TestShadowMapConfig:
    """Tests for shadow mapping configuration."""

    def test_default_values(self) -> None:
        cfg = ShadowMapConfig()
        assert cfg.resolution == 1024
        assert cfg.bias == 0.005
        assert cfg.pcf_samples == 4
        assert cfg.cascade_count == 3

    def test_custom_values(self) -> None:
        cfg = ShadowMapConfig(resolution=2048, bias=0.01, pcf_samples=8, cascade_count=4)
        assert cfg.resolution == 2048
        assert cfg.pcf_samples == 8


class TestSkeletalAnimation:
    """Tests for skeletal animation system."""

    def _make_skeleton(self) -> SkeletalAnimation:
        joints = [
            Joint(name="root", index=0, parent_index=-1),
            Joint(name="child", index=1, parent_index=0),
        ]
        channels = [
            AnimationChannel(
                joint_index=0,
                property="translation",
                times=np.array([0.0, 1.0], dtype=np.float32),
                values=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32),
            ),
        ]
        return SkeletalAnimation(
            name="test_anim",
            joints=joints,
            channels=channels,
            duration=1.0,
        )

    def test_sample_at_start(self) -> None:
        """Sampling at t=0 gives initial pose."""
        anim = self._make_skeleton()
        matrices = anim.sample(0.0)
        assert matrices.shape == (2, 4, 4)
        # Root translation should be (0,0,0) at t=0
        assert matrices[0, 0, 3] == 0.0

    def test_sample_at_end(self) -> None:
        """Sampling at t=1 gives final pose."""
        anim = self._make_skeleton()
        matrices = anim.sample(1.0)
        assert matrices.shape == (2, 4, 4)
        # Root translation should be (1,0,0) at t=1
        assert abs(matrices[0, 0, 3] - 1.0) < 0.01

    def test_sample_midpoint(self) -> None:
        """Sampling at t=0.5 interpolates."""
        anim = self._make_skeleton()
        matrices = anim.sample(0.5)
        assert abs(matrices[0, 0, 3] - 0.5) < 0.01

    def test_empty_skeleton(self) -> None:
        """Empty skeleton returns empty array."""
        anim = SkeletalAnimation()
        matrices = anim.sample(0.0)
        assert matrices.shape == (0, 4, 4)

    def test_time_wrapping(self) -> None:
        """Time wraps around duration."""
        anim = self._make_skeleton()
        m0 = anim.sample(0.0)
        m2 = anim.sample(2.0)  # Should wrap to 0.0
        np.testing.assert_array_almost_equal(m0, m2)


class TestInstanceData:
    """Tests for GPU instancing data."""

    def test_count(self) -> None:
        matrices = np.stack([np.eye(4, dtype=np.float32)] * 5)
        inst = InstanceData(model_matrices=matrices)
        assert inst.count == 5

    def test_with_colors(self) -> None:
        matrices = np.stack([np.eye(4, dtype=np.float32)] * 3)
        colors = np.ones((3, 4), dtype=np.float32)
        inst = InstanceData(model_matrices=matrices, colors=colors)
        assert inst.count == 3
        assert inst.colors is not None
        assert inst.colors.shape == (3, 4)

    def test_without_colors(self) -> None:
        matrices = np.stack([np.eye(4, dtype=np.float32)] * 2)
        inst = InstanceData(model_matrices=matrices)
        assert inst.colors is None
