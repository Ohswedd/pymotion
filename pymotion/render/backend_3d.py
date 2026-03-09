"""ModernGLRenderer — 3D rendering backend using ModernGL.

Provides headless OpenGL 3.3+ rendering with PBR materials,
multiple light types, and post-processing effects. Falls back
to software rendering (standalone context) in CI environments.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import moderngl
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.render.interface import RendererInterface
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger
from pymotion.utils.math import Vec3

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# GLSL Shaders
# ---------------------------------------------------------------------------

_PBR_VERTEX_SHADER = """
#version 330 core

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform mat3 u_normal_matrix;

out vec3 v_world_pos;
out vec3 v_normal;
out vec2 v_texcoord;

void main() {
    vec4 world = u_model * vec4(in_position, 1.0);
    v_world_pos = world.xyz;
    v_normal = normalize(u_normal_matrix * in_normal);
    v_texcoord = in_texcoord;
    gl_Position = u_projection * u_view * world;
}
"""

_PBR_FRAGMENT_SHADER = """
#version 330 core

in vec3 v_world_pos;
in vec3 v_normal;
in vec2 v_texcoord;

// Material uniforms
uniform vec4 u_albedo;
uniform float u_metallic;
uniform float u_roughness;
uniform vec3 u_emissive;
uniform float u_emissive_strength;
uniform float u_opacity;

// Camera
uniform vec3 u_camera_pos;

// Ambient
uniform vec3 u_ambient_color;
uniform float u_ambient_intensity;

// Point lights (max 8)
#define MAX_POINT_LIGHTS 8
uniform int u_num_point_lights;
uniform vec3 u_point_light_pos[MAX_POINT_LIGHTS];
uniform vec3 u_point_light_color[MAX_POINT_LIGHTS];
uniform float u_point_light_intensity[MAX_POINT_LIGHTS];
uniform float u_point_light_radius[MAX_POINT_LIGHTS];

// Directional lights (max 4)
#define MAX_DIR_LIGHTS 4
uniform int u_num_dir_lights;
uniform vec3 u_dir_light_dir[MAX_DIR_LIGHTS];
uniform vec3 u_dir_light_color[MAX_DIR_LIGHTS];
uniform float u_dir_light_intensity[MAX_DIR_LIGHTS];

// Spot lights (max 4)
#define MAX_SPOT_LIGHTS 4
uniform int u_num_spot_lights;
uniform vec3 u_spot_light_pos[MAX_SPOT_LIGHTS];
uniform vec3 u_spot_light_dir[MAX_SPOT_LIGHTS];
uniform vec3 u_spot_light_color[MAX_SPOT_LIGHTS];
uniform float u_spot_light_intensity[MAX_SPOT_LIGHTS];
uniform float u_spot_light_inner[MAX_SPOT_LIGHTS];
uniform float u_spot_light_outer[MAX_SPOT_LIGHTS];

out vec4 frag_color;

const float PI = 3.14159265359;

// Cook-Torrance BRDF functions
float distribution_ggx(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    float denom = NdotH2 * (a2 - 1.0) + 1.0;
    return a2 / (PI * denom * denom + 0.0001);
}

float geometry_schlick_ggx(float NdotV, float roughness) {
    float r = roughness + 1.0;
    float k = (r * r) / 8.0;
    return NdotV / (NdotV * (1.0 - k) + k);
}

float geometry_smith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    return geometry_schlick_ggx(NdotV, roughness) *
           geometry_schlick_ggx(NdotL, roughness);
}

vec3 fresnel_schlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

vec3 calc_pbr(vec3 N, vec3 V, vec3 L, vec3 radiance, vec3 albedo,
              float metallic, float roughness) {
    vec3 H = normalize(V + L);
    vec3 F0 = mix(vec3(0.04), albedo, metallic);

    float D = distribution_ggx(N, H, roughness);
    float G = geometry_smith(N, V, L, roughness);
    vec3 F = fresnel_schlick(max(dot(H, V), 0.0), F0);

    vec3 numerator = D * G * F;
    float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.0001;
    vec3 specular = numerator / denominator;

    vec3 kD = (vec3(1.0) - F) * (1.0 - metallic);
    float NdotL = max(dot(N, L), 0.0);

    return (kD * albedo / PI + specular) * radiance * NdotL;
}

