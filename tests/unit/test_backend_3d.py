"""Unit tests for render/backend_3d.py — 3D rendering backend."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.render.backend_3d import (
    AmbientLight,
    BloomConfig,
    Camera,
    DepthOfFieldConfig,
    DirectionalLight,
    Model3D,
    ModernGLRenderer,
    PBRMaterial,
    PointLight,
    SpotLight,
    SSAOConfig,
    ToneMappingMode,
    _look_at,
    _model_matrix,
    _normal_matrix,
    _perspective,
    parse_obj,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec3

# ---------------------------------------------------------------------------
# PBRMaterial
# ---------------------------------------------------------------------------


class TestPBRMaterial:
    def test_defaults(self) -> None:
        mat = PBRMaterial()
        assert mat.metallic == 0.0
        assert mat.roughness == 0.5
        assert mat.opacity == 1.0
        assert mat.albedo == Color(1.0, 1.0, 1.0)
        assert mat.emissive == Color(0.0, 0.0, 0.0)
        assert mat.normal_map is None
        assert mat.ao_map is None

    def test_custom_values(self) -> None:
        mat = PBRMaterial(
            albedo=Color(1.0, 0.0, 0.0),
            metallic=1.0,
            roughness=0.1,
            emissive=Color(0.5, 0.5, 0.0),
            emissive_strength=2.0,
            opacity=0.8,
        )
        assert mat.metallic == 1.0
        assert mat.roughness == 0.1
        assert mat.emissive_strength == 2.0


# ---------------------------------------------------------------------------
# Lights
# ---------------------------------------------------------------------------


class TestLights:
    def test_point_light_defaults(self) -> None:
        light = PointLight(position=Vec3(1.0, 2.0, 3.0))
        assert light.position == Vec3(1.0, 2.0, 3.0)
        assert light.intensity == 1.0
        assert light.radius == 10.0
        assert light.color == Color(1.0, 1.0, 1.0)

    def test_directional_light(self) -> None:
        light = DirectionalLight(
            direction=Vec3(0.0, -1.0, 0.0),
            intensity=2.0,
            cast_shadows=True,
        )
        assert light.direction == Vec3(0.0, -1.0, 0.0)
        assert light.intensity == 2.0
        assert light.cast_shadows is True

    def test_spot_light(self) -> None:
        light = SpotLight(
            position=Vec3(0.0, 5.0, 0.0),
            direction=Vec3(0.0, -1.0, 0.0),
            inner_angle=20.0,
            outer_angle=40.0,
        )
        assert light.inner_angle == 20.0
        assert light.outer_angle == 40.0

    def test_ambient_light(self) -> None:
        light = AmbientLight(intensity=0.2)
        assert light.intensity == 0.2


# ---------------------------------------------------------------------------
# Post-FX Configs
# ---------------------------------------------------------------------------


class TestPostFXConfigs:
    def test_ssao_defaults(self) -> None:
        cfg = SSAOConfig()
        assert cfg.radius == 0.5
        assert cfg.samples == 16

    def test_bloom_defaults(self) -> None:
        cfg = BloomConfig()
        assert cfg.threshold == 1.0
        assert cfg.intensity == 1.0

    def test_dof_defaults(self) -> None:
        cfg = DepthOfFieldConfig()
        assert cfg.focus_distance == 5.0
        assert cfg.aperture == 0.1


class TestToneMappingMode:
    def test_values(self) -> None:
        assert ToneMappingMode.ACES.value == "aces"
        assert ToneMappingMode.REINHARD.value == "reinhard"
        assert ToneMappingMode.LINEAR.value == "linear"
        assert ToneMappingMode.FILMIC.value == "filmic"


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------


class TestCamera:
    def test_defaults(self) -> None:
        cam = Camera()
        assert cam.fov == 60.0
        assert cam.near == 0.01
        assert cam.far == 1000.0
        assert cam.position == Vec3(0.0, 0.0, 5.0)
        assert cam.target == Vec3(0.0, 0.0, 0.0)

    def test_view_matrix_shape(self) -> None:
        cam = Camera(position=Vec3(0.0, 0.0, 5.0), target=Vec3(0.0, 0.0, 0.0))
        view = cam.view_matrix()
        assert view.shape == (4, 4)
        assert view.dtype == np.float32

    def test_projection_matrix_shape(self) -> None:
        cam = Camera()
        proj = cam.projection_matrix(16.0 / 9.0)
        assert proj.shape == (4, 4)
        assert proj.dtype == np.float32

    def test_custom_camera(self) -> None:
        cam = Camera(
            position=Vec3(10.0, 5.0, 10.0),
            target=Vec3(0.0, 0.0, 0.0),
            fov=45.0,
        )
        assert cam.fov == 45.0
        view = cam.view_matrix()
        assert view.shape == (4, 4)


# ---------------------------------------------------------------------------
# Model3D
# ---------------------------------------------------------------------------


class TestModel3D:
    def test_construction(self) -> None:
        verts = np.array([0, 0, 0, 1, 0, 0, 0, 1, 0], dtype=np.float32)
        norms = np.array([0, 0, 1, 0, 0, 1, 0, 0, 1], dtype=np.float32)
        uvs = np.array([0, 0, 1, 0, 0, 1], dtype=np.float32)
        model = Model3D(vertices=verts, normals=norms, texcoords=uvs)
        assert model.indices is None
        assert model.material.metallic == 0.0  # default

    def test_with_material(self) -> None:
        mat = PBRMaterial(metallic=0.9)
        model = Model3D(
            vertices=np.zeros(9, dtype=np.float32),
            normals=np.zeros(9, dtype=np.float32),
            texcoords=np.zeros(6, dtype=np.float32),
            material=mat,
        )
        assert model.material.metallic == 0.9


# ---------------------------------------------------------------------------
# OBJ Parser
# ---------------------------------------------------------------------------


class TestParseObj:
    def test_simple_triangle(self) -> None:
        obj = """
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
vn 0.0 0.0 1.0
vn 0.0 0.0 1.0
vn 0.0 0.0 1.0
vt 0.0 0.0
vt 1.0 0.0
vt 0.0 1.0
f 1/1/1 2/2/2 3/3/3
"""
        model = parse_obj(obj)
        assert len(model.vertices) == 9  # 3 verts * 3 components
        assert len(model.normals) == 9
        assert len(model.texcoords) == 6

    def test_quad_triangulation(self) -> None:
        obj = """
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 0.0 1.0 0.0
vn 0.0 0.0 1.0
vt 0.0 0.0
f 1/1/1 2/1/1 3/1/1 4/1/1
"""
        model = parse_obj(obj)
        # Quad → 2 triangles → 6 verts
        assert len(model.vertices) == 18

    def test_face_without_texcoords(self) -> None:
        obj = """
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
vn 0.0 0.0 1.0
f 1//1 2//1 3//1
"""
        model = parse_obj(obj)
        assert len(model.vertices) == 9

    def test_empty_obj_raises(self) -> None:
        with pytest.raises(ValueError, match="no valid face data"):
            parse_obj("")

    def test_comments_and_blank_lines(self) -> None:
        obj = """
