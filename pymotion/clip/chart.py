"""Chart clips — animated data visualization rendered via Cairo.

Provides BarChartClip and related chart types for rendering animated
data visualizations as video clips.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.design.motion import ease_out_quart
from pymotion.design.renderer import (
    draw_rounded_rect_top,
    set_text_rendering,
)
from pymotion.design.tokens import (
    CHART_COLORS,
    NEUTRAL,
    safe_h,
    safe_v,
)
from pymotion.utils.color import Color

# Type for chart data: list, dict, or per-frame callable
ChartData = Sequence[float] | dict[str, float] | Callable[[int], Sequence[float]]

# ── Chart Theme ─────────────────────────────────────────────────────────

# Each theme defines: bar_colors, background, axis_color, grid_color,
# label_color, label_font, title_font, gridlines
_THEMES: dict[str, dict[str, Any]] = {
    "corporate": {
        "bar_colors": list(CHART_COLORS),
        "background": Color(0.0, 0.0, 0.0, 0.0),
        "axis_color": Color.parse("#3F3F46"),
        "grid_color": Color(0.247, 0.247, 0.275, 0.4),
        "label_color": Color.parse("#71717A"),
        "gridlines": True,
    },
    "minimal": {
        "bar_colors": [
            Color.parse("#111827"),
            Color.parse("#374151"),
            Color.parse("#6B7280"),
            Color.parse("#9CA3AF"),
            Color.parse("#D1D5DB"),
            Color.parse("#4B5563"),
        ],
        "background": Color.parse("#FFFFFF"),
        "axis_color": Color.parse("#9CA3AF"),
        "grid_color": Color.parse("#F3F4F6"),
        "label_color": Color.parse("#6B7280"),
        "gridlines": False,
    },
    "neon": {
        "bar_colors": [
            Color.parse("#00FF87"),
            Color.parse("#FF00E5"),
            Color.parse("#00D4FF"),
            Color.parse("#FFE500"),
            Color.parse("#FF6B00"),
            Color.parse("#A855F7"),
        ],
        "background": Color.parse("#0A0A0A"),
        "axis_color": Color.parse("#404040"),
        "grid_color": Color.parse("#1A1A1A"),
        "label_color": Color.parse("#A0A0A0"),
        "gridlines": True,
    },
    "gradient": {
        "bar_colors": [
            Color.parse("#6366F1"),
            Color.parse("#8B5CF6"),
            Color.parse("#A855F7"),
            Color.parse("#C084FC"),
            Color.parse("#D8B4FE"),
            Color.parse("#7C3AED"),
        ],
        "background": Color.parse("#FAFAFA"),
        "axis_color": Color.parse("#4B5563"),
        "grid_color": Color.parse("#E5E7EB"),
        "label_color": Color.parse("#4B5563"),
        "gridlines": True,
    },
}


def _get_theme(name: str) -> dict[str, Any]:
    """Return a chart theme by name.

    Args:
        name: Theme name (corporate, minimal, neon, gradient).

    Returns:
        Theme dictionary.

    Raises:
        ValueError: If the theme name is unknown.
    """
    if name not in _THEMES:
        valid = ", ".join(sorted(_THEMES))
        msg = f"Unknown chart theme '{name}'. Valid themes: {valid}"
        raise ValueError(msg)
    return _THEMES[name]


def _resolve_data(
    data: ChartData,
    frame: int,
) -> tuple[list[float], list[str] | None]:
    """Resolve chart data to a list of float values.

    Args:
        data: Chart data in any supported format.
        frame: Current frame number (for callable data).

    Returns:
        Tuple of (values, keys_or_none).
    """
    if callable(data):
        raw = data(frame)
        if isinstance(raw, dict):
            return list(raw.values()), list(raw.keys())
        return list(raw), None
    if isinstance(data, dict):
        return list(data.values()), list(data.keys())
    return list(data), None


def _resolve_labels(
    labels: Sequence[str] | None,
    data_keys: list[str] | None,
    count: int,
) -> list[str]:
    """Resolve bar labels from explicit labels, dict keys, or indices.

    Args:
        labels: Explicit labels, if provided.
        data_keys: Keys from dict data, if any.
        count: Number of data values.

    Returns:
        List of label strings.
    """
    if labels is not None:
        return list(labels)
    if data_keys is not None:
        return data_keys
    return [str(i) for i in range(count)]


def _clamp01(v: float) -> float:
    """Clamp a value to [0, 1]."""
    return max(0.0, min(1.0, v))


def _ease_out_cubic(t: float) -> float:
    """Ease-out curve for animation — delegates to design system ease_out_quart.

    Args:
        t: Progress value (0.0 to 1.0).

    Returns:
        Eased value.
    """
    return ease_out_quart(t)


@dataclass
class BarChartClip(Clip):
    """Animated bar chart clip — bars grow from the baseline.

    Renders a bar chart using Cairo, with smooth grow-in animation over
    ``animate_duration`` frames. Supports theming, custom colors, labels,
    and per-frame callable data for live binding.

    Args:
        data: Chart data as a list of numbers, dict mapping label→value,
            or a callable ``(frame) -> list[float]`` for live data.
        labels: Optional list of bar labels. If data is a dict, keys are
            used. Falls back to numeric indices.
        animate_duration: Number of frames for the grow-in animation.
            Bars grow from zero to full height. 0 means no animation.
        theme: Visual theme name: ``"corporate"``, ``"minimal"``,
            ``"neon"``, or ``"gradient"``.
        bar_colors: Optional list of bar colors (overrides theme colors).
        title: Optional chart title displayed above the chart.
        bar_gap: Gap between bars as a fraction of bar width (0.0–1.0).
        show_values: If True, display data values above each bar.
        padding: Padding around the chart area as (left, top, right, bottom).
    """

    data: ChartData = field(default_factory=list)
    labels: Sequence[str] | None = None
    animate_duration: int = 30
    theme: str = "corporate"
    bar_colors: list[Color] | None = None
    title: str | None = None
    bar_gap: float = 0.3
    show_values: bool = False
    padding: tuple[float, float, float, float] = (80.0, 60.0, 40.0, 60.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render an animated bar chart frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: transparent (from theme)
        # Layout: safe zone margins, y-axis labels left, x-axis labels bottom
        # Title: Inter SemiBold 18*scale, neutral_100, top-left of chart area
        # Grid: 4 horizontal lines at 25/50/75/100%, neutral_700 40%
        # Y-axis labels: JetBrains Mono 11*scale, neutral_400, right-aligned
        # Bars: CHART_PALETTE, 55% of bar_unit, rounded top corners 4*scale
        # X-axis labels: JetBrains Mono 11*scale, neutral_400, centered
        # Value labels: JetBrains Mono SemiBold 12*scale, neutral_100, above bar
        # Animation: staggered per-bar grow, ease_out_quart
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        scale = h / 1080

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        theme_cfg = _get_theme(self.theme)

        # Background
        bg = theme_cfg["background"]
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
        cr.paint()

        values, data_keys = _resolve_data(self.data, ctx.local_frame)
        if not values:
            return _surface_to_frame(surface, h, w)

        bar_labels = _resolve_labels(self.labels, data_keys, len(values))
        colors = self.bar_colors if self.bar_colors else theme_cfg["bar_colors"]

        n100 = NEUTRAL.n100
        n400 = NEUTRAL.n400
        n700 = NEUTRAL.n700

        # Layout with safe zones
        sh = safe_h(w)
        sv = safe_v(h)
        title_area_h = 30.0 * scale
        y_axis_label_w = 60.0 * scale
        x_axis_label_h = 24.0 * scale

        chart_left = sh + y_axis_label_w
        chart_top = sv + title_area_h
        chart_right = w - sh
        chart_bottom = h - sv - x_axis_label_h
        chart_w = chart_right - chart_left
        chart_h = chart_bottom - chart_top

        if chart_w <= 0 or chart_h <= 0:
            return _surface_to_frame(surface, h, w)

        max_val = max(abs(v) for v in values) if values else 1.0
        if max_val == 0:
            max_val = 1.0

        # Title (from labels[0] if it looks like a title, else from self.title)
        title_text = self.title or ""
        if not title_text and bar_labels and len(bar_labels) > 0:
            # Use first label only if it's not a data key
            pass
        if title_text:
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(18.0 * scale)
            cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
            cr.move_to(chart_left, sv + 18.0 * scale)
            cr.show_text(title_text)

        # Grid lines (4 horizontal at 25/50/75/100%)
        cr.set_line_width(1.0 * scale)
        for i in range(1, 5):
            gy = chart_bottom - (i / 4.0) * chart_h
            cr.set_source_rgba(n700.r, n700.g, n700.b, 0.4)
            cr.move_to(chart_left, gy)
            cr.line_to(chart_right, gy)
            cr.stroke()

        # Y-axis labels
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11.0 * scale)
        for i in range(5):
            label_val = (i / 4.0) * max_val
            label_text_y = (
                f"{int(label_val)}" if label_val == int(label_val) else f"{label_val:.0f}"
            )
            gy = chart_bottom - (i / 4.0) * chart_h
            ext = cr.text_extents(label_text_y)
            cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
            cr.move_to(chart_left - ext.width - 8.0 * scale, gy + ext.height / 2.0)
            cr.show_text(label_text_y)

        # Bar geometry
        n_bars = len(values)
        bar_unit = chart_w / n_bars
        bar_width = bar_unit * 0.55
        gap_w = bar_unit * 0.45
        stagger_frames = 4
        radius = 4.0 * scale

        for i, val in enumerate(values):
            # Staggered animation
            bar_start = i * stagger_frames
            if self.animate_duration > 0 and ctx.local_frame < bar_start + self.animate_duration:
                bar_progress = _clamp01(
                    (ctx.local_frame - bar_start) / max(1, self.animate_duration)
                )
                bar_t = ease_out_quart(bar_progress) if bar_progress > 0 else 0.0
            else:
                bar_t = 1.0

            color = colors[i % len(colors)]
            bar_h = (abs(val) / max_val) * chart_h * bar_t
            bar_x = chart_left + i * bar_unit + gap_w / 2.0
            bar_y = chart_bottom - bar_h

            if bar_h > 0:
                cr.set_source_rgba(color.r, color.g, color.b, color.a)
                if bar_h > radius * 2:
                    draw_rounded_rect_top(cr, bar_x, bar_y, bar_width, bar_h, radius)
                    cr.fill()
                else:
                    cr.rectangle(bar_x, bar_y, bar_width, bar_h)
                    cr.fill()

            # X-axis label
            label_text_x = bar_labels[i] if i < len(bar_labels) else ""
            cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(11.0 * scale)
            cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
            ext = cr.text_extents(label_text_x)
            lx = bar_x + bar_width / 2.0 - ext.width / 2.0
            cr.move_to(lx, chart_bottom + 8.0 * scale + ext.height)
            cr.show_text(label_text_x)

            # Value label above bar (only after bar finishes animating)
            if self.show_values and bar_t >= 1.0:
                val_text = str(int(val)) if val == int(val) else f"{val:.1f}"
                cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(12.0 * scale)
                cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
                vext = cr.text_extents(val_text)
                cr.move_to(
                    bar_x + bar_width / 2.0 - vext.width / 2.0,
                    bar_y - 6.0 * scale,
                )
                cr.show_text(val_text)

        frame = _surface_to_frame(surface, h, w)
        if self.theme == "neon":
            frame = _apply_neon_glow(frame)
        return frame


def _apply_neon_glow(frame: np.ndarray) -> np.ndarray:
    """Apply a neon glow post-process to a frame.

    Extracts bright pixels, blurs them, and blends additively to
    create a glow effect around neon-colored elements.

    Args:
        frame: BGRA frame to process.

    Returns:
        Frame with glow applied.
    """
    h, w = frame.shape[:2]
    # Extract bright pixels (above threshold on any RGB channel)
    rgb = frame[:, :, :3].astype(np.float32)
    brightness = np.max(rgb, axis=2)
    bright_mask = brightness > 100.0

    # Create glow layer from bright pixels only
    glow = np.zeros_like(rgb)
    glow[bright_mask] = rgb[bright_mask]

    # Simple box blur (two passes for smoother result)
    for _ in range(2):
        # Horizontal blur
        kernel_size = max(3, min(15, w // 60))
        padded = np.pad(glow, ((0, 0), (kernel_size, kernel_size), (0, 0)), mode="edge")
        cumsum = np.cumsum(padded, axis=1)
        glow = (cumsum[:, 2 * kernel_size :, :] - cumsum[:, :w, :]) / (2 * kernel_size)
        # Vertical blur
        padded = np.pad(glow, ((kernel_size, kernel_size), (0, 0), (0, 0)), mode="edge")
        cumsum = np.cumsum(padded, axis=0)
        glow = (cumsum[2 * kernel_size :, :, :] - cumsum[:h, :, :]) / (2 * kernel_size)

    # Additive blend glow onto original
    result = frame[:, :, :3].astype(np.float32) + glow * 0.6
    out = frame.copy()
    out[:, :, :3] = np.clip(result, 0, 255).astype(np.uint8)
    return out


def _draw_chart_frame(
    w: int,
    h: int,
    theme_cfg: dict[str, Any],
    padding: tuple[float, float, float, float],
    title: str | None,
) -> tuple[cairo.ImageSurface, cairo.Context[cairo.ImageSurface], float, float, float, float]:
    """Create a Cairo surface and draw common chart chrome (background, axes, grid).

    Args:
        w: Frame width.
        h: Frame height.
        theme_cfg: Theme configuration dict.
        padding: (left, top, right, bottom) padding.
        title: Optional chart title.

    Returns:
        Tuple of (surface, context, chart_x, chart_y, chart_w, chart_h).
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

    bg = theme_cfg["background"]
    cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a)
    cr.paint()

    pad_l, pad_t, pad_r, pad_b = padding
    chart_x = pad_l
    chart_y = pad_t
    chart_w = w - pad_l - pad_r
    chart_h = h - pad_t - pad_b

    if title and chart_w > 0 and chart_h > 0:
        label_color = theme_cfg["label_color"]
        cr.set_source_rgba(label_color.r, label_color.g, label_color.b, label_color.a)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        title_size = max(14.0, min(24.0, w * 0.03))
        cr.set_font_size(title_size)
        title_extents = cr.text_extents(title)
        title_x = w / 2 - title_extents.width / 2
        title_y = pad_t / 2 + title_size / 2
        cr.move_to(title_x, title_y)
        cr.show_text(title)

    return surface, cr, chart_x, chart_y, chart_w, chart_h


