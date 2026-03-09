"""Color pipeline — color space conversion, LUT, and tone mapping.

Phase 0.1 provides sRGB passthrough only. LUT support will be added
in a later phase.
"""

from __future__ import annotations

import numpy as np

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


def apply_color_pipeline(
    frame: np.ndarray,
    color_space: str = "srgb",
) -> np.ndarray:
    """Apply the color pipeline to a rendered frame.

    In Phase 0.1, this is a passthrough for sRGB content.
    Future phases will add LUT application, color grading,
    and HDR tone mapping.

    Args:
        frame: BGRA numpy array, shape (H, W, 4), dtype uint8.
        color_space: Target color space (currently only "srgb").

    Returns:
        Processed BGRA frame.
    """
    if color_space != "srgb":
        logger.warning(
            "unsupported_color_space",
            color_space=color_space,
            fallback="srgb",
        )

    # sRGB passthrough — no transformation needed
    return frame