# This is a comment
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0

vn 0.0 0.0 1.0
f 1//1 2//1 3//1
"""
        model = parse_obj(obj)
        assert len(model.vertices) == 9

    def test_obj_vertex_values(self) -> None:
        obj = """
v 1.5 2.5 3.5
v 4.5 5.5 6.5
v 7.5 8.5 9.5
f 1 2 3
"""
        model = parse_obj(obj)
        # First vertex should be (1.5, 2.5, 3.5)
        assert model.vertices[0] == pytest.approx(1.5)
        assert model.vertices[1] == pytest.approx(2.5)
        assert model.vertices[2] == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Matrix Utilities
# ---------------------------------------------------------------------------


class TestMatrixUtils:
    def test_look_at_identity_like(self) -> None:
        view = _look_at(
            Vec3(0.0, 0.0, 1.0),
            Vec3(0.0, 0.0, 0.0),
            Vec3(0.0, 1.0, 0.0),
        )
        assert view.shape == (4, 4)
        assert view.dtype == np.float32

    def test_perspective_shape(self) -> None:
        proj = _perspective(60.0, 16.0 / 9.0, 0.01, 1000.0)
        assert proj.shape == (4, 4)
        assert proj.dtype == np.float32

    def test_perspective_fov_effect(self) -> None:
        narrow = _perspective(30.0, 1.0, 0.01, 100.0)
        wide = _perspective(90.0, 1.0, 0.01, 100.0)
        # Narrow FOV → larger focal length → larger [1,1] element
        assert narrow[1, 1] > wide[1, 1]

    def test_model_matrix_identity(self) -> None:
        mat = _model_matrix()
        expected = np.eye(4, dtype=np.float32)
        np.testing.assert_array_almost_equal(mat, expected)

    def test_model_matrix_translation(self) -> None:
        mat = _model_matrix(position=Vec3(1.0, 2.0, 3.0))
        assert mat[0, 3] == pytest.approx(1.0)
        assert mat[1, 3] == pytest.approx(2.0)
        assert mat[2, 3] == pytest.approx(3.0)

    def test_model_matrix_scale(self) -> None:
        mat = _model_matrix(scale=Vec3(2.0, 3.0, 4.0))
        assert mat[0, 0] == pytest.approx(2.0)
        assert mat[1, 1] == pytest.approx(3.0)
        assert mat[2, 2] == pytest.approx(4.0)

    def test_normal_matrix_identity(self) -> None:
        model = np.eye(4, dtype=np.float32)
        normal = _normal_matrix(model)
        assert normal.shape == (3, 3)
        np.testing.assert_array_almost_equal(normal, np.eye(3, dtype=np.float32))

    def test_normal_matrix_scaled(self) -> None:
        model = _model_matrix(scale=Vec3(2.0, 2.0, 2.0))
        normal = _normal_matrix(model)
        assert normal.shape == (3, 3)
        # For uniform scale, normal matrix should be inverse transpose
        # which is 1/scale * I
        assert normal[0, 0] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# ModernGLRenderer (mocked — no real GPU in CI)
# ---------------------------------------------------------------------------


class TestModernGLRenderer:
    def test_can_render_scene3d(self) -> None:
        from pymotion.clip.scene3d import Scene3DClip

        renderer = ModernGLRenderer(320, 240)
        clip = Scene3DClip()
        assert renderer.can_render(clip) is True

    def test_cannot_render_other_clips(self) -> None:
        from pymotion.clip.color import ColorClip

        renderer = ModernGLRenderer(320, 240)
        clip = ColorClip(color=Color(1.0, 0.0, 0.0))
        assert renderer.can_render(clip) is False

    def test_render_frame_rejects_wrong_type(self) -> None:
        from pymotion.clip.base import RenderContext, Resolution, TimeRange
        from pymotion.clip.color import ColorClip

        renderer = ModernGLRenderer(320, 240)
        clip = ColorClip(color=Color(1.0, 0.0, 0.0))
        ctx = RenderContext(
            frame=0,
            fps=30,
            resolution=Resolution(320, 240),
            time_range=TimeRange(0, 30),
            local_frame=0,
            progress=0.0,
        )
        with pytest.raises(TypeError, match="cannot render"):
            renderer.render_frame(clip, ctx)