def _surface_to_frame(
    surface: cairo.ImageSurface,
    h: int,
    w: int,
    theme: str | None = None,
) -> np.ndarray:
    """Convert a Cairo surface to a BGRA numpy array.

    Args:
        surface: The Cairo image surface.
        h: Frame height.
        w: Frame width.
        theme: Chart theme name. If ``"neon"``, applies glow post-process.

    Returns:
        BGRA numpy array of shape (h, w, 4), dtype uint8.
    """
    buf = surface.get_data()
    frame = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=bytes(buf)).copy()
    if theme == "neon":
        frame = _apply_neon_glow(frame)
    return frame


def _draw_axes_and_grid(
    cr: cairo.Context[cairo.ImageSurface],
    theme_cfg: dict[str, Any],
    chart_x: float,
    chart_y: float,
    chart_w: float,
    chart_h: float,
    max_val: float,
) -> None:
    """Draw grid lines, axes, and Y-axis labels.

    Args:
        cr: Cairo context.
        theme_cfg: Theme configuration.
        chart_x: Chart area left.
        chart_y: Chart area top.
        chart_w: Chart area width.
        chart_h: Chart area height.
        max_val: Maximum data value for Y-axis labels.
    """
    n_grid = 5
    if theme_cfg["gridlines"]:
        grid_color = theme_cfg["grid_color"]
        cr.set_source_rgba(grid_color.r, grid_color.g, grid_color.b, grid_color.a)
        cr.set_line_width(1.0)
        for i in range(n_grid + 1):
            gy = chart_y + chart_h - (i / n_grid) * chart_h
            cr.move_to(chart_x, gy)
            cr.line_to(chart_x + chart_w, gy)
            cr.stroke()

    axis_color = theme_cfg["axis_color"]
    cr.set_source_rgba(axis_color.r, axis_color.g, axis_color.b, axis_color.a)
    cr.set_line_width(2.0)
    cr.move_to(chart_x, chart_y + chart_h)
    cr.line_to(chart_x + chart_w, chart_y + chart_h)
    cr.stroke()
    cr.move_to(chart_x, chart_y)
    cr.line_to(chart_x, chart_y + chart_h)
    cr.stroke()

    # Y-axis labels
    label_color = theme_cfg["label_color"]
    cr.set_source_rgba(label_color.r, label_color.g, label_color.b, label_color.a)
    cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    y_label_size = max(9.0, min(13.0, 12.0))
    cr.set_font_size(y_label_size)
    for i in range(n_grid + 1):
        lv = (i / n_grid) * max_val
        lt = f"{lv:.0f}" if lv == int(lv) else f"{lv:.1f}"
        gy = chart_y + chart_h - (i / n_grid) * chart_h
        ext = cr.text_extents(lt)
        cr.move_to(chart_x - ext.width - 8, gy + ext.height / 2)
        cr.show_text(lt)


