"""Design system rendering utilities — shadow application and helpers.

Provides shadow_apply and other rendering helpers used by components
that need design-system-consistent visual effects.

Shared helpers:
  - set_text_rendering(ctx): configure high-quality text anti-aliasing
  - draw_pill(ctx, x, y, w, h, color): draw a true pill shape (two semicircles)
  - draw_shadow(surface, blur_radius, offset_y, color): Gaussian-blurred shadow
  - draw_rounded_rect(cr, x, y, w, h, radius): rounded rectangle path
  - shadow_apply(frame, shadow): numpy-level shadow compositing
"""

from __future__ import annotations

import math

import cairo as _cairo
import numpy as np
from scipy.ndimage import gaussian_filter  # type: ignore[import-untyped]

from pymotion.design.tokens import ShadowConfig
from pymotion.utils.color import Color


def set_text_rendering(cr: object) -> None:
    """Configure high-quality text anti-aliasing on a Cairo context.

    Must be called on every Cairo context used for text rendering.
    Sets subpixel anti-aliasing with slight hinting for optimal legibility.

    Args:
        cr: Cairo context.
    """
    if not isinstance(cr, _cairo.Context):
        msg = "cr must be a cairo.Context"
        raise TypeError(msg)
    ctx: _cairo.Context[_cairo.ImageSurface] = cr
    ctx.set_antialias(_cairo.ANTIALIAS_BEST)
    font_options = _cairo.FontOptions()
    font_options.set_antialias(_cairo.ANTIALIAS_SUBPIXEL)
    font_options.set_hint_style(_cairo.HINT_STYLE_SLIGHT)
    font_options.set_hint_metrics(_cairo.HINT_METRICS_ON)
    ctx.set_font_options(font_options)


def draw_pill(
    cr: object,
    x: float,
    y: float,
    width: float,
    height: float,
    color: Color | None = None,
) -> None:
    """Draw a true pill shape — two semicircles connected by straight lines.

    Creates the path and optionally fills it with the given color.
    If color is None, only the path is created (caller must fill/stroke).

    Args:
        cr: Cairo context.
        x: Left edge x coordinate.
        y: Top edge y coordinate.
        width: Pill width.
        height: Pill height.
        color: Fill color, or None to only create path.
    """
    if not isinstance(cr, _cairo.Context):
        msg = "cr must be a cairo.Context"
        raise TypeError(msg)
    ctx: _cairo.Context[_cairo.ImageSurface] = cr
    r = height / 2.0
    if width < height:
        r = width / 2.0
    pi = math.pi
    ctx.new_sub_path()
    # Right semicircle
    ctx.arc(x + width - r, y + r, r, -pi / 2, pi / 2)
    # Bottom line to left semicircle
    ctx.line_to(x + r, y + height)
    # Left semicircle
    ctx.arc(x + r, y + r, r, pi / 2, 3 * pi / 2)
    # Top line back to start
    ctx.close_path()
    if color is not None:
        ctx.set_source_rgba(color.r, color.g, color.b, color.a)
        ctx.fill()


def draw_shadow_surface(
    cr: object,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    blur_radius: float,
    offset_y: float,
    color: Color,
) -> None:
    """Draw a blurred shadow beneath a rounded rectangle using Gaussian blur.

    Creates a separate surface, draws a silhouette, applies Gaussian blur,
    and composites it onto the main context at the given offset.

    Args:
        cr: Cairo context to draw onto.
        x: Left edge of the element casting the shadow.
        y: Top edge of the element.
        width: Element width.
        height: Element height.
        radius: Corner radius of the element.
        blur_radius: Gaussian blur radius in pixels.
        offset_y: Vertical offset of the shadow.
        color: Shadow color (with alpha).
    """
    if not isinstance(cr, _cairo.Context):
        msg = "cr must be a cairo.Context"
        raise TypeError(msg)
    ctx: _cairo.Context[_cairo.ImageSurface] = cr

    # Determine the bounding box for the shadow (element + blur margin + offset)
    margin = int(blur_radius * 2) + abs(int(offset_y)) + 4
    sw = int(width) + margin * 2
    sh = int(height) + margin * 2
    if sw <= 0 or sh <= 0:
        return

    shadow_surface = _cairo.ImageSurface(_cairo.FORMAT_ARGB32, sw, sh)
    shadow_ctx: _cairo.Context[_cairo.ImageSurface] = _cairo.Context(shadow_surface)

    # Draw the silhouette centered in the shadow surface
    sx = float(margin)
    sy = float(margin) + offset_y
    r = min(radius, width / 2, height / 2)
    pi = math.pi
    shadow_ctx.new_sub_path()
    shadow_ctx.arc(sx + width - r, sy + r, r, -pi / 2, 0)
    shadow_ctx.arc(sx + width - r, sy + height - r, r, 0, pi / 2)
    shadow_ctx.arc(sx + r, sy + height - r, r, pi / 2, pi)
    shadow_ctx.arc(sx + r, sy + r, r, pi, 3 * pi / 2)
    shadow_ctx.close_path()
    shadow_ctx.set_source_rgba(color.r, color.g, color.b, color.a)
    shadow_ctx.fill()

    # Apply Gaussian blur to the shadow surface
    buf = shadow_surface.get_data()
    arr = np.ndarray(shape=(sh, sw, 4), dtype=np.uint8, buffer=buf)
    sigma = blur_radius / 3.0
    if sigma > 0.5:
        for c in range(4):
            arr[:, :, c] = gaussian_filter(arr[:, :, c].astype(np.float32), sigma=sigma).astype(
                np.uint8
            )
    shadow_surface.mark_dirty()

    # Composite the blurred shadow onto the main context
    ctx.set_source_surface(shadow_surface, x - margin, y - margin)
    ctx.paint()


def draw_rounded_rect_top(
    cr: object,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
) -> None:
    """Draw a rectangle with only the top two corners rounded.

    Args:
        cr: Cairo context.
        x: Left edge.
        y: Top edge.
        width: Width.
        height: Height.
        radius: Top corner radius.
    """
    if not isinstance(cr, _cairo.Context):
        msg = "cr must be a cairo.Context"
        raise TypeError(msg)
    ctx: _cairo.Context[_cairo.ImageSurface] = cr
    r = min(radius, width / 2, height / 2)
    pi = math.pi
    ctx.new_sub_path()
    ctx.arc(x + width - r, y + r, r, -pi / 2, 0)
    ctx.line_to(x + width, y + height)
    ctx.line_to(x, y + height)
    ctx.arc(x + r, y + r, r, pi, 3 * pi / 2)
    ctx.close_path()


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
