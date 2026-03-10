"""Frame compositor — alpha compositing and blend modes.

Composites multiple clip layers into a single frame using NumPy-vectorized
operations. Supports all 8 blend modes: NORMAL, MULTIPLY, SCREEN, OVERLAY,
ADD, SOFT_LIGHT, HARD_LIGHT, DIFFERENCE.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pymotion.clip.base import BlendMode
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


def _find_alpha_bbox(
    alpha: np.ndarray,
) -> tuple[int, int, int, int] | None:
    """Find the bounding box of non-zero alpha pixels.

    Args:
        alpha: 2D alpha channel array (H, W), dtype uint8.

    Returns:
        (y0, y1, x0, x1) bounding box, or None if fully transparent.
    """
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    if not np.any(rows):
        return None
    y0 = int(np.argmax(rows))
    y1 = int(len(rows) - np.argmax(rows[::-1]))
    x0 = int(np.argmax(cols))
    x1 = int(len(cols) - np.argmax(cols[::-1]))
    return (y0, y1, x0, x1)


_alpha_cache: dict[int, tuple[int, int, tuple[int, int, int, int] | None]] = {}


def _get_alpha_info(
    frame: np.ndarray,
) -> tuple[int, int, tuple[int, int, int, int] | None]:
    """Get cached alpha channel info: (min_a, max_a, bbox).

    Uses the frame's data pointer + a hash of the alpha channel as
    cache key for correctness (pointer alone can alias after free).

    Args:
        frame: BGRA frame (H, W, 4), dtype uint8.

    Returns:
        (min_alpha, max_alpha, bounding_box_or_None).
    """
    # Use (pointer, nbytes, first alpha, last alpha) as cheap identity check.
    # This avoids hashing the full alpha channel while catching most aliasing.
    alpha = frame[:, :, 3]
    ptr = frame.ctypes.data
    a_first = int(alpha.flat[0]) if alpha.size > 0 else 0
    a_last = int(alpha.flat[-1]) if alpha.size > 0 else 0
    cache_key = (ptr, frame.nbytes, a_first, a_last)

    cached = _alpha_cache.get(cache_key)
    if cached is not None:
        return cached

    max_a = int(alpha.max())
    if max_a == 0:
        info = (0, 0, None)
    else:
        min_a = int(alpha.min())
        if min_a == max_a == 255:
            # Fully opaque — no bbox needed
            info = (255, 255, None)
        else:
            bbox = _find_alpha_bbox(alpha)
            info = (min_a, max_a, bbox)

    # Keep cache bounded
    if len(_alpha_cache) > 200:
        _alpha_cache.clear()
    _alpha_cache[cache_key] = info
    return info


def composite_layers(
    background: np.ndarray[Any, Any],
    layers: list[tuple[np.ndarray[Any, Any], BlendMode, float]],
) -> np.ndarray[Any, Any]:
    """Composite multiple layers onto a background.

    Each layer is a tuple of (frame, blend_mode, opacity).
    Layers are composited in order (first = bottom, last = top).

    Uses a fast path for the common case (NORMAL blend, full opacity).

    Args:
        background: BGRA background frame, shape (H, W, 4), dtype uint8.
        layers: List of (frame, blend_mode, opacity) tuples.

    Returns:
        Composited BGRA frame, shape (H, W, 4), dtype uint8.
    """
    # Clear alpha cache between frames to prevent stale entries from
    # numpy memory address reuse (arrays freed and reallocated at the
    # same pointer return incorrect cached alpha info).
    _alpha_cache.clear()

    if not layers:
        return background

    # Optimization: find the topmost fully-opaque layer that covers the full frame.
    # Everything below it is invisible and can be skipped.
    start_idx = 0
    for i in range(len(layers) - 1, -1, -1):
        lf, bm, op = layers[i]
        if bm == BlendMode.NORMAL and op >= 1.0:
            alpha_info = _get_alpha_info(lf)
            if alpha_info[0] == 255:  # min_a == 255
                start_idx = i
                break

    # Work on a uint8 result; only convert to float32 within regions that need blending
    if start_idx > 0:
        result = layers[start_idx][0].copy()
        layers = layers[start_idx + 1 :]
    else:
        result = background.copy()

    for layer_frame, blend_mode, opacity in layers:
        # Skip fully transparent layers
        if opacity <= 0.0:
            continue

        min_a, max_a, bbox = _get_alpha_info(layer_frame)
        if max_a == 0:
            continue

        # NORMAL blend fast paths
        if blend_mode == BlendMode.NORMAL:
            if opacity >= 1.0 and min_a == 255:
                # Completely opaque — direct copy (no alpha math)
                result[:] = layer_frame
                continue

            if min_a == 255 and opacity < 1.0:
                # Opaque layer with track opacity — fast uint16 lerp
                _lerp_opaque_layer(result, layer_frame, opacity)
                continue

            if bbox is None:
                if min_a == 255:
                    h, w = result.shape[:2]
                    y0, y1, x0, x1 = 0, h, 0, w
                else:
                    continue
            else:
                y0, y1, x0, x1 = bbox
            _blend_region_normal(result, layer_frame, y0, y1, x0, x1, opacity)
            continue

        # Non-NORMAL blend modes
        if bbox is None:
            if min_a == 255:
                # Fully opaque: use full frame
                h, w = result.shape[:2]
                y0, y1, x0, x1 = 0, h, 0, w
            else:
                continue
        else:
            y0, y1, x0, x1 = bbox

        # ADD blend fast path — integer arithmetic
        if blend_mode == BlendMode.ADD:
            _blend_region_add(result, layer_frame, opacity, y0, y1, x0, x1)
            continue

        _blend_region_generic(result, layer_frame, blend_mode, opacity, y0, y1, x0, x1)

    return result


def _lerp_opaque_layer(
    result: np.ndarray,
    layer_frame: np.ndarray,
    opacity: float,
) -> None:
    """Fast lerp for fully-opaque layer with opacity < 1.

    Uses uint16 arithmetic to avoid float32 allocation.

    Args:
        result: Mutable uint8 result buffer (H, W, 4).
        layer_frame: uint8 layer frame (H, W, 4) with alpha=255.
        opacity: Layer opacity (0-1).
    """
    # result = result * (1 - opacity) + layer * opacity
    # Using fixed-point: multiply by 256*opacity, shift right 8
    opa_i = int(opacity * 256)
    inv_i = 256 - opa_i
    r16 = result.astype(np.uint16)
    l16 = layer_frame.astype(np.uint16)
    blended = (r16 * inv_i + l16 * opa_i) >> 8
    result[:] = blended.astype(np.uint8)


def _blend_region_add(
    result: np.ndarray,
    layer_frame: np.ndarray,
    opacity: float,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
) -> None:
    """Fast additive blend using uint16 arithmetic.

    For very sparse layers (< 5% coverage), uses masked scatter to avoid
    processing millions of zero pixels.

    Args:
        result: Mutable uint8 result buffer (H, W, 4).
        layer_frame: uint8 layer frame (H, W, 4).
        opacity: Layer opacity (0-1).
        y0: Top row of bounding box.
        y1: Bottom row (exclusive).
        x0: Left column.
        x1: Right column (exclusive).
    """
    dst = result[y0:y1, x0:x1]
    src = layer_frame[y0:y1, x0:x1]
    src_alpha = src[:, :, 3]

    # For sparse layers, only process non-zero pixels
    total_pixels = (y1 - y0) * (x1 - x0)
    nonzero_count = np.count_nonzero(src_alpha)

    if nonzero_count == 0:
        return

    if nonzero_count < total_pixels * 0.05:
        # Sparse path: only touch pixels with alpha > 0
        rows, cols = np.nonzero(src_alpha)
        src_px = src[rows, cols].astype(np.uint16)

        if opacity < 1.0:
            opa_i = int(opacity * 256)
            src_px = (src_px * opa_i) >> 8

        dst_px = dst[rows, cols].astype(np.uint16)
        added = np.minimum(dst_px + src_px, 255).astype(np.uint8)
        dst[rows, cols] = added
        return

    # Dense path: process entire region
    if opacity < 1.0:
        opa_i = int(opacity * 256)
        src_scaled = (src.astype(np.uint16) * opa_i) >> 8
    else:
        src_scaled = src.astype(np.uint16)

    added = dst.astype(np.uint16) + src_scaled
    np.minimum(added, 255, out=added)
    dst[:] = added.astype(np.uint8)


def _blend_region_normal(
    result: np.ndarray,
    layer_frame: np.ndarray,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    opacity: float,
) -> None:
    """Alpha-blend a region using NORMAL mode into result.

    Uses uint16 fixed-point arithmetic for speed when the destination
    is fully opaque (common case: compositing over an opaque background).

    Args:
        result: Mutable uint8 result buffer (H, W, 4).
        layer_frame: uint8 layer frame (H, W, 4).
        y0: Top row of bounding box.
        y1: Bottom row (exclusive).
        x0: Left column.
        x1: Right column (exclusive).
        opacity: Layer opacity (0-1).
    """
    region = result[y0:y1, x0:x1]
    src_region = layer_frame[y0:y1, x0:x1]

    # Get effective source alpha (src_alpha * opacity)
    src_a = src_region[:, :, 3].astype(np.uint16)
    if opacity < 1.0:
        src_a = (src_a * int(opacity * 256)) >> 8

    dst_a = region[:, :, 3]

    # Fast path: if destination is fully opaque (most common case),
    # we can use simple alpha lerp: out = dst*(255-sa)/255 + src*sa/255
    if dst_a.min() == 255:
        inv_a = 255 - src_a  # (H, W) uint16
        sa = src_a

        for c in range(3):
            dc = region[:, :, c].astype(np.uint16)
            sc = src_region[:, :, c].astype(np.uint16)
            region[:, :, c] = ((dc * inv_a + sc * sa) >> 8).astype(np.uint8)
        # Alpha stays 255
        return

    # General path: full Porter-Duff over
    src = src_region.astype(np.float32)
    dst = region.astype(np.float32)

    src_alpha = src_a[:, :, np.newaxis].astype(np.float32) / 255.0
    dst_alpha = dst[:, :, 3:4] / 255.0

    out_alpha = src_alpha + dst_alpha * (1.0 - src_alpha)
    safe_alpha = np.where(out_alpha > 0, out_alpha, 1.0)

    out_rgb = (
        src[:, :, :3] * src_alpha + dst[:, :, :3] * dst_alpha * (1.0 - src_alpha)
    ) / safe_alpha

    region[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
    region[:, :, 3] = np.clip(out_alpha[:, :, 0] * 255, 0, 255).astype(np.uint8)


def _apply_blend(
    bg_rgb: np.ndarray,
    layer_rgb: np.ndarray,
    blend_mode: BlendMode,
) -> np.ndarray:
    """Apply blend mode to RGB arrays. Both must be float32.

    Args:
        bg_rgb: Background RGB (float32).
        layer_rgb: Layer RGB (float32).
        blend_mode: Blend mode.

    Returns:
        Blended RGB (float32).
    """
    if blend_mode == BlendMode.MULTIPLY:
        return (bg_rgb * layer_rgb) / 255.0
    if blend_mode == BlendMode.SCREEN:
        return 255.0 - ((255.0 - bg_rgb) * (255.0 - layer_rgb)) / 255.0
    if blend_mode == BlendMode.OVERLAY:
        low = 2.0 * bg_rgb * layer_rgb / 255.0
        high = 255.0 - 2.0 * (255.0 - bg_rgb) * (255.0 - layer_rgb) / 255.0
        return np.where(bg_rgb < 128, low, high)
    if blend_mode == BlendMode.ADD:
        return bg_rgb + layer_rgb
    if blend_mode == BlendMode.SOFT_LIGHT:
        return (
            255.0 - 2.0 * layer_rgb
        ) * bg_rgb * bg_rgb / 65025.0 + 2.0 * layer_rgb * bg_rgb / 255.0
    if blend_mode == BlendMode.HARD_LIGHT:
        low = 2.0 * bg_rgb * layer_rgb / 255.0
        high = 255.0 - 2.0 * (255.0 - bg_rgb) * (255.0 - layer_rgb) / 255.0
        return np.where(layer_rgb < 128, low, high)
    if blend_mode == BlendMode.DIFFERENCE:
        return np.abs(bg_rgb - layer_rgb)
    return layer_rgb


def _blend_region_generic(
    result: np.ndarray,
    layer_frame: np.ndarray,
    blend_mode: BlendMode,
    opacity: float,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
) -> None:
    """Blend a bounding-box region with any blend mode. Writes into result.

    Args:
        result: Mutable uint8 result buffer (H, W, 4).
        layer_frame: uint8 layer frame (H, W, 4).
        blend_mode: Blend mode to use.
        opacity: Layer opacity (0-1).
        y0: Top row of bounding box.
        y1: Bottom row (exclusive).
        x0: Left column.
        x1: Right column (exclusive).
    """
    layer = layer_frame[y0:y1, x0:x1].astype(np.float32)
    bg = result[y0:y1, x0:x1].astype(np.float32)

    if opacity < 1.0:
        layer[:, :, 3] *= opacity

    layer_alpha: np.ndarray[Any, Any] = layer[:, :, 3:4] / 255.0
    bg_alpha: np.ndarray[Any, Any] = bg[:, :, 3:4] / 255.0
    layer_rgb: np.ndarray[Any, Any] = layer[:, :, :3]
    bg_rgb: np.ndarray[Any, Any] = bg[:, :, :3]

    blended_rgb = _apply_blend(bg_rgb, layer_rgb, blend_mode)

    out_alpha = layer_alpha + bg_alpha * (1.0 - layer_alpha)
    safe_alpha = np.where(out_alpha > 0, out_alpha, 1.0)
    out_rgb = (blended_rgb * layer_alpha + bg_rgb * bg_alpha * (1.0 - layer_alpha)) / safe_alpha

    region = result[y0:y1, x0:x1]
    region[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
    region[:, :, 3] = np.clip(out_alpha[:, :, 0] * 255, 0, 255).astype(np.uint8)


def _blend_full_frame(
    result: np.ndarray,
    layer_frame: np.ndarray,
    blend_mode: BlendMode,
    opacity: float,
) -> None:
    """Full-frame blend with any blend mode. Writes into result in-place.

    Args:
        result: Mutable uint8 result buffer (H, W, 4).
        layer_frame: uint8 layer frame (H, W, 4).
        blend_mode: Blend mode to use.
        opacity: Layer opacity (0-1).
    """
    h, w = result.shape[:2]
    _blend_region_generic(result, layer_frame, blend_mode, opacity, 0, h, 0, w)