# ── LineChartClip ───────────────────────────────────────────────────────


@dataclass
class LineChartClip(Clip):
    """Animated line chart clip — line draws on from left to right.

    Renders a line chart using Cairo, with a draw-on animation that
    reveals the line progressively over ``animate_duration`` frames.

    Args:
        data: Chart data as a list, dict, or per-frame callable.
        labels: Optional X-axis labels.
        animate_duration: Frames for the draw-on animation.
        theme: Visual theme name.
        line_colors: Optional list of line colors (overrides theme).
        title: Optional chart title.
        line_width: Width of the data line in pixels.
        show_dots: If True, draw dots at data points.
        show_fill: If True, fill the area under the line.
        padding: Padding around the chart area.
    """

    data: ChartData = field(default_factory=list)
    labels: Sequence[str] | None = None
    animate_duration: int = 30
    theme: str = "corporate"
    line_colors: list[Color] | None = None
    title: str | None = None
    line_width: float = 2.0
    show_dots: bool = True
    show_fill: bool = False
    padding: tuple[float, float, float, float] = (80.0, 60.0, 40.0, 60.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render an animated line chart frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Layout: safe_h/safe_v margins, 60*scale y-axis label area
        # Z-order:
        #   1. Title: Inter Bold 18*scale, neutral_100, top-left in safe zone
        #   2. Grid: 4 horizontal lines at 25/50/75/100%, neutral_700 at 0.3 alpha
        #   3. Y-axis labels: JetBrains Mono 11*scale, neutral_400, integer values
        #   4. Fill area: accent color at 0.12 alpha (if show_fill)
        #   5. Line: accent color, line_width*scale, rounded joins/caps
        #   6. Dots: filled accent circles, radius 4*scale (if show_dots)
        #   7. X-axis labels: JetBrains Mono 11*scale, neutral_400
        # Animation: progressive point reveal via ease_out_quart
        # All pixel values scaled by comp_height / 1080
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        scale = h / 1080

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        values, data_keys = _resolve_data(self.data, ctx.local_frame)
        if not values:
            return _surface_to_frame(surface, h, w)

        max_val = max(abs(v) for v in values)
        if max_val == 0:
            max_val = 1.0

        n100 = NEUTRAL.n100
        n400 = NEUTRAL.n400
        n700 = NEUTRAL.n700

        sh = safe_h(w)
        sv = safe_v(h)
        y_label_w = 60.0 * scale
        chart_left = sh + y_label_w
        chart_top = sv + 40.0 * scale
        chart_right = w - sh
        chart_bottom = h - sv - 30.0 * scale
        chart_w = chart_right - chart_left
        chart_h = chart_bottom - chart_top

        if chart_w <= 0 or chart_h <= 0:
            return _surface_to_frame(surface, h, w)

        # Title
        if self.title:
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(18.0 * scale)
            cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
            cr.move_to(sh, sv + 20.0 * scale)
            cr.show_text(self.title)

        # Grid lines (4 at 25/50/75/100%)
        cr.set_source_rgba(n700.r, n700.g, n700.b, 0.3)
        cr.set_line_width(1.0 * scale)
        for i in range(1, 5):
            gy = chart_bottom - (i / 4.0) * chart_h
            cr.move_to(chart_left, gy)
            cr.line_to(chart_right, gy)
            cr.stroke()

        # Y-axis labels
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11.0 * scale)
        for i in range(5):
            label_val = (i / 4.0) * max_val
            label_text = f"{int(label_val)}"
            gy = chart_bottom - (i / 4.0) * chart_h
            ext = cr.text_extents(label_text)
            cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
            cr.move_to(chart_left - ext.width - 8.0 * scale, gy + ext.height / 2.0)
            cr.show_text(label_text)

        # Animation progress
        if self.animate_duration > 0 and ctx.local_frame < self.animate_duration:
            anim_t = ease_out_quart(ctx.local_frame / self.animate_duration)
        else:
            anim_t = 1.0

        colors = self.line_colors if self.line_colors else _get_theme(self.theme)["bar_colors"]
        color = colors[0]
        n_points = len(values)
        visible = max(1, int(n_points * anim_t))

        # Compute point positions
        points: list[tuple[float, float]] = []
        for i in range(n_points):
            if n_points > 1:
                px = chart_left + (i / (n_points - 1)) * chart_w
            else:
                px = chart_left + chart_w / 2.0
            py = chart_bottom - (values[i] / max_val) * chart_h
            points.append((px, py))

        # Fill area under line
        if self.show_fill and visible > 0:
            cr.set_source_rgba(color.r, color.g, color.b, 0.12)
            cr.move_to(points[0][0], chart_bottom)
            for i in range(visible):
                cr.line_to(points[i][0], points[i][1])
            cr.line_to(points[visible - 1][0], chart_bottom)
            cr.close_path()
            cr.fill()

        # Draw line
        if visible > 0:
            cr.set_source_rgba(color.r, color.g, color.b, color.a)
            cr.set_line_width(self.line_width * scale)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(points[0][0], points[0][1])
            for i in range(1, visible):
                cr.line_to(points[i][0], points[i][1])
            cr.stroke()

        # Draw dots (filled circles)
        if self.show_dots:
            dot_r = 4.0 * scale
            for i in range(visible):
                cr.set_source_rgba(color.r, color.g, color.b, color.a)
                cr.arc(points[i][0], points[i][1], dot_r, 0, 2 * math.pi)
                cr.fill()

        # X-axis labels
        chart_labels = _resolve_labels(self.labels, data_keys, n_points)
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11.0 * scale)
        cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
        for i in range(n_points):
            ext = cr.text_extents(chart_labels[i])
            lx = points[i][0] - ext.width / 2.0
            ly = chart_bottom + 8.0 * scale + ext.height
            cr.move_to(lx, ly)
            cr.show_text(chart_labels[i])

        return _surface_to_frame(surface, h, w)


