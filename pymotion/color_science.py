"""Color science — ACES pipeline, HDR output, color matching, scopes.

Professional color pipeline with ACES 1.3 support, HDR10/HLG output
presets, secondary color grading, and video scope visualizations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


# ── ACES Color Space Matrices ─────────────────────────────────────────

# sRGB to ACES AP0 (CIE XYZ intermediate)
_SRGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)

_XYZ_TO_AP0 = np.array(
    [
        [1.0498110175, 0.0000000000, -0.0000974845],
        [-0.4959030231, 1.3733130458, 0.0982400361],
        [0.0000000000, 0.0000000000, 0.9912520182],
    ],
    dtype=np.float64,
)

_AP0_TO_XYZ = np.array(
    [
        [0.9525523959, 0.0000000000, 0.0000936786],
        [0.3439664498, 0.7281660966, -0.0721325464],
        [0.0000000000, 0.0000000000, 1.0088251844],
    ],
    dtype=np.float64,
)

_XYZ_TO_SRGB = np.array(
    [
        [3.2404542, -1.5371385, -0.4985314],
        [-0.9692660, 1.8760108, 0.0415560],
        [0.0555434, -0.2040259, 1.0572252],
    ],
    dtype=np.float64,
)


def _srgb_to_linear(srgb: np.ndarray) -> np.ndarray:
    """Convert sRGB gamma to linear light.

    Args:
        srgb: sRGB values in [0, 1].

    Returns:
        Linear values.
    """
    result: np.ndarray = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4,
    )
    return result


def _linear_to_srgb(linear: np.ndarray) -> np.ndarray:
    """Convert linear light to sRGB gamma.

    Args:
        linear: Linear values in [0, 1].

    Returns:
        sRGB gamma values.
    """
    linear = np.clip(linear, 0.0, 1.0)
    result: np.ndarray = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * (linear ** (1.0 / 2.4)) - 0.055,
    )
    return result


def srgb_to_aces(frame: np.ndarray) -> np.ndarray:
    """Convert an sRGB frame to ACES AP0 color space.

    Args:
        frame: BGRA uint8 frame (H, W, 4).

    Returns:
        Float64 ACES AP0 frame (H, W, 3) in scene-linear light.
    """
    h, w = frame.shape[:2]
    rgb = frame[:, :, :3][:, :, ::-1].astype(np.float64) / 255.0
    linear = _srgb_to_linear(rgb)
    flat = linear.reshape(-1, 3)
    xyz = flat @ _SRGB_TO_XYZ.T
    aces: np.ndarray = xyz @ _XYZ_TO_AP0.T
    return aces.reshape(h, w, 3)


def aces_to_srgb(aces: np.ndarray) -> np.ndarray:
    """Convert ACES AP0 frame to sRGB BGRA uint8.

    Applies a simplified ACES RRT+ODT (tone mapping) before
    converting to sRGB.

    Args:
        aces: Float64 ACES AP0 frame (H, W, 3).

    Returns:
        BGRA uint8 frame (H, W, 4).
    """
    h, w = aces.shape[:2]
    flat = aces.reshape(-1, 3)

    # Simple ACES filmic tone map
    # Hill ACES approximation: (x(ax+b)) / (x(cx+d)+e)
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    xyz = flat @ _AP0_TO_XYZ.T
    rgb_linear = xyz @ _XYZ_TO_SRGB.T
    rgb_linear = np.clip(rgb_linear, 0.0, None)
    mapped = (rgb_linear * (a * rgb_linear + b)) / (rgb_linear * (c * rgb_linear + d) + e)
    mapped = np.clip(mapped, 0.0, 1.0)

    srgb = _linear_to_srgb(mapped).reshape(h, w, 3)
    bgr = (srgb[:, :, ::-1] * 255).astype(np.uint8)

    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, :3] = bgr
    result[:, :, 3] = 255
    return result


# ── HDR Transfer Functions ────────────────────────────────────────────


def _pq_eotf_inv(linear: np.ndarray) -> np.ndarray:
    """Apply PQ (Perceptual Quantizer) EOTF inverse for HDR10.

    SMPTE ST 2084 PQ curve, normalized to [0, 1].

    Args:
        linear: Scene-linear values (0 to ~1.0, can exceed 1.0).

    Returns:
        PQ-encoded values in [0, 1].
    """
    m1 = 0.1593017578125
    m2 = 78.84375
    c1 = 0.8359375
    c2 = 18.8515625
    c3 = 18.6875

    # Normalize to 10000 nits reference
    y = np.clip(linear, 0.0, 1.0)
    ym1 = y**m1
    result: np.ndarray = ((c1 + c2 * ym1) / (1.0 + c3 * ym1)) ** m2
    return result


def _hlg_oetf(linear: np.ndarray) -> np.ndarray:
    """Apply HLG (Hybrid Log-Gamma) OETF.

    ARIB STD-B67 transfer function.

    Args:
        linear: Scene-linear values.

    Returns:
        HLG-encoded values in [0, 1].
    """
    a = 0.17883277
    b = 1.0 - 4.0 * a
    c = 0.5 - a * math.log(4.0 * a)

    linear = np.clip(linear, 0.0, 1.0)
    result: np.ndarray = np.where(
        linear <= 1.0 / 12.0,
        np.sqrt(3.0 * linear),
        a * np.log(12.0 * linear - b) + c,
    )
    return result


# ── HDR Output Presets ────────────────────────────────────────────────


HDR10_PRESET: dict[str, str | int] = {
    "transfer": "pq",
    "primaries": "bt2020",
    "bit_depth": "10",
    "color_space": "bt2020nc",
}

HLG_PRESET: dict[str, str | int] = {
    "transfer": "hlg",
    "primaries": "bt2020",
    "bit_depth": "10",
    "color_space": "bt2020nc",
}


# ── Color Effects ─────────────────────────────────────────────────────


@dataclass
class ColorMatch(Effect):
    """Match the color grade of a clip to a reference clip.

    Computes per-channel mean and standard deviation of the reference
    and adjusts the source to match, using the Reinhard color transfer
    method in Lab color space.

    Args:
        reference_frame: A reference BGRA uint8 frame (H, W, 4) to
                         match the grade to.
    """

    reference_frame: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 4), dtype=np.uint8))

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply color matching to a frame.

        Args:
            frame: BGRA uint8 frame (H, W, 4).
            ctx: Render context.

        Returns:
            Color-matched BGRA uint8 frame.
        """
        if self.reference_frame.size <= 4:
            return frame

        # Convert to float Lab-like space (simplified: use linear RGB means)
        src = frame[:, :, :3].astype(np.float64) / 255.0
        ref = self.reference_frame[:, :, :3].astype(np.float64) / 255.0

        for ch in range(3):
            src_mean = np.mean(src[:, :, ch])
            src_std = np.std(src[:, :, ch]) + 1e-6
            ref_mean = np.mean(ref[:, :, ch])
            ref_std = np.std(ref[:, :, ch]) + 1e-6

            src[:, :, ch] = (src[:, :, ch] - src_mean) * (ref_std / src_std) + ref_mean

        src = np.clip(src * 255, 0, 255).astype(np.uint8)
        result = frame.copy()
        result[:, :, :3] = src
        return result


