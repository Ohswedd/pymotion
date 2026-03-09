"""Color effects — brightness, contrast, saturation, HSL, curves, LUT, split toning.

All effects operate on BGRA numpy arrays and are stateless.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.color import Color, ColorInput


@dataclass
class Brightness(Effect):
    """Brightness adjustment — multiplicative.

    Args:
        value: Brightness multiplier (1.0 = no change, >1 brighter, <1 darker).
    """

    value: float = 1.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply brightness adjustment to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Brightness-adjusted BGRA frame.
        """
        result = frame.astype(np.float32)
        result[:, :, :3] *= self.value
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class Contrast(Effect):
    """Contrast adjustment.

    Args:
        value: Contrast multiplier (1.0 = no change, >1 more contrast).
    """

    value: float = 1.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply contrast adjustment to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Contrast-adjusted BGRA frame.
        """
        result = frame.astype(np.float32)
        result[:, :, :3] = (result[:, :, :3] - 128) * self.value + 128
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class Saturation(Effect):
    """Saturation adjustment.

    Args:
        value: Saturation multiplier (1.0 = no change, 0 = grayscale).
    """

    value: float = 1.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply saturation adjustment to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Saturation-adjusted BGRA frame.
        """
        result = frame.astype(np.float32)
        # Luminance weights for BGRA (B=0.114, G=0.587, R=0.299)
        lum = 0.114 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.299 * result[:, :, 2]
        lum_3d = lum[:, :, np.newaxis]
        result[:, :, :3] = lum_3d + (result[:, :, :3] - lum_3d) * self.value
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class HueSaturationLuminance(Effect):
    """HSL adjustment — shift hue, saturation, and luminance.

    Args:
        hue: Hue shift in degrees (-180 to 180).
        saturation: Saturation multiplier (1.0 = no change).
        luminance: Luminance offset (-1.0 to 1.0).
    """

    hue: float = 0.0
    saturation: float = 1.0
    luminance: float = 0.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply HSL adjustment to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            HSL-adjusted BGRA frame.
        """
        result = frame.astype(np.float32) / 255.0
        r = result[:, :, 2]
        g = result[:, :, 1]
        b = result[:, :, 0]
        alpha = result[:, :, 3]

        # RGB to HSL
        cmax = np.maximum(np.maximum(r, g), b)
        cmin = np.minimum(np.minimum(r, g), b)
        delta = cmax - cmin
        light = (cmax + cmin) / 2.0

        # Hue calculation
        h_val = np.zeros_like(delta)
        mask_r = (delta > 0) & (cmax == r)
        mask_g = (delta > 0) & (cmax == g)
        mask_b = (delta > 0) & (cmax == b)
        safe_delta = np.where(delta > 0, delta, 1.0)
        h_val[mask_r] = (60.0 * ((g[mask_r] - b[mask_r]) / safe_delta[mask_r]) + 360) % 360
        h_val[mask_g] = (60.0 * ((b[mask_g] - r[mask_g]) / safe_delta[mask_g]) + 120) % 360
        h_val[mask_b] = (60.0 * ((r[mask_b] - g[mask_b]) / safe_delta[mask_b]) + 240) % 360

        sat = np.where(delta > 0, delta / np.clip(1.0 - np.abs(2.0 * light - 1.0), 1e-6, None), 0)

        # Apply adjustments
        h_val = (h_val + self.hue) % 360
        sat = np.clip(sat * self.saturation, 0, 1)
        light = np.clip(light + self.luminance, 0, 1)

        # HSL to RGB
        c = (1.0 - np.abs(2.0 * light - 1.0)) * sat
        x = c * (1.0 - np.abs((h_val / 60.0) % 2 - 1.0))
        m = light - c / 2.0

        r_out = np.zeros_like(h_val)
        g_out = np.zeros_like(h_val)
        b_out = np.zeros_like(h_val)

        for lo, hi, rv, gv, bv in [
            (0, 60, c, x, 0),
            (60, 120, x, c, 0),
            (120, 180, 0, c, x),
            (180, 240, 0, x, c),
            (240, 300, x, 0, c),
            (300, 360, c, 0, x),
        ]:
            mask = (h_val >= lo) & (h_val < hi)
            r_out[mask] = (rv[mask] if isinstance(rv, np.ndarray) else rv) + m[mask]
            g_out[mask] = (gv[mask] if isinstance(gv, np.ndarray) else gv) + m[mask]
            b_out[mask] = (bv[mask] if isinstance(bv, np.ndarray) else bv) + m[mask]

        out = np.empty_like(result)
        out[:, :, 0] = b_out * 255
        out[:, :, 1] = g_out * 255
        out[:, :, 2] = r_out * 255
        out[:, :, 3] = alpha * 255
        return np.clip(out, 0, 255).astype(np.uint8)


@dataclass
class ColorBalance(Effect):
    """Color balance — adjust shadows, midtones, and highlights separately.

    Args:
        shadows: Color offset for shadows.
        midtones: Color offset for midtones.
        highlights: Color offset for highlights.
    """

    shadows: Color = Color(0.0, 0.0, 0.0, 1.0)
    midtones: Color = Color(0.0, 0.0, 0.0, 1.0)
    highlights: Color = Color(0.0, 0.0, 0.0, 1.0)

    def __init__(
        self,
        shadows: ColorInput = "#000000",
        midtones: ColorInput = "#000000",
        highlights: ColorInput = "#000000",
    ) -> None:
        """Initialize ColorBalance.

        Args:
            shadows: Color offset for dark regions.
            midtones: Color offset for mid-brightness regions.
            highlights: Color offset for bright regions.
        """
        self.shadows = Color.parse(shadows)
        self.midtones = Color.parse(midtones)
        self.highlights = Color.parse(highlights)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply color balance to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Color-balanced BGRA frame.
        """
        result = frame.astype(np.float32)
        lum = (0.114 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.299 * result[:, :, 2]) / 255.0

        # Weight masks for shadows/midtones/highlights
        shadow_w = np.clip(1.0 - lum * 3.0, 0, 1)[:, :, np.newaxis]
        highlight_w = np.clip(lum * 3.0 - 2.0, 0, 1)[:, :, np.newaxis]
        midtone_w = 1.0 - shadow_w - highlight_w

        # BGR offsets from Color (r,g,b scaled to -128..128 from 0..1)
        s_bgr = np.array([self.shadows.b, self.shadows.g, self.shadows.r]) * 255 - 128
        m_bgr = np.array([self.midtones.b, self.midtones.g, self.midtones.r]) * 255 - 128
        h_bgr = np.array([self.highlights.b, self.highlights.g, self.highlights.r]) * 255 - 128

        result[:, :, :3] += shadow_w * s_bgr + midtone_w * m_bgr + highlight_w * h_bgr
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class Curves(Effect):
    """Curves adjustment — apply tone curves to RGB channels.

    Each curve is a list of (input, output) control points in 0-255 range.
    Linear interpolation is used between points.

    Args:
        rgb_curve: Master curve control points.
        r_curve: Red channel curve.
        g_curve: Green channel curve.
        b_curve: Blue channel curve.
    """

    rgb_curve: list[tuple[float, float]] = field(default_factory=lambda: [(0, 0), (255, 255)])
    r_curve: list[tuple[float, float]] = field(default_factory=lambda: [(0, 0), (255, 255)])
    g_curve: list[tuple[float, float]] = field(default_factory=lambda: [(0, 0), (255, 255)])
    b_curve: list[tuple[float, float]] = field(default_factory=lambda: [(0, 0), (255, 255)])

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply curves adjustment to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Curves-adjusted BGRA frame.
        """
        result = frame.copy()
        x_vals = np.arange(256, dtype=np.float32)

        # Build LUTs
        master_lut = self._build_lut(self.rgb_curve, x_vals)
        r_lut = self._build_lut(self.r_curve, x_vals)
        g_lut = self._build_lut(self.g_curve, x_vals)
        b_lut = self._build_lut(self.b_curve, x_vals)

        # Apply master then per-channel
        for c, lut in enumerate([b_lut, g_lut, r_lut]):
            channel = result[:, :, c]
            channel = master_lut[channel]
            result[:, :, c] = lut[channel]

        return result

    @staticmethod
    def _build_lut(points: list[tuple[float, float]], x_vals: np.ndarray) -> np.ndarray:
        """Build a 256-entry LUT from control points.

        Args:
            points: List of (input, output) control points.
            x_vals: Array of 0-255 input values.

        Returns:
            Uint8 lookup table array of shape (256,).
        """
        pts = sorted(points, key=lambda p: p[0])
        xs = np.array([p[0] for p in pts], dtype=np.float32)
        ys = np.array([p[1] for p in pts], dtype=np.float32)
        interp = np.interp(x_vals, xs, ys)
        out: np.ndarray = np.clip(interp, 0, 255).astype(np.uint8)
        return out


@dataclass
class LUTEffect(Effect):
    """LUT color grading — applies a .cube LUT file.

    Args:
        lut_path: Path to .cube LUT file.
        intensity: Blend intensity (0.0 = none, 1.0 = full).
    """

    lut_path: Path = Path(".")
    intensity: float = 1.0

    def __init__(self, lut_path: Path | str, intensity: float = 1.0) -> None:
        """Initialize LUT effect.

        Args:
            lut_path: Path to .cube LUT file.
            intensity: Blend intensity.
        """
        self.lut_path = Path(lut_path).resolve()
        self.intensity = intensity
        self._lut_data: np.ndarray | None = None
        self._lut_size: int = 0

    def _load_lut(self) -> None:
        """Load .cube LUT file into memory."""
        if self._lut_data is not None:
            return

        values: list[list[float]] = []
        size = 0
        with open(self.lut_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("LUT_3D_SIZE"):
                    size = int(line.split()[-1])
                elif line and not line.startswith("#") and not line.startswith("TITLE"):
                    parts = line.split()
                    if len(parts) == 3:
                        try:
                            values.append([float(x) for x in parts])
                        except ValueError:
                            continue

        self._lut_size = size
        # R varies fastest → indexed as [b, g, r]
        self._lut_data = np.array(values, dtype=np.float32).reshape(size, size, size, 3)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply LUT to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Color-graded BGRA frame.
        """
        self._load_lut()
        if self._lut_data is None or self._lut_size == 0:
            return frame.copy()

        result = frame.astype(np.float32)
        size = self._lut_size

        # Normalize to LUT range
        r = result[:, :, 2] / 255.0 * (size - 1)
        g = result[:, :, 1] / 255.0 * (size - 1)
        b = result[:, :, 0] / 255.0 * (size - 1)

        # Floor indices for trilinear interpolation
        r0 = np.clip(np.floor(r).astype(np.intp), 0, size - 2)
        g0 = np.clip(np.floor(g).astype(np.intp), 0, size - 2)
        b0 = np.clip(np.floor(b).astype(np.intp), 0, size - 2)
        rf = r - r0
        gf = g - g0
        bf = b - b0

        # Trilinear interpolation
        lut = self._lut_data
        c000 = lut[b0, g0, r0]
        c001 = lut[b0, g0, r0 + 1]
        c010 = lut[b0, g0 + 1, r0]
        c011 = lut[b0, g0 + 1, r0 + 1]
        c100 = lut[b0 + 1, g0, r0]
        c101 = lut[b0 + 1, g0, r0 + 1]
        c110 = lut[b0 + 1, g0 + 1, r0]
        c111 = lut[b0 + 1, g0 + 1, r0 + 1]

        rf3 = rf[:, :, np.newaxis]
        gf3 = gf[:, :, np.newaxis]
        bf3 = bf[:, :, np.newaxis]

        c00 = c000 * (1 - rf3) + c001 * rf3
        c01 = c010 * (1 - rf3) + c011 * rf3
        c10 = c100 * (1 - rf3) + c101 * rf3
        c11 = c110 * (1 - rf3) + c111 * rf3
        c0 = c00 * (1 - gf3) + c01 * gf3
        c1 = c10 * (1 - gf3) + c11 * gf3
        graded = c0 * (1 - bf3) + c1 * bf3  # (H, W, 3) in RGB

        # Convert back to BGR and blend
        original_bgr = result[:, :, :3]
        graded_bgr = np.empty_like(original_bgr)
        graded_bgr[:, :, 0] = graded[:, :, 2] * 255  # B
        graded_bgr[:, :, 1] = graded[:, :, 1] * 255  # G
        graded_bgr[:, :, 2] = graded[:, :, 0] * 255  # R

        result[:, :, :3] = original_bgr * (1 - self.intensity) + graded_bgr * self.intensity
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class SplitToning(Effect):
    """Split toning — tint highlights and shadows with different colors.

    Args:
        highlights_color: Color for bright areas.
        shadows_color: Color for dark areas.
        balance: Balance between shadows and highlights (-1.0 to 1.0).
    """

    highlights_color: Color = Color(1.0, 0.9, 0.8, 1.0)
    shadows_color: Color = Color(0.2, 0.3, 0.5, 1.0)
    balance: float = 0.0

    def __init__(
        self,
        highlights_color: ColorInput = "#FFE6CC",
        shadows_color: ColorInput = "#334D80",
        balance: float = 0.0,
    ) -> None:
        """Initialize SplitToning.

        Args:
            highlights_color: Color for highlights.
            shadows_color: Color for shadows.
            balance: Shift balance toward shadows (<0) or highlights (>0).
        """
        self.highlights_color = Color.parse(highlights_color)
        self.shadows_color = Color.parse(shadows_color)
        self.balance = balance

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply split toning to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Split-toned BGRA frame.
        """
        result = frame.astype(np.float32)
        lum = (0.114 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.299 * result[:, :, 2]) / 255.0

        # Shift midpoint based on balance
        midpoint = 0.5 + self.balance * 0.5
        shadow_w = np.clip(1.0 - lum / max(midpoint, 0.01), 0, 1)[:, :, np.newaxis]
        highlight_w = np.clip((lum - midpoint) / max(1.0 - midpoint, 0.01), 0, 1)[:, :, np.newaxis]

        s_bgr = np.array([self.shadows_color.b, self.shadows_color.g, self.shadows_color.r])
        h_bgr = np.array(
            [self.highlights_color.b, self.highlights_color.g, self.highlights_color.r]
        )

        # Blend toning: overlay color onto luminance
        result[:, :, :3] += shadow_w * (s_bgr * 255 - 128) * 0.3
        result[:, :, :3] += highlight_w * (h_bgr * 255 - 128) * 0.3
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class BleachBypass(Effect):
    """Bleach bypass effect — desaturated, high-contrast look.

    Args:
        strength: Effect strength (0.0-1.0).
    """

    strength: float = 0.5

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply bleach bypass to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Bleach-bypass-processed BGRA frame.
        """
        result = frame.astype(np.float32)
        lum = 0.114 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.299 * result[:, :, 2]
        lum_3d = lum[:, :, np.newaxis]

        # Overlay blend mode between original and luminance
        low = 2 * result[:, :, :3] * lum_3d / 255.0
        high = 255 - 2 * (255 - result[:, :, :3]) * (255 - lum_3d) / 255.0
        overlay = np.where(result[:, :, :3] < 128, low, high)

        result[:, :, :3] = result[:, :, :3] * (1 - self.strength) + overlay * self.strength
        return np.clip(result, 0, 255).astype(np.uint8)
