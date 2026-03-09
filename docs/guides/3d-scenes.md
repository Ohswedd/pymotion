# 3D Scenes

PyMotion includes a real-time 3D rendering pipeline built on ModernGL. You
can create scenes with PBR materials, multiple light types, and OBJ model
loading, then composite them into your video as clips.

## Prerequisites

The 3D system requires ModernGL and a working OpenGL 3.3+ context. On
headless servers, ModernGL uses a standalone (offscreen) context
automatically.

```bash
pip install moderngl
```

## Creating a scene

`Scene3D` is the container for models, lights, and camera:

```python
from pymotion.clip.scene3d import Scene3D
from pymotion.render.backend_3d import Camera, Light, PBRMaterial

# Create a scene at 1080p
scene = Scene3D(width=1920, height=1080)
```

## Camera

Every scene starts with a default camera. Access it through the `camera`
property, or replace it entirely:

```python
from pymotion.render.backend_3d import Camera
from pymotion.utils.math import Vec3

# Access the default camera
cam = scene.camera

# Or set a new one
scene.camera = Camera(
    position=Vec3(0.0, 2.0, 5.0),
    target=Vec3(0.0, 0.0, 0.0),
    up=Vec3(0.0, 1.0, 0.0),
    fov=60.0,
    near=0.1,
    far=100.0,
)
```

### Camera parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `position` | Camera position in world space | `(0, 0, 5)` |
| `target` | Point the camera looks at | `(0, 0, 0)` |
| `up` | Up direction vector | `(0, 1, 0)` |
| `fov` | Vertical field of view in degrees | 60.0 |
| `near` | Near clipping plane distance | 0.1 |
| `far` | Far clipping plane distance | 100.0 |

## Loading models

Load OBJ models from file. The path is validated for security:

```python
from pathlib import Path
from pymotion.render.backend_3d import PBRMaterial

# Load a model with default material
model = scene.load_model("assets/models/cube.obj")

# Load with a custom PBR material
material = PBRMaterial(
    albedo=(0.8, 0.2, 0.2, 1.0),
    metallic=0.0,
    roughness=0.5,
)
model = scene.load_model(
    "assets/models/sphere.obj",
    material=material,
    base_dirs=[Path("assets/models")],
)
```

### PBR materials

PyMotion uses a Cook-Torrance PBR BRDF for physically-based shading:

```python
from pymotion.render.backend_3d import PBRMaterial

# Shiny metal
metal = PBRMaterial(
    albedo=(0.9, 0.9, 0.9, 1.0),
    metallic=1.0,
    roughness=0.1,
)

# Rough plastic
plastic = PBRMaterial(
    albedo=(0.2, 0.5, 0.8, 1.0),
    metallic=0.0,
    roughness=0.8,
)

# Emissive material (glowing)
glow = PBRMaterial(
    albedo=(1.0, 0.5, 0.0, 1.0),
    metallic=0.0,
    roughness=0.5,
    emissive=(1.0, 0.5, 0.0),
    emissive_strength=2.0,
)
```

| Property | Range | Description |
|----------|-------|-------------|
| `albedo` | RGBA tuple (0-1) | Base color |
| `metallic` | 0.0 - 1.0 | Metal vs. dielectric |
| `roughness` | 0.0 - 1.0 | Surface roughness |
| `emissive` | RGB tuple (0-1) | Emission color |
| `emissive_strength` | 0.0+ | Emission intensity multiplier |

## Lighting

Add point lights and directional lights to the scene:

```python
from pymotion.render.backend_3d import Light
from pymotion.utils.math import Vec3

# Point light
scene.add_light(Light(
    light_type="point",
    position=Vec3(3.0, 4.0, 2.0),
    color=(1.0, 1.0, 1.0),
    intensity=1.5,
))

# Directional light (sun-like)
scene.add_light(Light(
    light_type="directional",
    direction=Vec3(-0.5, -1.0, -0.3),
    color=(1.0, 0.95, 0.9),
    intensity=1.0,
))

# Colored accent light
scene.add_light(Light(
    light_type="point",
    position=Vec3(-2.0, 1.0, 3.0),
    color=(0.3, 0.5, 1.0),
    intensity=0.8,
))
```

The renderer supports up to 8 point lights per scene.

## Background color

Set the scene background:

```python
from pymotion.utils.color import Color

scene.set_background(Color(0.05, 0.05, 0.1))
```

## Converting to a clip

Use `to_clip()` to convert the scene into a renderable clip for your
composition:

```python
from pymotion import Composition

# Create a 3-second clip from the scene
clip = scene.to_clip(duration=90)  # 90 frames at 30 fps

comp = Composition(1920, 1080, fps=30, duration=90)
comp.add(clip)
comp.render("3d_scene.mp4")
```

The `Scene3DClip` uses `ModernGLRenderer` internally. The renderer creates
a headless OpenGL context and reads back BGRA pixel data for each frame.

## Adding pre-built models

If you build `Model3D` instances programmatically, add them directly:

```python
from pymotion.render.backend_3d import Model3D

# Build a model from vertex data (advanced)
model = Model3D(
    vertices=vertex_array,
    normals=normal_array,
    texcoords=texcoord_array,
    indices=index_array,
)
scene.add_model(model)
```

## Post-processing effects

Add 3D-specific post-processing effects to the scene:

```python
from pymotion.render.backend_3d import PostFX3D

scene.add_effect(PostFX3D(effect_type="bloom", strength=0.5))
scene.add_effect(PostFX3D(effect_type="ssao", radius=0.3))
```

## Complete example

```python
from pymotion import Composition
from pymotion.clip.scene3d import Scene3D
from pymotion.render.backend_3d import Camera, Light, PBRMaterial
from pymotion.utils.color import Color
from pymotion.utils.math import Vec3

# Set up the scene
scene = Scene3D(1920, 1080)
scene.set_background(Color(0.02, 0.02, 0.05))

# Camera
scene.camera = Camera(
    position=Vec3(3.0, 2.0, 4.0),
    target=Vec3(0.0, 0.0, 0.0),
    fov=50.0,
)

# Lights
scene.add_light(Light(
    light_type="point",
    position=Vec3(4.0, 5.0, 3.0),
    color=(1.0, 0.95, 0.9),
    intensity=2.0,
))
scene.add_light(Light(
    light_type="point",
    position=Vec3(-3.0, 2.0, -1.0),
    color=(0.4, 0.6, 1.0),
    intensity=0.8,
))

# Load model with material
material = PBRMaterial(
    albedo=(0.7, 0.3, 0.1, 1.0),
    metallic=0.9,
    roughness=0.2,
)
model = scene.load_model("assets/models/teapot.obj", material=material)

# Render as a clip
clip = scene.to_clip(duration=150)
comp = Composition(1920, 1080, fps=30, duration=150)
comp.add(clip)
comp.render("teapot.mp4")
```
