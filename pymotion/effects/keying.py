"""Keying effects — chroma key, luma key, color key, and difference key.

All keying effects modify the alpha channel of the input frame to
remove or isolate regions based on color, luminance, or difference
from a reference frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


def _feather_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Apply Gaussian blur to soften mask edges.

    Args:
        mask: Single-channel float32 mask (0.0-1.0).
        radius: Blur radius in pixels. If 0 or negative, returns unchanged.

    Returns:
        Feathered mask with softened edges.
    """
    if radius <= 0:
        return mask
    # Box blur approximation (3 passes ≈ Gaussian)
    kernel_size = radius * 2 + 1
    from numpy.lib.stride_tricks import sliding_window_view

    padded = np.pad(mask, radius, mode="edge")
    # Horizontal pass
    h_windows = sliding_window_view(padded, kernel_size, axis=1)
    h_blur = h_windows.mean(axis=-1)
    # Vertical pass on result
    padded_v = np.pad(h_blur, ((radius, radius), (0, 0)), mode="edge")
    v_windows = sliding_window_view(padded_v, kernel_size, axis=0)
    result = v_windows.mean(axis=-1)
    feathered: np.ndarray = result[: mask.shape[0], : mask.shape[1]]
    return feathered


def _choke_mask(mask: np.ndarray, amount: float) -> np.ndarray:
    """Expand or contract a mask by shifting threshold.

    Args:
        mask: Single-channel float32 mask (0.0-1.0).
        amount: Positive values expand the mask, negative values contract.
            Range: -1.0 to 1.0.

    Returns:
        Adjusted mask.
    """
    if abs(amount) < 1e-6:
        return mask
    return np.clip(mask + amount, 0.0, 1.0)


def _despill(frame: np.ndarray, spill_color: np.ndarray, strength: float) -> np.ndarray:
    """Remove color spill from foreground edges.

    Reduces the spill color component where it exceeds the average of
    the other two channels.

    Args:
        frame: BGRA uint8 frame.
        spill_color: BGR uint8 color to despill (shape: (3,)).
        strength: Despill strength (0.0-1.0).

    Returns:
        Frame with spill suppressed.
    """
    if strength <= 0:
        return frame

    result = frame.copy()
    bgr = result[:, :, :3].astype(np.float32)

    # Find which channel is dominant in the spill color
    spill_channel = int(np.argmax(spill_color[:3]))
    other_channels = [i for i in range(3) if i != spill_channel]

    # Reduce spill: clamp the spill channel to max of other channels
    avg_other = (bgr[:, :, other_channels[0]] + bgr[:, :, other_channels[1]]) / 2.0
    excess = bgr[:, :, spill_channel] - avg_other
    excess = np.maximum(excess, 0.0)
    bgr[:, :, spill_channel] -= excess * strength
    bgr = np.clip(bgr, 0.0, 255.0)

    result[:, :, :3] = bgr.astype(np.uint8)
    return result


@dataclass
class ChromaKey(Effect):
    """Remove a background color using YCbCr chroma distance.

    Designed for green/blue screen removal. Converts to YCbCr color
    space for robust chroma keying independent of luminance.

    Args:
        color: Key color (hex string, CSS name, or Color).
        tolerance: Color distance threshold (0.0-1.0). Higher = more removal.
        edge_softness: Mask feather radius as a fraction of frame height.
        spill_suppression: Strength of spill removal (0.0-1.0).
    """

    color: ColorInput = "#00FF00"
    tolerance: float = 0.3
    edge_softness: float = 0.0
    spill_suppression: float = 0.5

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply chroma key to remove the specified color.

        Args:
            frame: BGRA uint8 frame.
            ctx: Render context.

        Returns:
            BGRA frame with keyed areas made transparent.
        """
        parsed_color = Color.parse(self.color)
        b_key, g_key, r_key, _ = parsed_color.to_bgra_uint8()

        # Convert frame BGR to YCbCr (only need chroma channels for key)
        bgr = frame[:, :, :3].astype(np.float32)
        cb_frame = 128.0 + (-0.169 * bgr[:, :, 2] - 0.331 * bgr[:, :, 1] + 0.5 * bgr[:, :, 0])
        cr_frame = 128.0 + (0.5 * bgr[:, :, 2] - 0.419 * bgr[:, :, 1] - 0.081 * bgr[:, :, 0])

        # Convert key color to YCbCr
        r_f, g_f, b_f = float(r_key), float(g_key), float(b_key)
        cb_key = 128.0 + (-0.169 * r_f - 0.331 * g_f + 0.5 * b_f)
        cr_key = 128.0 + (0.5 * r_f - 0.419 * g_f - 0.081 * b_f)

        # Chroma distance (ignoring luminance)
        dist = np.sqrt((cb_frame - cb_key) ** 2 + (cr_frame - cr_key) ** 2) / 255.0

        # Create mask: 0 = key (transparent), 1 = keep (opaque)
        tol = max(self.tolerance, 0.001)
        mask = np.clip((dist - tol * 0.5) / (tol * 0.5), 0.0, 1.0).astype(np.float32)

        # Feather
        if self.edge_softness > 0:
            radius = max(1, int(frame.shape[0] * self.edge_softness))
            mask = _feather_mask(mask, radius)

        # Apply mask to alpha
        result = frame.copy()
        original_alpha = result[:, :, 3].astype(np.float32) / 255.0
        result[:, :, 3] = (original_alpha * mask * 255.0).astype(np.uint8)

        # Despill
        if self.spill_suppression > 0:
            spill_bgr = np.array([b_key, g_key, r_key], dtype=np.uint8)
            result = _despill(result, spill_bgr, self.spill_suppression)

        return result


@dataclass
class LumaKey(Effect):
    """Key on luminance threshold.

    Removes dark or bright regions based on luma values.

    Args:
        threshold: Luminance threshold (0.0-1.0). Pixels below this are keyed.
        softness: Transition softness around the threshold (0.0-1.0).
        invert: If True, key bright pixels instead of dark ones.
    """

    threshold: float = 0.5
    softness: float = 0.1
    invert: bool = False

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply luma key based on luminance threshold.

        Args:
            frame: BGRA uint8 frame.
            ctx: Render context.

        Returns:
            BGRA frame with keyed areas made transparent.
        """
        bgr = frame[:, :, :3].astype(np.float32) / 255.0
        luma = 0.299 * bgr[:, :, 2] + 0.587 * bgr[:, :, 1] + 0.114 * bgr[:, :, 0]

        soft = max(self.softness, 0.001)
        if self.invert:
            mask = np.clip((self.threshold - luma) / soft + 0.5, 0.0, 1.0).astype(np.float32)
        else:
            mask = np.clip((luma - self.threshold) / soft + 0.5, 0.0, 1.0).astype(np.float32)

        result = frame.copy()
        original_alpha = result[:, :, 3].astype(np.float32) / 255.0
        result[:, :, 3] = (original_alpha * mask * 255.0).astype(np.uint8)
        return result


