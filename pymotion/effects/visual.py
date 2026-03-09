"""Visual effects — GaussianBlur and Vignette for Phase 0.1.

All effects operate on BGRA numpy arrays and are stateless.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter  # type: ignore[import-untyped]

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect


@dataclass
class GaussianBlur(Effect):
    """Gaussian blur effect.

    Args:
        radius: Blur radius in pixels.
    """

    radius: float = 5.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply Gaussian blur to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Blurred BGRA frame.
        """
        if self.radius <= 0:
            return frame.copy()

        result = frame.astype(np.float32)
        # Blur RGB channels, preserve alpha
        for c in range(3):
            result[:, :, c] = gaussian_filter(result[:, :, c], sigma=self.radius)
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class Vignette(Effect):
    """Vignette effect — darkens edges of the frame.

    Args:
        strength: How dark the vignette is (0.0 = none, 1.0 = full).
        radius: Size of the clear center area (0.0-1.0).
        feather: How gradual the falloff is (0.0-1.0).
    """

    strength: float = 0.5
    radius: float = 0.8
    feather: float = 0.3

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply vignette effect to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with vignette applied.
        """
        h, w = frame.shape[:2]

        # Create distance map from center
        y = np.linspace(-1, 1, h, dtype=np.float32)
        x = np.linspace(-1, 1, w, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        dist = np.sqrt(xx**2 + yy**2)

        # Create vignette mask
        vignette = 1.0 - np.clip((dist - self.radius) / max(self.feather, 0.001), 0.0, 1.0)
        vignette = 1.0 - self.strength * (1.0 - vignette)

        result = frame.astype(np.float32)
        # Apply to BGR channels only, preserve alpha
        for c in range(3):
            result[:, :, c] *= vignette

        return np.clip(result, 0, 255).astype(np.uint8)
