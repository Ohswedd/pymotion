"""Scene3DClip — wraps a 3D scene for rendering to BGRA frames.

Provides the Scene3D container that holds models, lights, camera,
and post-processing effects, and can be converted to a renderable clip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.render.backend_3d import (
    Camera,
    Light,
    Model3D,
    ModernGLRenderer,
    PBRMaterial,
    PostFX3D,
    parse_obj,
)
from pymotion.security.validation import validate_path
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


class Scene3D:
    """Container for a 3D scene with models, lights, camera, and effects.

    Provides methods to build up a 3D scene declaratively, then convert
    it to a Scene3DClip for rendering in a composition.
    """

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        """Initialize an empty 3D scene.

        Args:
            width: Scene width in pixels.
            height: Scene height in pixels.
        """
        self._width = width
        self._height = height
        self._models: list[Model3D] = []
        self._lights: list[Light] = []
        self._camera = Camera()
        self._post_effects: list[PostFX3D] = []
        self._bg_color = Color(0.0, 0.0, 0.0)

    @property
    def camera(self) -> Camera:
        """Access the scene camera.

        Returns:
            The scene's Camera instance.
        """
        return self._camera

    @camera.setter
    def camera(self, value: Camera) -> None:
        """Set the scene camera.

        Args:
            value: The new camera.
        """
        self._camera = value

    def load_model(
        self,
        path: str | Path,
        base_dirs: list[Path] | None = None,
        material: PBRMaterial | None = None,
    ) -> Model3D:
        """Load a 3D model from file and add it to the scene.

        Currently supports OBJ format. GLTF/GLB support requires
        the pygltflib optional dependency.

        Args:
            path: Path to the model file.
            base_dirs: Allowed directories for path validation.
                Defaults to the file's parent directory.
            material: Optional PBR material to apply.

        Returns:
            The loaded Model3D instance.

        Raises:
            ValueError: If path is outside allowed directories.
            FileNotFoundError: If the file doesn't exist.
        """
        p = Path(path)
        if base_dirs is None:
            base_dirs = [p.parent.resolve()]
        validated = validate_path(p, base_dirs)

        content = validated.read_text(encoding="utf-8")
        suffix = validated.suffix.lower()

        if suffix == ".obj":
            model = parse_obj(content)
        else:
            msg = f"Unsupported model format: {suffix} (supported: .obj)"
            raise ValueError(msg)

        if material is not None:
            model.material = material

        self._models.append(model)
        logger.info("model_loaded", path=str(validated), format=suffix)
        return model

    def add_model(self, model: Model3D) -> None:
        """Add a pre-built Model3D to the scene.

        Args:
            model: The model to add.
        """
        self._models.append(model)

    def add_light(self, light: Light) -> None:
        """Add a light source to the scene.

        Args:
            light: The light to add.
        """
        self._lights.append(light)

    def set_environment(self, hdri_path: str | Path) -> None:
        """Set an HDRI environment map (stub for future implementation).

        Args:
            hdri_path: Path to the HDRI file.
        """
        logger.warning("hdri_not_implemented", path=str(hdri_path))

    def add_effect(self, effect: PostFX3D) -> None:
        """Add a post-processing effect to the scene.

        Args:
            effect: The effect configuration.
        """
        self._post_effects.append(effect)

    def set_background(self, color: Color) -> None:
        """Set the background color.

        Args:
            color: Background color.
        """
        self._bg_color = color

    def to_clip(self, duration: int) -> Scene3DClip:
        """Convert this scene to a renderable clip.

        Args:
            duration: Duration in frames.

        Returns:
            A Scene3DClip bound to this scene.
        """
        clip = Scene3DClip(scene=self)
        clip.set_duration(duration)
        return clip


@dataclass
class Scene3DClip(Clip):
    """Clip that renders a 3D scene to BGRA frames.

    Wraps a Scene3D and uses ModernGLRenderer for rendering.
    """

    scene: Scene3D = field(default_factory=Scene3D)
    _renderer: ModernGLRenderer | None = field(default=None, repr=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of the 3D scene.

        Args:
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        width = ctx.resolution.width
        height = ctx.resolution.height

        if self._renderer is None or (
            self._renderer._width != width or self._renderer._height != height
        ):
            if self._renderer is not None:
                self._renderer.release()
            self._renderer = ModernGLRenderer(width, height)

        return self._renderer.render_scene(
            models=self.scene._models,
            camera=self.scene._camera,
            lights=self.scene._lights,
            post_effects=self.scene._post_effects or None,
            bg_color=self.scene._bg_color,
        )
