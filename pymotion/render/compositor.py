"""Frame compositor — alpha compositing and blend modes.

Composites multiple clip layers into a single frame using NumPy-vectorized
operations. Supports NORMAL, MULTIPLY, SCREEN, and ADD blend modes.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pymotion.clip.base import BlendMode
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


def composite_layers(
    background: np.ndarray[Any, Any],
    layers: list[tuple[np.ndarray[Any, Any], BlendMode, float]],
) -> np.ndarray[Any, Any]:
    """Composite multiple layers onto a background.

    Each layer is a tuple of (frame, blend_mode, opacity).
    Layers are composited in order (first = bottom, last = top).

    All operations are done in float32 to avoid integer overflow,
    then clipped and cast back to uint8.

    Args:
        background: BGRA background frame, shape (H, W, 4), dtype uint8.
        layers: List of (frame, blend_mode, opacity) tuples.

    Returns:
        Composited BGRA frame, shape (H, W, 4), dtype uint8.
    """
    result = background.astype(np.float32)

    for layer_frame, blend_mode, opacity in layers:
        layer = layer_frame.astype(np.float32)

        # Apply opacity to layer alpha
        layer[:, :, 3] *= opacity

        # Extract alpha as 0-1 factor
        layer_alpha: np.ndarray[Any, Any] = layer[:, :, 3:4] / 255.0
        bg_alpha: np.ndarray[Any, Any] = result[:, :, 3:4] / 255.0

        # Get RGB channels (0-255 float)
        layer_rgb: np.ndarray[Any, Any] = layer[:, :, :3]
        bg_rgb: np.ndarray[Any, Any] = result[:, :, :3]

        blended_rgb: np.ndarray[Any, Any]
        if blend_mode == BlendMode.NORMAL:
            blended_rgb = layer_rgb
        elif blend_mode == BlendMode.MULTIPLY:
            blended_rgb = (bg_rgb * layer_rgb) / 255.0
        elif blend_mode == BlendMode.SCREEN:
            blended_rgb = 255.0 - ((255.0 - bg_rgb) * (255.0 - layer_rgb)) / 255.0
        elif blend_mode == BlendMode.ADD:
            blended_rgb = bg_rgb + layer_rgb
        else:
            blended_rgb = layer_rgb

        # Alpha compositing (Porter-Duff "over" operator)
        out_alpha = layer_alpha + bg_alpha * (1.0 - layer_alpha)
        safe_alpha = np.where(out_alpha > 0, out_alpha, 1.0)

        out_rgb = (blended_rgb * layer_alpha + bg_rgb * bg_alpha * (1.0 - layer_alpha)) / safe_alpha

        result[:, :, :3] = out_rgb
        result[:, :, 3:4] = out_alpha * 255.0

    out: np.ndarray[Any, Any] = np.clip(result, 0, 255).astype(np.uint8)
    return out
