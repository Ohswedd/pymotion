"""Design system rendering utilities — shadow application and helpers.

Provides shadow_apply and other rendering helpers used by components
that need design-system-consistent visual effects.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter  # type: ignore[import-untyped]

from pymotion.design.tokens import ShadowConfig


def shadow_apply(
    frame: np.ndarray,
    shadow: ShadowConfig,
) -> np.ndarray:
    """Apply a Gaussian shadow beneath content in a BGRA frame.

    Creates a blurred, offset copy of the frame's alpha channel as a
    shadow and composites it beneath the original content.

    Args:
        frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
        shadow: Shadow configuration specifying blur, offset, and color.

    Returns:
        New BGRA frame with shadow composited beneath original content.
    """
    h, w = frame.shape[:2]
    result = np.zeros_like(frame)

    # Extract alpha channel and create shadow mask
    alpha = frame[:, :, 3].astype(np.float32) / 255.0

    # Apply Gaussian blur to create soft shadow
    sigma = shadow.blur_radius / 3.0  # sigma ~= radius/3 for Gaussian
    if sigma > 0:
        shadow_mask = gaussian_filter(alpha, sigma=sigma)
    else:
        shadow_mask = alpha.copy()

    # Apply offset
    ox = int(round(shadow.offset_x))
    oy = int(round(shadow.offset_y))
    if ox != 0 or oy != 0:
        shifted = np.zeros_like(shadow_mask)
        src_y0 = max(0, -oy)
        src_y1 = min(h, h - oy)
        src_x0 = max(0, -ox)
        src_x1 = min(w, w - ox)
        dst_y0 = max(0, oy)
        dst_y1 = min(h, h + oy)
        dst_x0 = max(0, ox)
        dst_x1 = min(w, w + ox)
        actual_h = min(src_y1 - src_y0, dst_y1 - dst_y0)
        actual_w = min(src_x1 - src_x0, dst_x1 - dst_x0)
        if actual_h > 0 and actual_w > 0:
            shifted[dst_y0 : dst_y0 + actual_h, dst_x0 : dst_x0 + actual_w] = shadow_mask[
                src_y0 : src_y0 + actual_h, src_x0 : src_x0 + actual_w
            ]
        shadow_mask = shifted

    # Scale shadow alpha by shadow color's alpha
    shadow_alpha = shadow_mask * shadow.color_a

    # Draw shadow layer
    result[:, :, 0] = np.clip(shadow.color_b * 255 * shadow_alpha, 0, 255).astype(np.uint8)
    result[:, :, 1] = np.clip(shadow.color_g * 255 * shadow_alpha, 0, 255).astype(np.uint8)
    result[:, :, 2] = np.clip(shadow.color_r * 255 * shadow_alpha, 0, 255).astype(np.uint8)
    result[:, :, 3] = np.clip(shadow_alpha * 255, 0, 255).astype(np.uint8)

    # Composite original frame over shadow using alpha blending
    src_alpha = frame[:, :, 3].astype(np.float32) / 255.0
    dst_alpha = result[:, :, 3].astype(np.float32) / 255.0

    out_alpha = src_alpha + dst_alpha * (1.0 - src_alpha)
    safe_alpha = np.where(out_alpha > 0, out_alpha, 1.0)

    for c in range(3):
        result[:, :, c] = np.clip(
            (
                frame[:, :, c].astype(np.float32) * src_alpha
                + result[:, :, c].astype(np.float32) * dst_alpha * (1.0 - src_alpha)
            )
            / safe_alpha,
            0,
            255,
        ).astype(np.uint8)
    result[:, :, 3] = np.clip(out_alpha * 255, 0, 255).astype(np.uint8)

    return result


def draw_rounded_rect(
    cr: object,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
) -> None:
    """Draw a rounded rectangle path on a Cairo context.

    Args:
        cr: Cairo context (typed as object for mypy compatibility).
        x: Left edge x coordinate.
        y: Top edge y coordinate.
        width: Rectangle width.
        height: Rectangle height.
        radius: Corner radius in pixels.
    """
    import math

    import cairo as _cairo

    if not isinstance(cr, _cairo.Context):
        msg = "cr must be a cairo.Context"
        raise TypeError(msg)
    ctx: _cairo.Context[_cairo.ImageSurface] = cr

    r = min(radius, width / 2, height / 2)
    pi = math.pi
    ctx.new_sub_path()
    ctx.arc(x + width - r, y + r, r, -pi / 2, 0)
    ctx.arc(x + width - r, y + height - r, r, 0, pi / 2)
    ctx.arc(x + r, y + height - r, r, pi / 2, pi)
    ctx.arc(x + r, y + r, r, pi, 3 * pi / 2)
    ctx.close_path()
