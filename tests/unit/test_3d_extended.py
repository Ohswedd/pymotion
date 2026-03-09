"""Extended tests for 3D features to improve coverage."""

from __future__ import annotations

import numpy as np

from pymotion.render.backend_3d import (
    AnimationChannel,
    Camera,
    HDRIEnvironment,
    InstanceData,
    Joint,
    PBRMaterial,
    SkeletalAnimation,
    _look_at,
    _model_matrix,
    _normal_matrix,
    _perspective,
    parse_obj,
)
from pymotion.utils.math import Vec3


class TestHDRIExtended:
    """Extended HDRI tests."""

    def test_sample_various_directions(self) -> None:
        """Sample in multiple directions."""
        data = np.random.default_rng(42).random((32, 64, 3)).astype(np.float32)
        hdri = HDRIEnvironment(data=data, intensity=1.0)
        for d in [Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1), Vec3(-1, 0, 0)]:
            r, g, b = hdri.sample(d)
            assert 0 <= r <= 1
            assert 0 <= g <= 1
            assert 0 <= b <= 1

    def test_load_unsupported_format(self) -> None:
        """Loading unsupported format logs warning."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake")
            path = Path(f.name)

        hdri = HDRIEnvironment(path=str(path))
        hdri.load()  # Should log warning, not crash
        path.unlink()

    def test_load_none_path(self) -> None:
        """Loading with None path is a no-op."""
        hdri = HDRIEnvironment(path=None)
        hdri.load()
        assert hdri.data is None


class TestSkeletalExtended:
    """Extended skeletal animation tests."""

    def test_scale_channel(self) -> None:
        """Scale channel affects joint matrices."""
        joints = [Joint(name="root", index=0)]
        channels = [
            AnimationChannel(
                joint_index=0,
                property="scale",
                times=np.array([0.0, 1.0], dtype=np.float32),
                values=np.array([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]], dtype=np.float32),
            ),
        ]
        anim = SkeletalAnimation(name="scale", joints=joints, channels=channels, duration=1.0)
        m = anim.sample(0.5)
        assert abs(m[0, 0, 0] - 1.5) < 0.01

    def test_empty_channel_times(self) -> None:
        """Channel with empty times is skipped."""
        joints = [Joint(name="root", index=0)]
        channels = [
            AnimationChannel(
                joint_index=0,
                property="translation",
                times=np.array([], dtype=np.float32),
                values=np.array([], dtype=np.float32).reshape(0, 3),
            ),
        ]
        anim = SkeletalAnimation(name="empty", joints=joints, channels=channels, duration=1.0)
        m = anim.sample(0.0)
        assert m.shape == (1, 4, 4)

    def test_invalid_joint_index(self) -> None:
        """Channel targeting invalid joint index is skipped."""
        joints = [Joint(name="root", index=0)]
        channels = [
            AnimationChannel(
                joint_index=99,
                property="translation",
                times=np.array([0.0], dtype=np.float32),
                values=np.array([[1.0, 0.0, 0.0]], dtype=np.float32),
            ),
        ]
        anim = SkeletalAnimation(name="bad_idx", joints=joints, channels=channels, duration=1.0)
        m = anim.sample(0.0)
        assert m.shape == (1, 4, 4)

    def test_before_first_keyframe(self) -> None:
        """Sampling before first keyframe uses first value."""
        joints = [Joint(name="root", index=0)]
        channels = [
            AnimationChannel(
                joint_index=0,
                property="translation",
                times=np.array([0.5, 1.0], dtype=np.float32),
                values=np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]], dtype=np.float32),
            ),
        ]
        anim = SkeletalAnimation(name="early", joints=joints, channels=channels, duration=1.5)
        m = anim.sample(0.0)
        assert abs(m[0, 0, 3] - 1.0) < 0.01


class TestMatrixUtils:
    """Test matrix utility functions."""

    def test_model_matrix_default(self) -> None:
        mat = _model_matrix()
        np.testing.assert_array_almost_equal(mat, np.eye(4, dtype=np.float32))

    def test_model_matrix_translation(self) -> None:
        mat = _model_matrix(position=Vec3(1.0, 2.0, 3.0))
        assert mat[0, 3] == 1.0
        assert mat[1, 3] == 2.0
        assert mat[2, 3] == 3.0

    def test_model_matrix_scale(self) -> None:
        mat = _model_matrix(scale=Vec3(2.0, 3.0, 4.0))
        assert mat[0, 0] == 2.0
        assert mat[1, 1] == 3.0
        assert mat[2, 2] == 4.0

    def test_normal_matrix_identity(self) -> None:
        model = np.eye(4, dtype=np.float32)
        nmat = _normal_matrix(model)
        np.testing.assert_array_almost_equal(nmat, np.eye(3, dtype=np.float32))

    def test_normal_matrix_singular(self) -> None:
        """Singular matrix returns identity."""
        model = np.zeros((4, 4), dtype=np.float32)
        nmat = _normal_matrix(model)
        np.testing.assert_array_almost_equal(nmat, np.eye(3, dtype=np.float32))

    def test_perspective_matrix(self) -> None:
        mat = _perspective(60.0, 16 / 9, 0.1, 100.0)
        assert mat.shape == (4, 4)
        assert mat[3, 2] == -1.0

    def test_look_at_matrix(self) -> None:
        mat = _look_at(Vec3(0, 0, 5), Vec3(0, 0, 0), Vec3(0, 1, 0))
        assert mat.shape == (4, 4)


class TestCameraMatrices:
    """Test Camera matrix generation."""

    def test_view_matrix(self) -> None:
        cam = Camera(position=Vec3(0, 0, 5), target=Vec3(0, 0, 0))
        view = cam.view_matrix()
        assert view.shape == (4, 4)

    def test_projection_matrix(self) -> None:
        cam = Camera(fov=90.0)
        proj = cam.projection_matrix(16 / 9)
        assert proj.shape == (4, 4)


class TestModel3D:
    """Test Model3D dataclass."""

    def test_parse_simple_obj(self) -> None:
        obj = """
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
vn 0.0 0.0 1.0
f 1//1 2//1 3//1
"""
        model = parse_obj(obj)
        assert len(model.vertices) == 9  # 3 verts * 3 coords
        assert len(model.normals) == 9

    def test_material_defaults(self) -> None:
        mat = PBRMaterial()
        assert mat.metallic == 0.0
        assert mat.roughness == 0.5
        assert mat.opacity == 1.0


class TestInstanceData:
    """Extended InstanceData tests."""

    def test_single_instance(self) -> None:
        matrices = np.eye(4, dtype=np.float32).reshape(1, 4, 4)
        inst = InstanceData(model_matrices=matrices)
        assert inst.count == 1