@dataclass
class HSLSecondary(Effect):
    """Secondary color correction — isolate and grade a color range.

    Selects pixels within a specified HSL range and applies a grade
    (hue shift, saturation adjust, luminance adjust) only to those
    pixels.

    Args:
        hue_range: (min_hue, max_hue) in degrees [0, 360].
        saturation_range: (min_sat, max_sat) in [0, 1].
        luminance_range: (min_lum, max_lum) in [0, 1].
        hue_shift: Hue shift in degrees to apply.
        saturation_scale: Saturation multiplier.
        luminance_scale: Luminance multiplier.
    """

    hue_range: tuple[float, float] = (0.0, 360.0)
    saturation_range: tuple[float, float] = (0.0, 1.0)
    luminance_range: tuple[float, float] = (0.0, 1.0)
    hue_shift: float = 0.0
    saturation_scale: float = 1.0
    luminance_scale: float = 1.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply secondary color correction.

        Args:
            frame: BGRA uint8 frame (H, W, 4).
            ctx: Render context.

        Returns:
            Graded BGRA uint8 frame.
        """
        h, w = frame.shape[:2]
        rgb = frame[:, :, :3][:, :, ::-1].astype(np.float64) / 255.0

        # Convert to HSL
        hsl = self._rgb_to_hsl(rgb)
        hue = hsl[:, :, 0]
        sat = hsl[:, :, 1]
        lum = hsl[:, :, 2]

        # Build selection mask
        h_min, h_max = self.hue_range
        if h_min <= h_max:
            hue_mask = (hue >= h_min) & (hue <= h_max)
        else:
            hue_mask = (hue >= h_min) | (hue <= h_max)

        s_min, s_max = self.saturation_range
        sat_mask = (sat >= s_min) & (sat <= s_max)

        l_min, l_max = self.luminance_range
        lum_mask = (lum >= l_min) & (lum <= l_max)

        mask = hue_mask & sat_mask & lum_mask

        # Apply adjustments
        hsl[:, :, 0] = np.where(mask, (hue + self.hue_shift) % 360.0, hue)
        hsl[:, :, 1] = np.where(mask, np.clip(sat * self.saturation_scale, 0, 1), sat)
        hsl[:, :, 2] = np.where(mask, np.clip(lum * self.luminance_scale, 0, 1), lum)

        # Convert back to RGB
        rgb_out = self._hsl_to_rgb(hsl)
        bgr = (rgb_out[:, :, ::-1] * 255).astype(np.uint8)

        result = frame.copy()
        result[:, :, :3] = bgr
        return result

    @staticmethod
    def _rgb_to_hsl(rgb: np.ndarray) -> np.ndarray:
        """Convert RGB [0,1] to HSL (H in degrees, S and L in [0,1]).

        Args:
            rgb: RGB array (H, W, 3).

        Returns:
            HSL array (H, W, 3).
        """
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        cmax = np.maximum(np.maximum(r, g), b)
        cmin = np.minimum(np.minimum(r, g), b)
        delta = cmax - cmin

        # Lightness
        lum = (cmax + cmin) / 2.0

        # Saturation
        sat = np.where(delta == 0, 0.0, delta / (1.0 - np.abs(2.0 * lum - 1.0) + 1e-10))
        sat = np.clip(sat, 0.0, 1.0)

        # Hue
        hue = np.zeros_like(delta)
        mask_r = (delta > 0) & (cmax == r)
        mask_g = (delta > 0) & (cmax == g)
        mask_b = (delta > 0) & (cmax == b)

        hue[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)
        hue[mask_g] = 60.0 * ((b[mask_g] - r[mask_g]) / delta[mask_g] + 2)
        hue[mask_b] = 60.0 * ((r[mask_b] - g[mask_b]) / delta[mask_b] + 4)
        hue = hue % 360.0

        result = np.stack([hue, sat, lum], axis=-1)
        return result

    @staticmethod
    def _hsl_to_rgb(hsl: np.ndarray) -> np.ndarray:
        """Convert HSL to RGB [0,1].

        Args:
            hsl: HSL array (H, W, 3).

        Returns:
            RGB array (H, W, 3).
        """
        h, s, l_val = hsl[:, :, 0], hsl[:, :, 1], hsl[:, :, 2]

        c = (1.0 - np.abs(2.0 * l_val - 1.0)) * s
        x = c * (1.0 - np.abs((h / 60.0) % 2 - 1.0))
        m = l_val - c / 2.0

        r = np.zeros_like(h)
        g = np.zeros_like(h)
        b = np.zeros_like(h)

        mask0 = (h >= 0) & (h < 60)
        mask1 = (h >= 60) & (h < 120)
        mask2 = (h >= 120) & (h < 180)
        mask3 = (h >= 180) & (h < 240)
        mask4 = (h >= 240) & (h < 300)
        mask5 = (h >= 300) & (h < 360)

        r[mask0], g[mask0], b[mask0] = c[mask0], x[mask0], 0
        r[mask1], g[mask1], b[mask1] = x[mask1], c[mask1], 0
        r[mask2], g[mask2], b[mask2] = 0, c[mask2], x[mask2]
        r[mask3], g[mask3], b[mask3] = 0, x[mask3], c[mask3]
        r[mask4], g[mask4], b[mask4] = x[mask4], 0, c[mask4]
        r[mask5], g[mask5], b[mask5] = c[mask5], 0, x[mask5]

        result: np.ndarray = np.clip(np.stack([r + m, g + m, b + m], axis=-1), 0, 1)
        return result


# ── Video Scope Clips ─────────────────────────────────────────────────


def _surface_to_frame(surface: cairo.ImageSurface, h: int, w: int) -> np.ndarray:
    """Convert a Cairo surface to a BGRA numpy array."""
    buf = surface.get_data()
    return np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=bytes(buf)).copy()


@dataclass
class WaveformScopeClip(Clip):
    """Luma waveform monitor visualization.

    Renders a waveform scope showing the luminance distribution of
    a source frame, similar to a broadcast waveform monitor.

    Args:
        source_frame: BGRA uint8 frame to analyze.
        color: Scope trace color.
        background: Background color.
    """

    source_frame: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 4), dtype=np.uint8))
    color: Color = field(default_factory=lambda: Color.parse("#00FF00"))
    background: Color = field(default_factory=lambda: Color.parse("#000000"))

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a waveform scope frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA uint8 frame (H, W, 4).
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        bg = self.background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        if self.source_frame.size <= 4:
            return _surface_to_frame(surface, h, w)

        # Compute luma from source
        src = self.source_frame[:, :, :3].astype(np.float64) / 255.0
        # BT.709 luma: Y = 0.2126R + 0.7152G + 0.0722B (BGRA order)
        luma = 0.0722 * src[:, :, 0] + 0.7152 * src[:, :, 1] + 0.2126 * src[:, :, 2]

        src_h, src_w = luma.shape
        c = self.color

        # For each x column in output, map to source column
        for ox in range(w):
            sx = int(ox * src_w / w)
            sx = min(sx, src_w - 1)
            col_luma = luma[:, sx]

            # Draw points at luma positions
            cr.set_source_rgba(c.r, c.g, c.b, 0.15)
            for val in col_luma:
                y = int((1.0 - val) * h)
                y = max(0, min(h - 1, y))
                cr.rectangle(ox, y, 1, 1)
            cr.fill()

        return _surface_to_frame(surface, h, w)


@dataclass
class VectorscopeClip(Clip):
    """Chrominance vectorscope visualization.

    Displays the color distribution of a source frame on a
    chrominance diagram.

    Args:
        source_frame: BGRA uint8 frame to analyze.
        background: Background color.
    """

    source_frame: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 4), dtype=np.uint8))
    background: Color = field(default_factory=lambda: Color.parse("#000000"))

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a vectorscope frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA uint8 frame (H, W, 4).
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        bg = self.background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        if self.source_frame.size <= 4:
            return _surface_to_frame(surface, h, w)

        # Convert to YCbCr
        src = self.source_frame[:, :, :3].astype(np.float64) / 255.0
        r = src[:, :, 2]  # BGRA → R
        g = src[:, :, 1]
        b = src[:, :, 0]

        cb = -0.168736 * r - 0.331264 * g + 0.5 * b
        cr_val = 0.5 * r - 0.418688 * g - 0.081312 * b

        # Map Cb, Cr to display coordinates
        cx, cy = w / 2.0, h / 2.0
        scale = min(w, h) / 2.0 * 0.9

        # Subsample for performance
        step = max(1, self.source_frame.shape[0] * self.source_frame.shape[1] // 50000)
        cb_flat = cb.flatten()[::step]
        cr_flat = cr_val.flatten()[::step]

        cr.set_source_rgba(0.0, 1.0, 0.0, 0.1)
        for i in range(len(cb_flat)):
            px = cx + cb_flat[i] * scale * 2
            py = cy - cr_flat[i] * scale * 2
            cr.rectangle(int(px), int(py), 1, 1)
        cr.fill()

        # Draw crosshair
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        cr.set_line_width(1)
        cr.move_to(w / 2, 0)
        cr.line_to(w / 2, h)
        cr.move_to(0, h / 2)
        cr.line_to(w, h / 2)
        cr.stroke()

        return _surface_to_frame(surface, h, w)


@dataclass
class HistogramClip(Clip):
    """Per-channel histogram visualization.

    Renders RGB histograms of a source frame.

    Args:
        source_frame: BGRA uint8 frame to analyze.
        channels: Which channels to show (``"rgb"``, ``"r"``, ``"g"``,
                  ``"b"``, ``"luma"``).
        background: Background color.
    """

    source_frame: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 4), dtype=np.uint8))
    channels: str = "rgb"
    background: Color = field(default_factory=lambda: Color.parse("#000000"))

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a histogram frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA uint8 frame (H, W, 4).
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        bg = self.background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        if self.source_frame.size <= 4:
            return _surface_to_frame(surface, h, w)

        src = self.source_frame[:, :, :3]  # BGR

        channel_configs: list[tuple[int, tuple[float, float, float]]] = []
        if "r" in self.channels:
            channel_configs.append((2, (1.0, 0.0, 0.0)))  # R in BGRA is index 2
        if "g" in self.channels:
            channel_configs.append((1, (0.0, 1.0, 0.0)))
        if "b" in self.channels:
            channel_configs.append((0, (0.0, 0.0, 1.0)))
        if self.channels == "luma":
            channel_configs = [(-1, (1.0, 1.0, 1.0))]

        for ch_idx, color in channel_configs:
            if ch_idx == -1:
                data = (
                    0.0722 * src[:, :, 0].astype(np.float64)
                    + 0.7152 * src[:, :, 1].astype(np.float64)
                    + 0.2126 * src[:, :, 2].astype(np.float64)
                ).astype(np.uint8)
            else:
                data = src[:, :, ch_idx]

            hist = np.bincount(data.flatten(), minlength=256).astype(np.float64)
            peak = np.max(hist)
            if peak > 0:
                hist /= peak

            cr.set_source_rgba(color[0], color[1], color[2], 0.5)
            bar_w = w / 256.0
            for i in range(256):
                bar_h = hist[i] * h * 0.9
                x = i * bar_w
                y = h - bar_h
                cr.rectangle(x, y, max(bar_w, 1), bar_h)
            cr.fill()

        return _surface_to_frame(surface, h, w)


@dataclass
class ParadeScopeClip(Clip):
    """RGB parade monitor visualization.

    Displays R, G, B waveforms side by side.

    Args:
        source_frame: BGRA uint8 frame to analyze.
        background: Background color.
    """

    source_frame: np.ndarray = field(default_factory=lambda: np.zeros((1, 1, 4), dtype=np.uint8))
    background: Color = field(default_factory=lambda: Color.parse("#000000"))

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a parade scope frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA uint8 frame (H, W, 4).
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        bg = self.background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        if self.source_frame.size <= 4:
            return _surface_to_frame(surface, h, w)

        src = self.source_frame[:, :, :3].astype(np.float64) / 255.0
        src_h, src_w = src.shape[:2]
        panel_w = w // 3

        # RGB channels (BGRA order: 0=B, 1=G, 2=R)
        channels = [
            (2, (1.0, 0.0, 0.0)),  # R
            (1, (0.0, 1.0, 0.0)),  # G
            (0, (0.0, 0.0, 1.0)),  # B
        ]

        for panel_idx, (ch_idx, color) in enumerate(channels):
            x_offset = panel_idx * panel_w
            channel = src[:, :, ch_idx]

            cr.set_source_rgba(color[0], color[1], color[2], 0.15)

            for ox in range(panel_w):
                sx = int(ox * src_w / panel_w)
                sx = min(sx, src_w - 1)
                col = channel[:, sx]

                for val in col:
                    y = int((1.0 - val) * h)
                    y = max(0, min(h - 1, y))
                    cr.rectangle(x_offset + ox, y, 1, 1)

            cr.fill()

        # Panel dividers
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        cr.set_line_width(1)
        for i in range(1, 3):
            cr.move_to(i * panel_w, 0)
            cr.line_to(i * panel_w, h)
        cr.stroke()

        return _surface_to_frame(surface, h, w)
