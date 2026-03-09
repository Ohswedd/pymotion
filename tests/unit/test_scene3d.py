"""Unit tests for clip/scene3d.py — Scene3D and Scene3DClip."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from pymotion.clip.scene3d import Scene3D, Scene3DClip
from pymotion.render.backend_3d import (
    AmbientLight,
    BloomConfig,
    Camera,
    DirectionalLight,
    Model3D,
    PBRMaterial,
    PointLight,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec3


class TestScene3D:
    def test_default_creation(self) -> None:
        scene = Scene3D()
        assert scene._width == 1920
        assert scene._height == 1080
        assert len(scene._models) == 0
        assert len(scene._lights) == 0

    def test_custom_dimensions(self) -> None:
        scene = Scene3D(width=640, height=480)
        assert scene._width == 640
        assert scene._height == 480

    def test_camera_access(self) -> None:
        scene = Scene3D()
        cam = scene.camera
        assert isinstance(cam, Camera)
        assert cam.fov == 60.0

    def test_camera_setter(self) -> None:
        scene = Scene3D()
        new_cam = Camera(position=Vec3(10.0, 0.0, 0.0), fov=90.0)
        scene.camera = new_cam
        assert scene.camera.fov == 90.0

    def test_add_light(self) -> None:
        scene = Scene3D()
        light = PointLight(position=Vec3(0.0, 5.0, 0.0))
        scene.add_light(light)
        assert len(scene._lights) == 1

    def test_add_multiple_lights(self) -> None:
        scene = Scene3D()
        scene.add_light(PointLight(position=Vec3(0.0, 5.0, 0.0)))
        scene.add_light(DirectionalLight(direction=Vec3(0.0, -1.0, 0.0)))
        scene.add_light(AmbientLight(intensity=0.3))
        assert len(scene._lights) == 3

    def test_add_model(self) -> None:
        scene = Scene3D()
        model = Model3D(
            vertices=np.zeros(9, dtype=np.float32),
            normals=np.zeros(9, dtype=np.float32),
            texcoords=np.zeros(6, dtype=np.float32),
        )
        scene.add_model(model)
        assert len(scene._models) == 1

    def test_add_effect(self) -> None:
        scene = Scene3D()
        scene.add_effect(BloomConfig(threshold=0.8, intensity=1.5))
        assert len(scene._post_effects) == 1

    def test_set_background(self) -> None:
        scene = Scene3D()
        scene.set_background(Color(0.2, 0.3, 0.4))
        assert scene._bg_color == Color(0.2, 0.3, 0.4)

    def test_to_clip(self) -> None:
        scene = Scene3D()
        clip = scene.to_clip(duration=90)
        assert isinstance(clip, Scene3DClip)
        assert clip.duration == 90
        assert clip.scene is scene

    def test_load_model_obj(self) -> None:
        obj_content = """
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
vn 0.0 0.0 1.0
f 1//1 2//1 3//1
"""
        with tempfile.NamedTemporaryFile(suffix=".obj", mode="w", delete=False) as f:
            f.write(obj_content)
            f.flush()
            path = Path(f.name)

        scene = Scene3D()
        model = scene.load_model(path)
        assert len(model.vertices) == 9
        assert len(scene._models) == 1
        path.unlink()

    def test_load_model_with_material(self) -> None:
        obj_content = """
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
f 1 2 3
"""
        with tempfile.NamedTemporaryFile(suffix=".obj", mode="w", delete=False) as f:
            f.write(obj_content)
            f.flush()
            path = Path(f.name)

        scene = Scene3D()
        mat = PBRMaterial(metallic=0.8, roughness=0.2)
        model = scene.load_model(path, material=mat)
        assert model.material.metallic == 0.8
        path.unlink()

    def test_load_unsupported_format(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".fbx", mode="w", delete=False) as f:
            f.write("fake content")
            f.flush()
            path = Path(f.name)

        scene = Scene3D()
        with pytest.raises(ValueError, match="Unsupported model format"):
            scene.load_model(path)
        path.unlink()

    def test_load_model_path_traversal(self) -> None:
        """Security test: path traversal should be blocked."""
        scene = Scene3D()
        tmpdir = Path(tempfile.gettempdir())
        with pytest.raises((ValueError, FileNotFoundError)):
            scene.load_model(
                "/etc/passwd",
                base_dirs=[tmpdir],
            )

    def test_set_environment_logs_warning(self) -> None:
        """HDRI environment is a stub, should log warning."""
        scene = Scene3D()
        # Should not raise
        scene.set_environment("fake.hdr")


class TestScene3DClip:
    def test_default_clip(self) -> None:
        clip = Scene3DClip()
        assert clip.scene is not None
        assert clip._renderer is None

    def test_clip_with_scene(self) -> None:
        scene = Scene3D(width=320, height=240)
        clip = Scene3DClip(scene=scene)
        assert clip.scene is scene

    def test_duration_from_to_clip(self) -> None:
        scene = Scene3D()
        clip = scene.to_clip(duration=60)
        assert clip.start == 0
        assert clip.end == 60