# ── PieChartClip ────────────────────────────────────────────────────────


@dataclass
class PieChartClip(Clip):
    """Animated pie chart clip — slices sweep in clockwise.

    Args:
        data: Chart data as a list, dict, or per-frame callable.
        labels: Optional slice labels.
        animate_duration: Frames for the sweep-in animation.
        theme: Visual theme name.
        slice_colors: Optional list of slice colors (overrides theme).
        title: Optional chart title.
        show_labels: If True, draw labels next to slices.
        inner_radius: If > 0, creates a donut chart.
        padding: Padding around the chart area.
    """

    data: ChartData = field(default_factory=list)
    labels: Sequence[str] | None = None
    animate_duration: int = 30
    theme: str = "corporate"
    slice_colors: list[Color] | None = None
    title: str | None = None
    show_labels: bool = True
    inner_radius: float = 0.55
    gap_degrees: float = 1.5
    padding: tuple[float, float, float, float] = (60.0, 60.0, 60.0, 60.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render an animated pie chart frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Layout: donut centered at (w/2, h*0.46), radius fits within safe zone
        # Z-order:
        #   1. Title: Inter Bold 18*scale, neutral_100, top-left safe zone
        #   2. Donut slices: sequential sweep via ease_out_quart, gap between slices
        #   3. Center text: total value in JetBrains Mono Bold 28*scale, neutral_100
        #      "TOTAL" label below in Inter 11*scale caps, neutral_400
        #   4. Slice labels: "Label XX%" in Inter 12*scale, neutral_300
        # Animation: clockwise sweep from top (-π/2)
        # All pixel values scaled by comp_height / 1080
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        scale = h / 1080

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        values, data_keys = _resolve_data(self.data, ctx.local_frame)
        if not values:
            return _surface_to_frame(surface, h, w)

        total = sum(abs(v) for v in values)
        if total == 0:
            return _surface_to_frame(surface, h, w)

        n100 = NEUTRAL.n100
        n300 = NEUTRAL.n300
        n400 = NEUTRAL.n400

        sh = safe_h(w)
        sv = safe_v(h)

        # Title
        if self.title:
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(18.0 * scale)
            cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
            cr.move_to(sh, sv + 20.0 * scale)
            cr.show_text(self.title)

        colors = self.slice_colors if self.slice_colors else _get_theme(self.theme)["bar_colors"]
        chart_labels = _resolve_labels(self.labels, data_keys, len(values))

        # Animation
        if self.animate_duration > 0 and ctx.local_frame < self.animate_duration:
            anim_t = ease_out_quart(ctx.local_frame / self.animate_duration)
        else:
            anim_t = 1.0

        cx = w / 2.0
        cy = h * 0.46
        available = min(w - sh * 2, h - sv * 2) / 2.0
        radius = available * 0.65
        inner_r = radius * self.inner_radius

        start_angle = -math.pi / 2
        max_sweep = 2 * math.pi * anim_t
        current_angle = start_angle
        gap_rad = math.radians(self.gap_degrees)

        for i, val in enumerate(values):
            full_slice = (abs(val) / total) * max_sweep
            slice_gap = gap_rad if len(values) > 1 else 0.0
            slice_angle = max(0.0, full_slice - slice_gap)
            slice_start = current_angle + slice_gap / 2.0
            color = colors[i % len(colors)]

            if slice_angle > 0:
                cr.new_sub_path()
                cr.set_source_rgba(color.r, color.g, color.b, color.a)
                if inner_r > 0:
                    cr.arc(cx, cy, radius, slice_start, slice_start + slice_angle)
                    cr.arc_negative(cx, cy, inner_r, slice_start + slice_angle, slice_start)
                    cr.close_path()
                else:
                    cr.move_to(cx, cy)
                    cr.arc(cx, cy, radius, slice_start, slice_start + slice_angle)
                    cr.close_path()
                cr.fill()

            # Label with percentage
            if self.show_labels and anim_t > 0.3:
                mid_angle = slice_start + slice_angle / 2.0
                label_r = radius + 24.0 * scale
                lx = cx + label_r * math.cos(mid_angle)
                ly = cy + label_r * math.sin(mid_angle)

                pct = abs(val) / total * 100
                label_name = chart_labels[i] if i < len(chart_labels) else ""
                label_text = f"{label_name} {pct:.0f}%"
                cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(12.0 * scale)
                cr.set_source_rgba(n300.r, n300.g, n300.b, 1.0)
                ext = cr.text_extents(label_text)
                cr.move_to(lx - ext.width / 2.0, ly + ext.height / 2.0)
                cr.show_text(label_text)

            current_angle += full_slice

        # Center text (total value)
        if inner_r > 0 and anim_t > 0.5:
            total_text = f"{int(total):,}"
            cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(28.0 * scale)
            cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
            ext = cr.text_extents(total_text)
            cr.move_to(cx - ext.width / 2.0, cy + ext.height / 2.0 - 6.0 * scale)
            cr.show_text(total_text)

            # "TOTAL" label
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(11.0 * scale)
            cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
            total_label = "TOTAL"
            ext2 = cr.text_extents(total_label)
            cr.move_to(cx - ext2.width / 2.0, cy + ext.height / 2.0 + 12.0 * scale)
            cr.show_text(total_label)

        return _surface_to_frame(surface, h, w)


# ── AreaChartClip ───────────────────────────────────────────────────────


@dataclass
class AreaChartClip(Clip):
    """Animated area chart clip — filled area variant of line chart.

    Args:
        data: Chart data as a list, dict, or per-frame callable.
        labels: Optional X-axis labels.
        animate_duration: Frames for the draw-on animation.
        theme: Visual theme name.
        area_colors: Optional list of area colors (overrides theme).
        title: Optional chart title.
        fill_opacity: Opacity of the filled area (0.0–1.0).
        padding: Padding around the chart area.
    """

    data: ChartData = field(default_factory=list)
    labels: Sequence[str] | None = None
    animate_duration: int = 30
    theme: str = "corporate"
    area_colors: list[Color] | None = None
    title: str | None = None
    fill_opacity: float = 0.2
    padding: tuple[float, float, float, float] = (80.0, 60.0, 40.0, 60.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render an animated area chart frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        theme_cfg = _get_theme(self.theme)

        surface, cr, chart_x, chart_y, chart_w, chart_h = _draw_chart_frame(
            w, h, theme_cfg, self.padding, self.title
        )

        values, data_keys = _resolve_data(self.data, ctx.local_frame)
        if not values or chart_w <= 0 or chart_h <= 0:
            return _surface_to_frame(surface, h, w)

        max_val = max(abs(v) for v in values)
        if max_val == 0:
            max_val = 1.0

        _draw_axes_and_grid(cr, theme_cfg, chart_x, chart_y, chart_w, chart_h, max_val)

        if self.animate_duration > 0 and ctx.local_frame < self.animate_duration:
            anim_t = _ease_out_cubic(ctx.local_frame / self.animate_duration)
        else:
            anim_t = 1.0

        colors = self.area_colors if self.area_colors else theme_cfg["bar_colors"]
        color = colors[0]
        n_points = len(values)
        visible = max(1, int(n_points * anim_t))

        points: list[tuple[float, float]] = []
        for i in range(n_points):
            if n_points > 1:
                px = chart_x + (i / (n_points - 1)) * chart_w
            else:
                px = chart_x + chart_w / 2
            py = chart_y + chart_h - (values[i] / max_val) * chart_h
            points.append((px, py))

        # Filled area
        if visible > 0:
            cr.set_source_rgba(color.r, color.g, color.b, self.fill_opacity)
            cr.move_to(points[0][0], chart_y + chart_h)
            for i in range(visible):
                cr.line_to(points[i][0], points[i][1])
            cr.line_to(points[visible - 1][0], chart_y + chart_h)
            cr.close_path()
            cr.fill()

        # Line on top
        if visible > 0:
            cr.set_source_rgba(color.r, color.g, color.b, color.a)
            cr.set_line_width(2.0)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.move_to(points[0][0], points[0][1])
            for i in range(1, visible):
                cr.line_to(points[i][0], points[i][1])
            cr.stroke()

        # X-axis labels
        chart_labels = _resolve_labels(self.labels, data_keys, n_points)
        label_color = theme_cfg["label_color"]
        cr.set_source_rgba(label_color.r, label_color.g, label_color.b, label_color.a)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        font_size = max(9.0, min(14.0, chart_w / n_points * 0.4))
        cr.set_font_size(font_size)
        for i in range(n_points):
            ext = cr.text_extents(chart_labels[i])
            cr.move_to(points[i][0] - ext.width / 2, chart_y + chart_h + font_size + 4)
            cr.show_text(chart_labels[i])

        return _surface_to_frame(surface, h, w)


# ── RadarChartClip ──────────────────────────────────────────────────────


@dataclass
class RadarChartClip(Clip):
    """Animated radar (spider) chart clip.

    Args:
        data: Chart data as a list, dict, or per-frame callable.
        axes: Axis labels (one per data point).
        animate_duration: Frames for the grow-in animation.
        theme: Visual theme name.
        fill_color: Optional fill color (overrides theme).
        title: Optional chart title.
        fill_opacity: Opacity of the filled area.
        padding: Padding around the chart area.
    """

    data: ChartData = field(default_factory=list)
    axes: Sequence[str] | None = None
    animate_duration: int = 30
    theme: str = "corporate"
    fill_color: Color | None = None
    title: str | None = None
    fill_opacity: float = 0.3
    padding: tuple[float, float, float, float] = (80.0, 80.0, 80.0, 80.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render an animated radar chart frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        theme_cfg = _get_theme(self.theme)

        surface, cr, chart_x, chart_y, chart_w, chart_h = _draw_chart_frame(
            w, h, theme_cfg, self.padding, self.title
        )

        values, data_keys = _resolve_data(self.data, ctx.local_frame)
        if not values or chart_w <= 0 or chart_h <= 0:
            return _surface_to_frame(surface, h, w)

        max_val = max(abs(v) for v in values)
        if max_val == 0:
            max_val = 1.0

        n = len(values)
        cx = chart_x + chart_w / 2
        cy = chart_y + chart_h / 2
        radius = min(chart_w, chart_h) / 2 * 0.8

        if self.animate_duration > 0 and ctx.local_frame < self.animate_duration:
            anim_t = _ease_out_cubic(ctx.local_frame / self.animate_duration)
        else:
            anim_t = 1.0

        # Draw concentric circle grid rings
        grid_color = theme_cfg["grid_color"]
        cr.set_source_rgba(grid_color.r, grid_color.g, grid_color.b, grid_color.a)
        cr.set_line_width(1.0)
        for ring in range(1, 6):
            r = radius * ring / 5
            cr.new_sub_path()
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()

        # Draw spokes
        axis_color = theme_cfg["axis_color"]
        cr.set_source_rgba(axis_color.r, axis_color.g, axis_color.b, axis_color.a)
        cr.set_line_width(1.0)
        for i in range(n):
            angle = 2 * math.pi * i / n - math.pi / 2
            cr.move_to(cx, cy)
            cr.line_to(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            cr.stroke()

        # Data polygon
        color = self.fill_color if self.fill_color else theme_cfg["bar_colors"][0]
        points: list[tuple[float, float]] = []
        for i in range(n):
            angle = 2 * math.pi * i / n - math.pi / 2
            r = (abs(values[i]) / max_val) * radius * anim_t
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

        # Fill
        cr.set_source_rgba(color.r, color.g, color.b, self.fill_opacity)
        cr.move_to(points[0][0], points[0][1])
        for i in range(1, n):
            cr.line_to(points[i][0], points[i][1])
        cr.close_path()
        cr.fill()

        # Outline
        cr.set_source_rgba(color.r, color.g, color.b, color.a)
        cr.set_line_width(2.0)
        cr.move_to(points[0][0], points[0][1])
        for i in range(1, n):
            cr.line_to(points[i][0], points[i][1])
        cr.close_path()
        cr.stroke()

        # Dots at vertices
        for px, py in points:
            cr.set_source_rgba(color.r, color.g, color.b, color.a)
            cr.arc(px, py, 4, 0, 2 * math.pi)
            cr.fill()

        # Axis labels
        axis_labels = list(self.axes) if self.axes else _resolve_labels(None, data_keys, n)
        label_color = theme_cfg["label_color"]
        cr.set_source_rgba(label_color.r, label_color.g, label_color.b, label_color.a)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(max(9.0, min(13.0, radius * 0.12)))
        for i in range(n):
            angle = 2 * math.pi * i / n - math.pi / 2
            lx = cx + (radius + 16) * math.cos(angle)
            ly = cy + (radius + 16) * math.sin(angle)
            ext = cr.text_extents(axis_labels[i])
            cr.move_to(lx - ext.width / 2, ly + ext.height / 2)
            cr.show_text(axis_labels[i])

        return _surface_to_frame(surface, h, w)


# ── ScatterPlotClip ─────────────────────────────────────────────────────


@dataclass
class ScatterPlotClip(Clip):
    """Animated scatter plot clip — points appear progressively.

    Args:
        x: X-axis data values.
        y: Y-axis data values (must be same length as x).
        labels: Optional point labels.
        animate_duration: Frames for the appear animation.
        theme: Visual theme name.
        point_color: Optional point color (overrides theme).
        title: Optional chart title.
        point_size: Radius of scatter dots in pixels.
        padding: Padding around the chart area.
    """

    x: Sequence[float] = field(default_factory=list)
    y: Sequence[float] = field(default_factory=list)
    labels: Sequence[str] | None = None
    animate_duration: int = 30
    theme: str = "corporate"
    point_color: Color | None = None
    title: str | None = None
    point_size: float = 4.0
    padding: tuple[float, float, float, float] = (80.0, 60.0, 40.0, 60.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render an animated scatter plot frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        theme_cfg = _get_theme(self.theme)

        surface, cr, chart_x, chart_y, chart_w, chart_h = _draw_chart_frame(
            w, h, theme_cfg, self.padding, self.title
        )

        x_vals = list(self.x)
        y_vals = list(self.y)
        if not x_vals or not y_vals or chart_w <= 0 or chart_h <= 0:
            return _surface_to_frame(surface, h, w)

        n = min(len(x_vals), len(y_vals))
        x_vals = x_vals[:n]
        y_vals = y_vals[:n]

        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        if x_max == x_min:
            x_max = x_min + 1
        if y_max == y_min:
            y_max = y_min + 1

        _draw_axes_and_grid(cr, theme_cfg, chart_x, chart_y, chart_w, chart_h, y_max)

        if self.animate_duration > 0 and ctx.local_frame < self.animate_duration:
            anim_t = _ease_out_cubic(ctx.local_frame / self.animate_duration)
        else:
            anim_t = 1.0

        visible = max(1, int(n * anim_t))
        color = self.point_color if self.point_color else theme_cfg["bar_colors"][0]

        for i in range(visible):
            px = chart_x + ((x_vals[i] - x_min) / (x_max - x_min)) * chart_w
            py = chart_y + chart_h - ((y_vals[i] - y_min) / (y_max - y_min)) * chart_h
            cr.set_source_rgba(color.r, color.g, color.b, color.a)
            cr.arc(px, py, self.point_size, 0, 2 * math.pi)
            cr.fill()

        return _surface_to_frame(surface, h, w)


# ── NumberCounter ───────────────────────────────────────────────────────


@dataclass
class NumberCounter(Clip):
    """Animated number counter — displays a number animating from start to end.

    Renders a large number that counts from ``start_value`` to ``end_value``
    over ``count_duration`` frames.

    Args:
        start_value: Starting number.
        end_value: Ending number.
        count_duration: Frames for the counting animation.
        format_fn: Optional formatting function applied to the current value.
        font: Font family name.
        size: Font size in pixels.
        color: Text color.
        padding: Padding around the text.
    """

    start_value: float = 0.0
    end_value: float = 100.0
    count_duration: int = 60
    format_fn: Callable[[float], str] | None = None
    font: str = "sans-serif"
    size: float = 72.0
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0, 1.0))
    padding: tuple[float, float, float, float] = (20.0, 20.0, 20.0, 20.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a number counter frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent)
        # Z-order:
        #   1. Number: JetBrains Mono Bold 96*scale, neutral_100, centered
        #      Formatted with comma separators, ease_out_quart counting
        #   2. Label (optional): Inter Medium 13*scale, ALL CAPS 0.1em, neutral_400
        # Position: horizontal center, comp_height * 0.44
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        scale = h / 1080

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        # Easing: ease_out_quart
        if self.count_duration > 0 and ctx.local_frame < self.count_duration:
            raw_t = ctx.local_frame / self.count_duration
            t = 1.0 - (1.0 - raw_t) ** 4  # ease_out_quart
        else:
            t = 1.0

        current = self.start_value + (self.end_value - self.start_value) * t

        # Format: default comma-separated integers
        if self.format_fn is not None:
            text = self.format_fn(current)
        else:
            text = f"{int(current):,}"

        n100 = NEUTRAL.n100

        # Position
        cx = self._position.x if self._position.x != 0.0 else w / 2.0
        cy = self._position.y if self._position.y != 0.0 else h * 0.44

        # Number
        num_size = 96.0 * scale
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(num_size)
        cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
        extents = cr.text_extents(text)
        tx = cx - extents.width / 2.0
        ty = cy + extents.height / 2.0
        cr.move_to(tx, ty)
        cr.show_text(text)

        return _surface_to_frame(surface, h, w)


# ── ProgressBar ─────────────────────────────────────────────────────────


@dataclass
class ProgressBar(Clip):
    """Animated progress bar clip.

    Renders a horizontal progress bar. The ``value`` can be a static float
    (0.0–1.0) or an animatable value that changes per frame.

    Args:
        value: Progress value (0.0–1.0). Can be a float or a callable
            ``(frame) -> float`` for animation.
        bar_width: Width of the bar in pixels.
        bar_height: Height of the bar in pixels.
        fill_color: Color of the filled portion.
        bg_color: Color of the unfilled background.
        radius: Corner radius of the bar.
        padding: Padding around the bar.
    """

    value: float | Callable[[int], float] = 0.5
    bar_width: float = 400.0
    bar_height: float = 8.0
    fill_color: Color = field(default_factory=lambda: Color.parse("#6366F1"))
    bg_color: Color = field(default_factory=lambda: Color.parse("#27272A"))
    radius: float = 9999.0
    padding: tuple[float, float, float, float] = (20.0, 20.0, 20.0, 20.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a progress bar frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent)
        # Z-order:
        #   1. Track: full width pill, 8*scale high, neutral_800
        #   2. Fill: accent pill, width = track * value
        #      Leading edge glow: 1px accent_300 at rightmost edge
        #   3. Percentage label: JetBrains Mono Medium 12*scale, neutral_400
        # Position: horizontal center, near bottom (safe_v + 8*scale)
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        scale = h / 1080

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        # Resolve value
        if callable(self.value):
            val = max(0.0, min(1.0, self.value(ctx.local_frame)))
        else:
            val = max(0.0, min(1.0, self.value))

        # Use position if set, else default to near bottom center
        sv = safe_v(h)
        track_w = self.bar_width
        track_h = self.bar_height * scale
        bx = self._position.x - track_w / 2.0 if self._position.x != 0.0 else (w - track_w) / 2.0
        by = self._position.y - track_h / 2.0 if self._position.y != 0.0 else h - sv - track_h
        r = min(self.radius, track_h / 2.0, track_w / 2.0)

        n800 = NEUTRAL.n800

        # LAYER 1: Track
        _rounded_rect(cr, bx, by, track_w, track_h, r)
        cr.set_source_rgba(n800.r, n800.g, n800.b, 1.0)
        cr.fill()

        # LAYER 2: Fill
        fill_w = track_w * val
        if fill_w > 0:
            _rounded_rect(cr, bx, by, fill_w, track_h, r)
            cr.set_source_rgba(
                self.fill_color.r, self.fill_color.g, self.fill_color.b, self.fill_color.a
            )
            cr.fill()

            # Leading edge glow
            if fill_w > 4.0 * scale:
                from pymotion.design.tokens import ACCENT

                a300 = ACCENT.a300
                cr.set_source_rgba(a300.r, a300.g, a300.b, 0.8)
                cr.set_line_width(1.0 * scale)
                edge_x = bx + fill_w - 2.0 * scale
                cr.move_to(edge_x, by + 1.0 * scale)
                cr.line_to(edge_x, by + track_h - 1.0 * scale)
                cr.stroke()

        # LAYER 3: Percentage label
        n400 = NEUTRAL.n400
        pct_text = f"{int(val * 100)}%"
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12.0 * scale)
        cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
        pext = cr.text_extents(pct_text)
        cr.move_to(bx + track_w + 8.0 * scale, by + track_h / 2.0 + pext.height / 2.0)
        cr.show_text(pct_text)

        return _surface_to_frame(surface, h, w)


def _rounded_rect(
    cr: cairo.Context[cairo.ImageSurface],
    x: float,
    y: float,
    w: float,
    h: float,
    r: float,
) -> None:
    """Draw a rounded rectangle path.

    Args:
        cr: Cairo context.
        x: Left edge.
        y: Top edge.
        w: Width.
        h: Height.
        r: Corner radius.
    """
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()