@dataclass
class ColorKey(Effect):
    """Key any arbitrary color using Lab color distance.

    More perceptually accurate than RGB distance for matching
    arbitrary colors.

    Args:
        color: Target color to key out.
        tolerance: Color distance threshold (0.0-1.0).
        softness: Edge softness (0.0-1.0).
    """

    color: ColorInput = "#000000"
    tolerance: float = 0.3
    softness: float = 0.1

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply color key using Lab color distance.

        Args:
            frame: BGRA uint8 frame.
            ctx: Render context.

        Returns:
            BGRA frame with keyed areas made transparent.
        """
        parsed_color = Color.parse(self.color)
        b_key, g_key, r_key, _ = parsed_color.to_bgra_uint8()

        # Simplified Lab distance: use linearized RGB Euclidean distance
        # weighted for perceptual uniformity
        bgr = frame[:, :, :3].astype(np.float32)
        key_bgr = np.array([float(b_key), float(g_key), float(r_key)], dtype=np.float32)

        # Weighted Euclidean distance (human eye is more sensitive to green)
        weights = np.array([0.114, 0.587, 0.299], dtype=np.float32)  # B, G, R
        diff = bgr - key_bgr
        dist = np.sqrt(np.sum(diff**2 * weights, axis=2)) / 255.0

        tol = max(self.tolerance, 0.001)
        soft = max(self.softness, 0.001)
        mask = np.clip((dist - tol) / soft + 0.5, 0.0, 1.0).astype(np.float32)

        result = frame.copy()
        original_alpha = result[:, :, 3].astype(np.float32) / 255.0
        result[:, :, 3] = (original_alpha * mask * 255.0).astype(np.uint8)
        return result


@dataclass
class DifferenceKey(Effect):
    """Key based on pixel difference from a reference frame.

    Compares each frame to a stored reference and keys pixels that
    are similar (within tolerance) to the reference.

    Args:
        reference: Reference BGRA frame to compare against.
        tolerance: Difference threshold (0.0-1.0).
        softness: Edge softness (0.0-1.0).
    """

    reference: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 4), dtype=np.uint8))
    tolerance: float = 0.2
    softness: float = 0.1

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply difference key against the reference frame.

        Args:
            frame: BGRA uint8 frame.
            ctx: Render context.

        Returns:
            BGRA frame with similar-to-reference areas made transparent.
        """
        ref = self.reference
        h, w = frame.shape[:2]

        # Resize reference if dimensions don't match
        if ref.shape[0] != h or ref.shape[1] != w:
            # Simple nearest-neighbor resize
            ref_h, ref_w = ref.shape[:2]
            if ref_h > 0 and ref_w > 0:
                y_idx = (np.arange(h) * ref_h // h).clip(0, ref_h - 1)
                x_idx = (np.arange(w) * ref_w // w).clip(0, ref_w - 1)
                ref = ref[np.ix_(y_idx, x_idx)]
            else:
                return frame

        # Compute per-pixel difference
        diff = np.abs(frame[:, :, :3].astype(np.float32) - ref[:, :, :3].astype(np.float32))
        dist = np.mean(diff, axis=2) / 255.0

        tol = max(self.tolerance, 0.001)
        soft = max(self.softness, 0.001)
        # Pixels close to reference → transparent (mask=0)
        mask = np.clip((dist - tol) / soft + 0.5, 0.0, 1.0).astype(np.float32)

        result = frame.copy()
        original_alpha = result[:, :, 3].astype(np.float32) / 255.0
        result[:, :, 3] = (original_alpha * mask * 255.0).astype(np.uint8)
        return result