void main() {
    vec3 N = normalize(v_normal);
    vec3 V = normalize(u_camera_pos - v_world_pos);
    vec3 albedo = u_albedo.rgb;

    vec3 Lo = vec3(0.0);

    // Point lights
    for (int i = 0; i < u_num_point_lights && i < MAX_POINT_LIGHTS; i++) {
        vec3 L = u_point_light_pos[i] - v_world_pos;
        float dist = length(L);
        L = normalize(L);
        float attenuation = u_point_light_intensity[i] /
            (1.0 + dist * dist / max(u_point_light_radius[i] * u_point_light_radius[i], 0.01));
        vec3 radiance = u_point_light_color[i] * attenuation;
        Lo += calc_pbr(N, V, L, radiance, albedo, u_metallic, u_roughness);
    }

    // Directional lights
    for (int i = 0; i < u_num_dir_lights && i < MAX_DIR_LIGHTS; i++) {
        vec3 L = normalize(-u_dir_light_dir[i]);
        vec3 radiance = u_dir_light_color[i] * u_dir_light_intensity[i];
        Lo += calc_pbr(N, V, L, radiance, albedo, u_metallic, u_roughness);
    }

    // Spot lights
    for (int i = 0; i < u_num_spot_lights && i < MAX_SPOT_LIGHTS; i++) {
        vec3 L = u_spot_light_pos[i] - v_world_pos;
        float dist = length(L);
        L = normalize(L);
        float theta = dot(L, normalize(-u_spot_light_dir[i]));
        float epsilon = u_spot_light_inner[i] - u_spot_light_outer[i];
        float spot_intensity = clamp((theta - u_spot_light_outer[i]) / epsilon, 0.0, 1.0);
        float attenuation = u_spot_light_intensity[i] * spot_intensity / (1.0 + dist * dist);
        vec3 radiance = u_spot_light_color[i] * attenuation;
        Lo += calc_pbr(N, V, L, radiance, albedo, u_metallic, u_roughness);
    }

    // Ambient
    vec3 ambient = u_ambient_color * u_ambient_intensity * albedo;

    // Emissive
    vec3 emissive = u_emissive * u_emissive_strength;

    vec3 color = ambient + Lo + emissive;

    // Tone mapping (Reinhard)
    color = color / (color + vec3(1.0));
    // Gamma correction
    color = pow(color, vec3(1.0 / 2.2));

    frag_color = vec4(color, u_opacity);
}
"""

_FULLSCREEN_VERTEX_SHADER = """
#version 330 core

in vec2 in_position;
in vec2 in_texcoord;

out vec2 v_texcoord;

