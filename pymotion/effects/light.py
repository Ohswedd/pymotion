"""Light effects — lens flare, god rays, neon glow, light leak.

All effects operate on BGRA numpy arrays and are stateless.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter  # type: ignore[import-untyped]

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.math import Vec2


@dataclass
class LensFlareLight(Effect):
    """Lens flare effect — renders multi-element flare at a position.

    Args:
        position: Flare source in normalized coordinates (0-1).
        intensity: Overall flare brightness.
        color: Primary flare color.
    """

    position: Vec2 = Vec2(0.5, 0.3)
    intensity: float = 0.8
    color: Color = Color(1.0, 0.95, 0.8, 1.0)

    def __init__(
        self,
        position: Vec2 | None = None,
        intensity: float = 0.8,
        color: ColorInput = "#FFF2CC",
    ) -> None:
        """Initialize LensFlareLight.

        Args:
            position: Flare source position.
            intensity: Flare brightness.
            color: Flare color.
        """
        self.position = position if position is not None else Vec2(0.5, 0.3)
        self.intensity = intensity
        self.color = Color.parse(color)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply lens flare to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with lens flare.
        """
        h, w = frame.shape[:2]
        result = frame.astype(np.float32)
        cy = self.position.y * h
        cx = self.position.x * w

        y_coords = np.arange(h, dtype=np.float32) - cy
        x_coords = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")
        dist = np.sqrt(xx * xx + yy * yy)

        b, g, r, _a = self.color.to_bgra_uint8()

        # Primary flare glow
        sigma = max(h, w) * 0.15
        glow = np.exp(-(dist * dist) / (2 * sigma * sigma)) * self.intensity

        # Secondary smaller flares along the flare axis
        for scale in [0.3, 0.15, 0.08]:
            offset_y = cy + (h / 2 - cy) * scale * 2
            offset_x = cx + (w / 2 - cx) * scale * 2
            dy = yy + cy - offset_y
            dx = xx + cx - offset_x
            d2 = np.sqrt(dy * dy + dx * dx)
            s = max(h, w) * scale * 0.5
            glow += np.exp(-(d2 * d2) / (2 * s * s)) * self.intensity * 0.3

        result[:, :, 0] += glow * b
        result[:, :, 1] += glow * g
        result[:, :, 2] += glow * r
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class GodRays(Effect):
    """God rays effect — volumetric light rays from a source point.

    Args:
        position: Light source in normalized coordinates (0-1).
        intensity: Ray brightness.
        decay: How quickly rays fade.
        samples: Number of radial blur samples.
    """

    position: Vec2 = Vec2(0.5, 0.0)
    intensity: float = 0.3
    decay: float = 0.95
    samples: int = 50

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply god rays to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with god rays.
        """
        h, w = frame.shape[:2]
        result = frame.astype(np.float32)

        # Extract bright areas as ray source
        lum = 0.299 * result[:, :, 2] + 0.587 * result[:, :, 1] + 0.114 * result[:, :, 0]
        bright_mask = (lum > 200).astype(np.float32)

        ray_layer = np.zeros((h, w), dtype=np.float32)
        cx = self.position.x * w
        cy = self.position.y * h

        y_coords = np.arange(h, dtype=np.float32)
        x_coords = np.arange(w, dtype=np.float32)
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

        # Radial blur from source
        weight = 1.0
        for i in range(1, self.samples + 1):
            t = i / self.samples * 0.1  # Small step
            sample_x = np.clip((xx + (cx - xx) * t).astype(np.intp), 0, w - 1)
            sample_y = np.clip((yy + (cy - yy) * t).astype(np.intp), 0, h - 1)
            ray_layer += bright_mask[sample_y, sample_x] * weight
            weight *= self.decay

        ray_layer *= self.intensity * 255 / max(self.samples, 1)

        result[:, :, :3] += ray_layer[:, :, np.newaxis]
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class NeonGlow(Effect):
    """Neon glow effect — colored glow around bright edges.

    Args:
        color: Glow color.
        radius: Blur radius for the glow.
        strength: Glow intensity.
        threshold: Edge detection threshold.
    """

    color: Color = Color(0.388, 0.4, 0.945, 1.0)
    radius: float = 8.0
    strength: float = 0.6
    threshold: float = 50.0

    def __init__(
        self,
        color: ColorInput = "#6366F1",
        radius: float = 8.0,
        strength: float = 0.6,
        threshold: float = 50.0,
    ) -> None:
        """Initialize NeonGlow.

        Args:
            color: Glow color.
            radius: Glow blur radius.
            strength: Glow intensity.
            threshold: Edge threshold.
        """
        self.color = Color.parse(color)
        self.radius = radius
        self.strength = strength
        self.threshold = threshold

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply neon glow to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with neon glow.
        """
        h, w = frame.shape[:2]
        result = frame.astype(np.float32)

        # Simple edge detection via luminance gradient
        lum = 0.114 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.299 * result[:, :, 2]
        # Sobel-like gradient approximation
        dy = np.abs(np.diff(lum, axis=0, prepend=lum[:1, :]))
        dx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1]))
        edges = np.sqrt(dx * dx + dy * dy)
        edge_mask = (edges > self.threshold).astype(np.float32)

        # Blur the edge mask for soft glow
        glow_mask = gaussian_filter(edge_mask, sigma=self.radius)

        b, g, r, _a = self.color.to_bgra_uint8()
        result[:, :, 0] += glow_mask * b * self.strength
        result[:, :, 1] += glow_mask * g * self.strength
        result[:, :, 2] += glow_mask * r * self.strength
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class LightLeak(Effect):
    """Light leak effect — warm color wash simulating light leaking into camera.

    Args:
        color: Leak color.
        position: Leak center in normalized coordinates.
        intensity: Leak brightness.
        size: Leak size (0-1).
    """

    color: Color = Color(1.0, 0.6, 0.2, 1.0)
    position: Vec2 = Vec2(0.8, 0.3)
    intensity: float = 0.5
    size: float = 0.4

    def __init__(
        self,
        color: ColorInput = "#FF9933",
        position: Vec2 | None = None,
        intensity: float = 0.5,
        size: float = 0.4,
    ) -> None:
        """Initialize LightLeak.

        Args:
            color: Leak color.
            position: Leak position.
            intensity: Leak brightness.
            size: Leak size.
        """
        self.color = Color.parse(color)
        self.position = position if position is not None else Vec2(0.8, 0.3)
        self.intensity = intensity
        self.size = size

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply light leak to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with light leak.
        """
        h, w = frame.shape[:2]
        result = frame.astype(np.float32)

        cy = self.position.y * h
        cx = self.position.x * w
        sigma = max(h, w) * max(self.size, 0.01)

        y_coords = np.arange(h, dtype=np.float32) - cy
        x_coords = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")
        dist_sq = xx * xx + yy * yy

        leak = np.exp(-dist_sq / (2 * sigma * sigma)) * self.intensity

        b, g, r, _a = self.color.to_bgra_uint8()
        result[:, :, 0] += leak * b
        result[:, :, 1] += leak * g
        result[:, :, 2] += leak * r
        return np.clip(result, 0, 255).astype(np.uint8)