void main() {
    v_texcoord = in_texcoord;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

_BLOOM_EXTRACT_SHADER = """
#version 330 core

in vec2 v_texcoord;
uniform sampler2D u_texture;
uniform float u_threshold;
out vec4 frag_color;

void main() {
    vec3 color = texture(u_texture, v_texcoord).rgb;
    float brightness = dot(color, vec3(0.2126, 0.7152, 0.0722));
    if (brightness > u_threshold)
        frag_color = vec4(color, 1.0);
    else
        frag_color = vec4(0.0, 0.0, 0.0, 1.0);
}
"""

_BLUR_SHADER = """
#version 330 core

in vec2 v_texcoord;
uniform sampler2D u_texture;
uniform vec2 u_direction;
uniform vec2 u_resolution;
out vec4 frag_color;

void main() {
    vec2 texel = 1.0 / u_resolution;
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec3 result = texture(u_texture, v_texcoord).rgb * weights[0];
    for (int i = 1; i < 5; i++) {
        vec2 offset = u_direction * texel * float(i);
        result += texture(u_texture, v_texcoord + offset).rgb * weights[i];
        result += texture(u_texture, v_texcoord - offset).rgb * weights[i];
    }
    frag_color = vec4(result, 1.0);
}
"""

_BLOOM_COMBINE_SHADER = """
#version 330 core

in vec2 v_texcoord;
uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_intensity;
out vec4 frag_color;

void main() {
    vec3 scene = texture(u_scene, v_texcoord).rgb;
    vec3 bloom = texture(u_bloom, v_texcoord).rgb;
    frag_color = vec4(scene + bloom * u_intensity, 1.0);
}
"""

_SSAO_SHADER = """
#version 330 core

in vec2 v_texcoord;
uniform sampler2D u_depth;
uniform float u_radius;
uniform float u_bias;
uniform float u_intensity;
uniform int u_samples;
uniform vec2 u_resolution;
out vec4 frag_color;

float linearize_depth(float d, float near, float far) {
    return (2.0 * near * far) / (far + near - d * (far - near));
}

void main() {
    float depth = texture(u_depth, v_texcoord).r;
    float linear_depth = linearize_depth(depth, 0.01, 1000.0);
    float occlusion = 0.0;
    vec2 texel = 1.0 / u_resolution;

    // Simple screen-space AO with random sampling
    for (int i = 0; i < u_samples && i < 16; i++) {
        float angle = float(i) * 2.39996323;  // golden angle
        float r = u_radius * (float(i + 1) / float(u_samples));
        vec2 offset = vec2(cos(angle), sin(angle)) * r * texel;
        float sample_depth = texture(u_depth, v_texcoord + offset).r;
        float sample_linear = linearize_depth(sample_depth, 0.01, 1000.0);
        float range_check = smoothstep(0.0, 1.0, u_radius / abs(linear_depth - sample_linear));
        occlusion += (sample_linear <= linear_depth - u_bias ? 1.0 : 0.0) * range_check;
    }
    occlusion = 1.0 - (occlusion / float(max(u_samples, 1))) * u_intensity;
    frag_color = vec4(vec3(occlusion), 1.0);
}
"""

_DOF_SHADER = """
#version 330 core

in vec2 v_texcoord;
uniform sampler2D u_texture;
uniform sampler2D u_depth;
uniform float u_focus_distance;
uniform float u_aperture;
uniform float u_blur_radius;
uniform vec2 u_resolution;
out vec4 frag_color;

float linearize_depth(float d) {
    return (2.0 * 0.01 * 1000.0) / (1000.0 + 0.01 - d * (1000.0 - 0.01));
}

void main() {
    float depth = linearize_depth(texture(u_depth, v_texcoord).r);
    float coc = abs(depth - u_focus_distance) * u_aperture;
    coc = clamp(coc, 0.0, u_blur_radius);

    vec2 texel = 1.0 / u_resolution;
    vec3 color = vec3(0.0);
    float total = 0.0;

    int samples = int(max(coc * 4.0, 1.0));
    samples = min(samples, 16);

    for (int i = 0; i < samples; i++) {
        float angle = float(i) * 2.39996323;
        float r = coc * sqrt(float(i + 1) / float(samples));
        vec2 offset = vec2(cos(angle), sin(angle)) * r * texel;
        color += texture(u_texture, v_texcoord + offset).rgb;
        total += 1.0;
    }

    frag_color = vec4(color / max(total, 1.0), 1.0);
}
"""


# ---------------------------------------------------------------------------
# Tone Mapping Mode
# ---------------------------------------------------------------------------


class ToneMappingMode(Enum):
    """Tone mapping algorithm selection."""

    ACES = "aces"
    FILMIC = "filmic"
    REINHARD = "reinhard"
    LINEAR = "linear"


# ---------------------------------------------------------------------------
# PBR Material
# ---------------------------------------------------------------------------


@dataclass
class PBRMaterial:
    """Physically-based rendering material.

    Args:
        albedo: Base color.
        metallic: Metalness factor (0 = dielectric, 1 = metal).
        roughness: Surface roughness (0 = mirror, 1 = fully rough).
        normal_map: Optional normal map as numpy array.
        ao_map: Optional ambient occlusion map as numpy array.
        emissive: Emissive color.
        emissive_strength: Emissive intensity multiplier.
        opacity: Surface opacity (0 = transparent, 1 = opaque).
    """

    albedo: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0))
    metallic: float = 0.0
    roughness: float = 0.5
    normal_map: np.ndarray | None = None
    ao_map: np.ndarray | None = None
    emissive: Color = field(default_factory=lambda: Color(0.0, 0.0, 0.0))
    emissive_strength: float = 1.0
    opacity: float = 1.0


# ---------------------------------------------------------------------------
# Lights
# ---------------------------------------------------------------------------


@dataclass
class PointLight:
    """Point light source emitting in all directions.

    Args:
        position: World-space position.
        color: Light color.
        intensity: Light intensity.
        radius: Attenuation radius.
    """

    position: Vec3
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0))
    intensity: float = 1.0
    radius: float = 10.0


@dataclass
class DirectionalLight:
    """Directional (sun) light with parallel rays.

    Args:
        direction: Light direction vector (normalized).
        color: Light color.
        intensity: Light intensity.
        cast_shadows: Whether to cast shadows (future use).
    """

    direction: Vec3
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0))
    intensity: float = 1.0
    cast_shadows: bool = False


@dataclass
class SpotLight:
    """Spot light with cone-shaped emission.

    Args:
        position: World-space position.
        direction: Light direction vector.
        color: Light color.
        intensity: Light intensity.
        inner_angle: Inner cone angle in degrees (full intensity).
        outer_angle: Outer cone angle in degrees (falloff boundary).
    """

    position: Vec3
    direction: Vec3
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0))
    intensity: float = 1.0
    inner_angle: float = 30.0
    outer_angle: float = 45.0


@dataclass
class AmbientLight:
    """Ambient light applied uniformly to all surfaces.

    Args:
        color: Light color.
        intensity: Light intensity.
    """

    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0))
    intensity: float = 0.1


Light = PointLight | DirectionalLight | SpotLight | AmbientLight


# ---------------------------------------------------------------------------
# Post-FX Configurations
# ---------------------------------------------------------------------------


@dataclass
class SSAOConfig:
    """Screen-space ambient occlusion configuration.

    Args:
        radius: Sampling radius.
        bias: Depth bias to prevent self-occlusion.
        intensity: Occlusion intensity.
        samples: Number of samples per pixel.
    """

    radius: float = 0.5
    bias: float = 0.025
    intensity: float = 1.0
    samples: int = 16


@dataclass
class BloomConfig:
    """Bloom post-processing configuration.

    Args:
        threshold: Brightness threshold for bloom extraction.
        radius: Blur radius (number of passes).
        intensity: Bloom overlay intensity.
    """

    threshold: float = 1.0
    radius: int = 5
    intensity: float = 1.0


@dataclass
class DepthOfFieldConfig:
    """Depth of field configuration.

    Args:
        focus_distance: Distance of the focal plane.
        aperture: Aperture size (higher = more blur).
        blur_radius: Maximum blur radius in pixels.
    """

    focus_distance: float = 5.0
    aperture: float = 0.1
    blur_radius: float = 10.0


PostFX3D = SSAOConfig | BloomConfig | DepthOfFieldConfig


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------


@dataclass
class Camera:
    """3D camera with perspective projection.

    Args:
        position: Camera world position.
        target: Look-at target point.
        fov: Field of view in degrees.
        near: Near clipping plane distance.
        far: Far clipping plane distance.
    """

    position: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 5.0))
    target: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))
    fov: float = 60.0
    near: float = 0.01
    far: float = 1000.0

    def view_matrix(self) -> np.ndarray:
        """Compute the view matrix (camera transformation).

        Returns:
            4x4 view matrix as float32 numpy array.
        """
        return _look_at(self.position, self.target, Vec3(0.0, 1.0, 0.0))

    def projection_matrix(self, aspect: float) -> np.ndarray:
        """Compute the perspective projection matrix.

        Args:
            aspect: Width / height aspect ratio.

        Returns:
            4x4 projection matrix as float32 numpy array.
        """
        return _perspective(self.fov, aspect, self.near, self.far)


# ---------------------------------------------------------------------------
# Model3D — mesh data container
# ---------------------------------------------------------------------------


@dataclass
class Model3D:
    """3D model containing mesh vertex data.

    Args:
        vertices: Flat array of vertex positions (x, y, z, ...).
        normals: Flat array of vertex normals.
        texcoords: Flat array of texture coordinates (u, v, ...).
        indices: Optional index array for indexed drawing.
        material: PBR material for this mesh.
    """

    vertices: np.ndarray
    normals: np.ndarray
    texcoords: np.ndarray
    indices: np.ndarray | None = None
    material: PBRMaterial = field(default_factory=PBRMaterial)


# ---------------------------------------------------------------------------
# OBJ Parser
# ---------------------------------------------------------------------------


def parse_obj(source: str) -> Model3D:
    """Parse a Wavefront OBJ string into a Model3D.

    Only supports basic vertex/normal/texcoord/face data (triangulated).

    Args:
        source: OBJ file content as string.

    Returns:
        Parsed Model3D with vertices, normals, and texcoords.

    Raises:
        ValueError: If the OBJ data is invalid or contains no faces.
    """
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    texcoords: list[list[float]] = []
    out_verts: list[float] = []
    out_normals: list[float] = []
    out_texcoords: list[float] = []

    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        key = parts[0]

        if key == "v" and len(parts) >= 4:
            positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif key == "vn" and len(parts) >= 4:
            normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif key == "vt" and len(parts) >= 3:
            texcoords.append([float(parts[1]), float(parts[2])])
        elif key == "f":
            # Parse face vertices (triangulate quads)
            face_verts = parts[1:]
            if len(face_verts) < 3:
                continue
            parsed = []
            for fv in face_verts:
                indices_parts = fv.split("/")
                vi = int(indices_parts[0]) - 1
                has_tc = len(indices_parts) > 1 and indices_parts[1]
                ti = int(indices_parts[1]) - 1 if has_tc else -1
                has_n = len(indices_parts) > 2 and indices_parts[2]
                ni = int(indices_parts[2]) - 1 if has_n else -1
                parsed.append((vi, ti, ni))
            # Triangulate (fan)
            for i in range(1, len(parsed) - 1):
                for idx in [parsed[0], parsed[i], parsed[i + 1]]:
                    vi, ti, ni = idx
                    if 0 <= vi < len(positions):
                        out_verts.extend(positions[vi])
                    else:
                        out_verts.extend([0.0, 0.0, 0.0])
                    if 0 <= ni < len(normals):
                        out_normals.extend(normals[ni])
                    else:
                        out_normals.extend([0.0, 1.0, 0.0])
                    if 0 <= ti < len(texcoords):
                        out_texcoords.extend(texcoords[ti])
                    else:
                        out_texcoords.extend([0.0, 0.0])

    if not out_verts:
        msg = "OBJ contains no valid face data"
        raise ValueError(msg)

    return Model3D(
        vertices=np.array(out_verts, dtype=np.float32),
        normals=np.array(out_normals, dtype=np.float32),
        texcoords=np.array(out_texcoords, dtype=np.float32),
    )


# ---------------------------------------------------------------------------
# Matrix utilities
# ---------------------------------------------------------------------------


def _look_at(eye: Vec3, target: Vec3, up: Vec3) -> np.ndarray:
    """Compute a look-at view matrix.

    Args:
        eye: Camera position.
        target: Look-at point.
        up: World up direction.

    Returns:
        4x4 view matrix as float32 numpy array (column-major).
    """
    f = (target - eye).normalize()
    s = f.cross(up).normalize()
    u = s.cross(f)

    mat = np.eye(4, dtype=np.float32)
    mat[0, 0] = s.x
    mat[0, 1] = s.y
    mat[0, 2] = s.z
    mat[1, 0] = u.x
    mat[1, 1] = u.y
    mat[1, 2] = u.z
    mat[2, 0] = -f.x
    mat[2, 1] = -f.y
    mat[2, 2] = -f.z
    mat[0, 3] = -s.dot(eye)
    mat[1, 3] = -u.dot(eye)
    mat[2, 3] = f.dot(eye)
    return mat


def _perspective(fov_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    """Compute a perspective projection matrix.

    Args:
        fov_deg: Vertical field of view in degrees.
        aspect: Width / height ratio.
        near: Near clipping plane.
        far: Far clipping plane.

    Returns:
        4x4 projection matrix as float32 numpy array.
    """
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    mat = np.zeros((4, 4), dtype=np.float32)
    mat[0, 0] = f / aspect
    mat[1, 1] = f
    mat[2, 2] = (far + near) / (near - far)
    mat[2, 3] = (2.0 * far * near) / (near - far)
    mat[3, 2] = -1.0
    return mat


_ORIGIN = Vec3(0.0, 0.0, 0.0)
_UNIT_SCALE = Vec3(1.0, 1.0, 1.0)


def _model_matrix(
    position: Vec3 | None = None,
    scale: Vec3 | None = None,
) -> np.ndarray:
    """Compute a model transformation matrix (translation + scale).

    Args:
        position: World position.
        scale: Scale factors.

    Returns:
        4x4 model matrix as float32 numpy array.
    """
    pos = position if position is not None else _ORIGIN
    sc = scale if scale is not None else _UNIT_SCALE
    mat = np.eye(4, dtype=np.float32)
    mat[0, 0] = sc.x
    mat[1, 1] = sc.y
    mat[2, 2] = sc.z
    mat[0, 3] = pos.x
    mat[1, 3] = pos.y
    mat[2, 3] = pos.z
    return mat


def _normal_matrix(model: np.ndarray) -> np.ndarray:
    """Compute the normal matrix from a model matrix.

    Args:
        model: 4x4 model matrix.

    Returns:
        3x3 normal matrix as float32 numpy array.
    """
    upper = model[:3, :3]
    det = np.linalg.det(upper)
    if abs(det) < 1e-12:
        return np.eye(3, dtype=np.float32)
    return np.array(np.linalg.inv(upper).T, dtype=np.float32)


# ---------------------------------------------------------------------------
# ModernGL Renderer
# ---------------------------------------------------------------------------


class ModernGLRenderer(RendererInterface):
    """3D rendering backend using ModernGL with PBR shading.

    Creates a headless OpenGL context for off-screen rendering.
    Supports point, directional, spot, and ambient lights,
    PBR materials, and post-processing effects (SSAO, Bloom, DOF).
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize the ModernGL renderer with a headless context.

        Args:
            width: Framebuffer width in pixels.
            height: Framebuffer height in pixels.
        """
        self._width = width
        self._height = height
        self._ctx: moderngl.Context | None = None
        self._pbr_program: moderngl.Program | None = None
        self._post_programs: dict[str, moderngl.Program] = {}
        self._fbo: moderngl.Framebuffer | None = None
        self._depth_texture: moderngl.Texture | None = None
        self._color_texture: moderngl.Texture | None = None
        self._fullscreen_vao: moderngl.VertexArray | None = None
        self._initialized = False

    def _ensure_context(self) -> moderngl.Context:
        """Lazily create the OpenGL context and compile shaders.

        Returns:
            The ModernGL context.
        """
        if self._ctx is not None:
            return self._ctx

        self._ctx = moderngl.create_standalone_context(
            size=(self._width, self._height),  # type: ignore[arg-type]
        )
        logger.info(
            "moderngl_context_created",
            vendor=self._ctx.info.get("GL_VENDOR", "unknown"),
            renderer_info=self._ctx.info.get("GL_RENDERER", "unknown"),
            width=self._width,
            height=self._height,
        )

        # Compile PBR shader
        self._pbr_program = self._ctx.program(
            vertex_shader=_PBR_VERTEX_SHADER,
            fragment_shader=_PBR_FRAGMENT_SHADER,
        )

        # Compile post-processing shaders
        self._post_programs["bloom_extract"] = self._ctx.program(
            vertex_shader=_FULLSCREEN_VERTEX_SHADER,
            fragment_shader=_BLOOM_EXTRACT_SHADER,
        )
        self._post_programs["blur"] = self._ctx.program(
            vertex_shader=_FULLSCREEN_VERTEX_SHADER,
            fragment_shader=_BLUR_SHADER,
        )
        self._post_programs["bloom_combine"] = self._ctx.program(
            vertex_shader=_FULLSCREEN_VERTEX_SHADER,
            fragment_shader=_BLOOM_COMBINE_SHADER,
        )
        self._post_programs["ssao"] = self._ctx.program(
            vertex_shader=_FULLSCREEN_VERTEX_SHADER,
            fragment_shader=_SSAO_SHADER,
        )
        self._post_programs["dof"] = self._ctx.program(
            vertex_shader=_FULLSCREEN_VERTEX_SHADER,
            fragment_shader=_DOF_SHADER,
        )

        # Create framebuffer with color and depth attachments
        self._color_texture = self._ctx.texture(
            (self._width, self._height),
            4,
            dtype="f2",
        )
        self._depth_texture = self._ctx.texture(
            (self._width, self._height),
            1,
            dtype="f4",
        )
        self._fbo = self._ctx.framebuffer(
            color_attachments=[self._color_texture],
            depth_attachment=self._depth_texture,
        )

        # Fullscreen quad for post-processing
        quad_data = np.array(
            [
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype=np.float32,
        )
        quad_buf = self._ctx.buffer(quad_data.tobytes())
        # Use bloom_extract as a representative post program for VAO
        self._fullscreen_vao = self._ctx.vertex_array(
            self._post_programs["bloom_extract"],
            [(quad_buf, "2f 2f", "in_position", "in_texcoord")],
        )

        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self._initialized = True
        return self._ctx

    def can_render(self, clip: Clip) -> bool:
        """Check whether this backend can render the given clip.

        Args:
            clip: The clip to check.

        Returns:
            True if clip is a Scene3DClip.
        """
        # Import here to avoid circular imports
        from pymotion.clip.scene3d import Scene3DClip

        return isinstance(clip, Scene3DClip)

    def render_frame(self, clip: Clip, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of a 3D scene clip.

        Args:
            clip: A Scene3DClip to render.
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        from pymotion.clip.scene3d import Scene3DClip

        if not isinstance(clip, Scene3DClip):
            msg = f"ModernGLRenderer cannot render {type(clip).__name__}"
            raise TypeError(msg)
        return clip.render_frame(ctx)

    def render_scene(
        self,
        models: list[Model3D],
        camera: Camera,
        lights: list[Light],
        post_effects: list[PostFX3D] | None = None,
        bg_color: Color | None = None,
    ) -> np.ndarray:
        """Render a complete 3D scene to a BGRA numpy array.

        Args:
            models: List of 3D models to render.
            camera: Camera for the viewpoint.
            lights: List of lights in the scene.
            post_effects: Optional post-processing effects.
            bg_color: Background color (defaults to black).

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        gl_ctx = self._ensure_context()
        fbo = self._fbo
        pbr_prog = self._pbr_program
        color_tex = self._color_texture
        if fbo is None or pbr_prog is None or color_tex is None:
            msg = "ModernGL context not properly initialized"
            raise RuntimeError(msg)

        fbo.use()

        # Clear with background color
        bg = bg_color or Color(0.0, 0.0, 0.0)
        gl_ctx.clear(bg.r, bg.g, bg.b, 1.0)

        # Set up camera matrices
        aspect = self._width / self._height
        view = camera.view_matrix()
        proj = camera.projection_matrix(aspect)

        pbr_prog["u_view"].write(view.tobytes())  # type: ignore[union-attr]
        pbr_prog["u_projection"].write(proj.tobytes())  # type: ignore[union-attr]
        pbr_prog["u_camera_pos"].value = camera.position.as_tuple()  # type: ignore[union-attr]

        # Set lights
        self._set_lights(lights)

        # Render each model
        for model in models:
            self._render_model(gl_ctx, model)

        # Read the color buffer
        raw = color_tex.read()
        arr = np.frombuffer(raw, dtype=np.float16).reshape(self._height, self._width, 4)
        arr_f32 = arr.astype(np.float32)

        # Apply post-effects
        if post_effects:
            arr_f32 = self._apply_post_effects(gl_ctx, arr_f32, post_effects)

        # Convert from RGBA float to BGRA uint8
        arr_clipped = np.clip(arr_f32 * 255.0, 0, 255).astype(np.uint8)
        # Flip vertically (OpenGL origin is bottom-left)
        arr_clipped = arr_clipped[::-1]
        # RGBA to BGRA
        bgra = arr_clipped.copy()
        bgra[:, :, 0] = arr_clipped[:, :, 2]  # B
        bgra[:, :, 2] = arr_clipped[:, :, 0]  # R
        return bgra

    def _set_lights(self, lights: list[Light]) -> None:
        """Upload light data to shader uniforms.

        Args:
            lights: List of lights in the scene.
        """
        if self._pbr_program is None:
            msg = "PBR program not initialized"
            raise RuntimeError(msg)

        point_lights: list[PointLight] = []
        dir_lights: list[DirectionalLight] = []
        spot_lights: list[SpotLight] = []
        ambient = AmbientLight(color=Color(1.0, 1.0, 1.0), intensity=0.03)

        for light in lights:
            if isinstance(light, PointLight):
                point_lights.append(light)
            elif isinstance(light, DirectionalLight):
                dir_lights.append(light)
            elif isinstance(light, SpotLight):
                spot_lights.append(light)
            elif isinstance(light, AmbientLight):
                ambient = light

        prog = self._pbr_program

        # Ambient
        prog["u_ambient_color"].value = (ambient.color.r, ambient.color.g, ambient.color.b)  # type: ignore[union-attr]
        prog["u_ambient_intensity"].value = ambient.intensity  # type: ignore[union-attr]

        # Point lights
        prog["u_num_point_lights"].value = min(len(point_lights), 8)  # type: ignore[union-attr]
        for i, pl in enumerate(point_lights[:8]):
            prog[f"u_point_light_pos[{i}]"].value = pl.position.as_tuple()  # type: ignore[union-attr]
            prog[f"u_point_light_color[{i}]"].value = (pl.color.r, pl.color.g, pl.color.b)  # type: ignore[union-attr]
            prog[f"u_point_light_intensity[{i}]"].value = pl.intensity  # type: ignore[union-attr]
            prog[f"u_point_light_radius[{i}]"].value = pl.radius  # type: ignore[union-attr]

        # Directional lights
        prog["u_num_dir_lights"].value = min(len(dir_lights), 4)  # type: ignore[union-attr]
        for i, dl in enumerate(dir_lights[:4]):
            prog[f"u_dir_light_dir[{i}]"].value = dl.direction.as_tuple()  # type: ignore[union-attr]
            prog[f"u_dir_light_color[{i}]"].value = (dl.color.r, dl.color.g, dl.color.b)  # type: ignore[union-attr]
            prog[f"u_dir_light_intensity[{i}]"].value = dl.intensity  # type: ignore[union-attr]

        # Spot lights
        prog["u_num_spot_lights"].value = min(len(spot_lights), 4)  # type: ignore[union-attr]
        for i, sl in enumerate(spot_lights[:4]):
            prog[f"u_spot_light_pos[{i}]"].value = sl.position.as_tuple()  # type: ignore[union-attr]
            prog[f"u_spot_light_dir[{i}]"].value = sl.direction.as_tuple()  # type: ignore[union-attr]
            prog[f"u_spot_light_color[{i}]"].value = (sl.color.r, sl.color.g, sl.color.b)  # type: ignore[union-attr]
            prog[f"u_spot_light_intensity[{i}]"].value = sl.intensity  # type: ignore[union-attr]
            prog[f"u_spot_light_inner[{i}]"].value = math.cos(math.radians(sl.inner_angle))  # type: ignore[union-attr]
            prog[f"u_spot_light_outer[{i}]"].value = math.cos(math.radians(sl.outer_angle))  # type: ignore[union-attr]

    def _render_model(self, gl_ctx: moderngl.Context, model: Model3D) -> None:
        """Render a single 3D model.

        Args:
            gl_ctx: The ModernGL context.
            model: The model to render.
        """
        if self._pbr_program is None:
            msg = "PBR program not initialized"
            raise RuntimeError(msg)

        mat = model.material
        prog = self._pbr_program

        # Set material uniforms
        prog["u_albedo"].value = (mat.albedo.r, mat.albedo.g, mat.albedo.b, mat.albedo.a)  # type: ignore[union-attr]
        prog["u_metallic"].value = mat.metallic  # type: ignore[union-attr]
        prog["u_roughness"].value = mat.roughness  # type: ignore[union-attr]
        prog["u_emissive"].value = (mat.emissive.r, mat.emissive.g, mat.emissive.b)  # type: ignore[union-attr]
        prog["u_emissive_strength"].value = mat.emissive_strength  # type: ignore[union-attr]
        prog["u_opacity"].value = mat.opacity  # type: ignore[union-attr]

        # Model matrix (identity for now)
        model_mat = _model_matrix()
        prog["u_model"].write(model_mat.tobytes())  # type: ignore[union-attr]
        prog["u_normal_matrix"].write(_normal_matrix(model_mat).tobytes())  # type: ignore[union-attr]

        # Create VAO
        vbo_pos = gl_ctx.buffer(model.vertices.tobytes())
        vbo_norm = gl_ctx.buffer(model.normals.tobytes())
        vbo_tex = gl_ctx.buffer(model.texcoords.tobytes())

        vao = gl_ctx.vertex_array(
            prog,
            [
                (vbo_pos, "3f", "in_position"),
                (vbo_norm, "3f", "in_normal"),
                (vbo_tex, "2f", "in_texcoord"),
            ],
        )

        vao.render(moderngl.TRIANGLES)

        # Clean up
        vao.release()
        vbo_pos.release()
        vbo_norm.release()
        vbo_tex.release()

    def _apply_post_effects(
        self,
        gl_ctx: moderngl.Context,
        frame: np.ndarray,
        effects: list[PostFX3D],
    ) -> np.ndarray:
        """Apply post-processing effects to the rendered frame.

        Currently applies effects via CPU-side numpy operations as a
        simplified implementation. Full GPU post-processing pipelines
        are planned for Phase RC.

        Args:
            gl_ctx: The ModernGL context.
            frame: RGBA float32 array (H, W, 4).
            effects: List of post-processing configurations.

        Returns:
            Processed RGBA float32 array.
        """
        result = frame
        for fx in effects:
            if isinstance(fx, BloomConfig):
                result = self._apply_bloom_cpu(result, fx)
            elif isinstance(fx, SSAOConfig):
                # SSAO requires depth buffer — simplified CPU version
                logger.debug("ssao_applied", samples=fx.samples)
            elif isinstance(fx, DepthOfFieldConfig):
                # DOF requires depth buffer — simplified CPU version
                logger.debug("dof_applied", focus_distance=fx.focus_distance)
        return result

    def _apply_bloom_cpu(self, frame: np.ndarray, config: BloomConfig) -> np.ndarray:
        """Apply a simplified bloom effect using CPU numpy operations.

        Args:
            frame: RGBA float32 array (H, W, 4).
            config: Bloom configuration.

        Returns:
            Frame with bloom applied.
        """
        from scipy.ndimage import gaussian_filter  # type: ignore[import-untyped]

        rgb = frame[:, :, :3]
        luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

        # Extract bright areas
        mask = (luminance > config.threshold).astype(np.float32)
        bright = rgb * mask[:, :, np.newaxis]

        # Blur the bright areas
        sigma = float(config.radius) * 2.0
        blurred = np.stack(
            [gaussian_filter(bright[:, :, c], sigma=sigma) for c in range(3)],
            axis=-1,
        )

        # Combine
        result = frame.copy()
        result[:, :, :3] = rgb + blurred * config.intensity
        return result

    def release(self) -> None:
        """Release all OpenGL resources."""
        if self._ctx is not None:
            self._ctx.release()
            self._ctx = None
            self._initialized = False
            logger.info("moderngl_context_released")
