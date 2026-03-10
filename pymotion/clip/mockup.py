"""Screen and device mockup clips — browser, phone, and desktop frames.

Wraps a content clip inside a device frame (browser chrome, phone bezel,
or desktop window) for professional screen recordings and app demos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.utils.color import Color


def _surface_to_frame(
    surface: cairo.ImageSurface,
    h: int,
    w: int,
) -> np.ndarray:
    """Convert a Cairo surface to a BGRA numpy array.

    Args:
        surface: The Cairo image surface.
        h: Frame height.
        w: Frame width.

    Returns:
        BGRA numpy array of shape (h, w, 4), dtype uint8.
    """
    buf = surface.get_data()
    return np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=bytes(buf)).copy()


def _ease_out_cubic(t: float) -> float:
    """Cubic ease-out."""
    return 1.0 - (1.0 - t) ** 3


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


def _composite_content(
    cr: cairo.Context[cairo.ImageSurface],
    content_clip: Clip | None,
    ctx: RenderContext,
    cx: float,
    cy: float,
    cw: float,
    ch: float,
) -> None:
    """Render and composite a content clip into a defined area.

    Args:
        cr: Cairo context.
        content_clip: Clip to render as content, or None.
        ctx: Current render context.
        cx: Content area x.
        cy: Content area y.
        cw: Content area width.
        ch: Content area height.
    """
    if content_clip is None or cw <= 0 or ch <= 0:
        # Fill with dark gray placeholder
        cr.set_source_rgba(0.15, 0.15, 0.2, 1.0)
        cr.rectangle(cx, cy, cw, ch)
        cr.fill()
        return

    from pymotion.clip.base import Resolution, TimeRange

    content_ctx = RenderContext(
        frame=ctx.frame,
        fps=ctx.fps,
        resolution=Resolution(max(2, int(cw) + (int(cw) % 2)), max(2, int(ch) + (int(ch) % 2))),
        time_range=TimeRange(ctx.time_range.start, ctx.time_range.end),
        local_frame=ctx.local_frame,
        progress=ctx.progress,
    )

    content_frame = content_clip.render_frame(content_ctx)

    # Scale content to fit the area
    fh, fw = content_frame.shape[:2]
    if fw != int(cw) or fh != int(ch):
        # Simple nearest-neighbor resize via numpy
        target_h = int(ch)
        target_w = int(cw)
        row_idx = (np.arange(target_h) * fh / target_h).astype(np.intp)
        col_idx = (np.arange(target_w) * fw / target_w).astype(np.intp)
        content_frame = content_frame[row_idx][:, col_idx]

    # Create a temporary surface from the content frame
    content_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(cw), int(ch))
    content_buf = content_surface.get_data()
    np.ndarray(
        shape=(int(ch), int(cw), 4),
        dtype=np.uint8,
        buffer=content_buf,
    )[:] = content_frame[: int(ch), : int(cw)]
    content_surface.mark_dirty()

    cr.set_source_surface(content_surface, cx, cy)
    cr.rectangle(cx, cy, cw, ch)
    cr.fill()


# Browser chrome colors
_BROWSER_THEMES = {
    "light": {
        "chrome": Color.parse("#F3F4F6"),
        "tab_bg": Color(1.0, 1.0, 1.0, 1.0),
        "text": Color.parse("#374151"),
        "url_bg": Color(1.0, 1.0, 1.0, 1.0),
        "border": Color.parse("#D1D5DB"),
    },
    "dark": {
        "chrome": Color.parse("#1F2937"),
        "tab_bg": Color.parse("#374151"),
        "text": Color.parse("#D1D5DB"),
        "url_bg": Color.parse("#111827"),
        "border": Color.parse("#4B5563"),
    },
}


@dataclass
class BrowserMockup(Clip):
    """Browser chrome frame around a content clip.

    Renders browser window UI (title bar, traffic lights, URL bar)
    around the content clip's output.

    Args:
        content_clip: The clip to display inside the browser window.
        mockup_theme: Browser theme ("light" or "dark").
        url_text: Text displayed in the URL bar.
        animate_in_frames: Frames for the enter animation (0 = none).
        animate_out_frames: Frames for the exit animation (0 = none).
        corner_radius: Corner radius of the browser window.
    """

    content_clip: Clip | None = None
    mockup_theme: str = "light"
    url_text: str = "https://example.com"
    animate_in_frames: int = 0
    animate_out_frames: int = 0
    corner_radius: float = 12.0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a browser mockup frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        theme_key = self.mockup_theme if self.mockup_theme in _BROWSER_THEMES else "light"
        t = _BROWSER_THEMES[theme_key]

        # Animation
        scale, opacity = self._compute_animation(ctx)
        if scale < 0.01:
            return _surface_to_frame(surface, h, w)

        cr.save()
        cr.translate(w / 2, h / 2)
        cr.scale(scale, scale)
        cr.translate(-w / 2, -h / 2)

        margin = 40.0
        bx, by = margin, margin
        bw, bh = w - margin * 2, h - margin * 2
        chrome_h = 60.0
        r = self.corner_radius

        # Window background
        _rounded_rect(cr, bx, by, bw, bh, r)
        cr.set_source_rgba(t["chrome"].r, t["chrome"].g, t["chrome"].b, opacity)
        cr.fill()

        # Traffic lights
        for i, color_hex in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
            c = Color.parse(color_hex)
            cx_dot = bx + 20 + i * 22
            cy_dot = by + chrome_h / 2
            cr.set_source_rgba(c.r, c.g, c.b, opacity)
            cr.arc(cx_dot, cy_dot, 7, 0, 2 * math.pi)
            cr.fill()

        # URL bar
        url_x = bx + 90
        url_y = by + chrome_h / 2 - 14
        url_w = bw - 130
        url_h = 28.0
        _rounded_rect(cr, url_x, url_y, url_w, url_h, 6)
        cr.set_source_rgba(t["url_bg"].r, t["url_bg"].g, t["url_bg"].b, opacity)
        cr.fill()

        # URL text
        cr.set_source_rgba(t["text"].r, t["text"].g, t["text"].b, opacity * 0.7)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(12)
        cr.move_to(url_x + 10, url_y + 18)
        cr.show_text(self.url_text)

        # Content area
        content_y = by + chrome_h
        content_h = bh - chrome_h
        _composite_content(cr, self.content_clip, ctx, bx, content_y, bw, content_h)

        # Bottom rounded corners (clip)
        cr.set_source_rgba(0, 0, 0, 0)

        cr.restore()

        return _surface_to_frame(surface, h, w)

    def _compute_animation(self, ctx: RenderContext) -> tuple[float, float]:
        """Compute scale and opacity for enter/exit animations.

        Args:
            ctx: Current render context.

        Returns:
            Tuple of (scale, opacity).
        """
        dur = self.duration if self.duration > 0 else 1
        scale = 1.0
        opacity = 1.0

        if self.animate_in_frames > 0 and ctx.local_frame < self.animate_in_frames:
            t = _ease_out_cubic(ctx.local_frame / self.animate_in_frames)
            scale = 0.8 + 0.2 * t
            opacity = t
        if self.animate_out_frames > 0 and ctx.local_frame > dur - self.animate_out_frames:
            remaining = dur - ctx.local_frame
            t = _ease_out_cubic(remaining / max(1, self.animate_out_frames))
            scale = 0.8 + 0.2 * t
            opacity = t

        return scale, opacity


# ── Phone Mockup ────────────────────────────────────────────────────────

_PHONE_MODELS = frozenset({"flat", "notch", "dynamic_island"})


@dataclass
class PhoneMockup(Clip):
    """Phone bezel frame around a content clip.

    Args:
        content_clip: The clip to display inside the phone screen.
        model: Phone model style ("flat", "notch", "dynamic_island").
        bezel_color: Color of the phone bezel.
        animate_in_frames: Frames for enter animation.
        animate_out_frames: Frames for exit animation.
    """

    content_clip: Clip | None = None
    model: str = "flat"
    bezel_color: Color = field(default_factory=lambda: Color.parse("#1F2937"))
    animate_in_frames: int = 0
    animate_out_frames: int = 0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a phone mockup frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        scale, opacity = self._compute_animation(ctx)
        if scale < 0.01:
            return _surface_to_frame(surface, h, w)

        cr.save()
        cr.translate(w / 2, h / 2)
        cr.scale(scale, scale)
        cr.translate(-w / 2, -h / 2)

        # Phone dimensions (9:19.5 aspect ratio, centered)
        phone_w = min(w * 0.4, h * 0.4 * (9.0 / 19.5))
        phone_h = phone_w * (19.5 / 9.0)
        px = (w - phone_w) / 2
        py = (h - phone_h) / 2
        bezel = phone_w * 0.04
        corner_r = phone_w * 0.12

        # Bezel
        bc = self.bezel_color
        _rounded_rect(cr, px, py, phone_w, phone_h, corner_r)
        cr.set_source_rgba(bc.r, bc.g, bc.b, opacity)
        cr.fill()

        # Screen area
        sx = px + bezel
        sy = py + bezel
        sw = phone_w - bezel * 2
        sh = phone_h - bezel * 2
        screen_r = corner_r - bezel

        _rounded_rect(cr, sx, sy, sw, sh, max(1, screen_r))
        cr.clip()
        _composite_content(cr, self.content_clip, ctx, sx, sy, sw, sh)
        cr.reset_clip()

        # Notch or dynamic island
        if self.model == "notch":
            notch_w = phone_w * 0.45
            notch_h = phone_h * 0.035
            notch_x = px + (phone_w - notch_w) / 2
            notch_y = py
            _rounded_rect(cr, notch_x, notch_y, notch_w, notch_h, notch_h / 2)
            cr.set_source_rgba(bc.r, bc.g, bc.b, opacity)
            cr.fill()
        elif self.model == "dynamic_island":
            di_w = phone_w * 0.3
            di_h = phone_h * 0.02
            di_x = px + (phone_w - di_w) / 2
            di_y = py + bezel + phone_h * 0.01
            _rounded_rect(cr, di_x, di_y, di_w, di_h, di_h / 2)
            cr.set_source_rgba(0, 0, 0, opacity)
            cr.fill()

        cr.restore()

        return _surface_to_frame(surface, h, w)

    def _compute_animation(self, ctx: RenderContext) -> tuple[float, float]:
        """Compute scale and opacity for enter/exit animations.

        Args:
            ctx: Current render context.

        Returns:
            Tuple of (scale, opacity).
        """
        dur = self.duration if self.duration > 0 else 1
        scale = 1.0
        opacity = 1.0

        if self.animate_in_frames > 0 and ctx.local_frame < self.animate_in_frames:
            t = _ease_out_cubic(ctx.local_frame / self.animate_in_frames)
            scale = 0.8 + 0.2 * t
            opacity = t
        if self.animate_out_frames > 0 and ctx.local_frame > dur - self.animate_out_frames:
            remaining = dur - ctx.local_frame
            t = _ease_out_cubic(remaining / max(1, self.animate_out_frames))
            scale = 0.8 + 0.2 * t
            opacity = t

        return scale, opacity


# ── Desktop Mockup ──────────────────────────────────────────────────────

_DESKTOP_THEMES = {
    "macos": {
        "titlebar": Color.parse("#E8E8E8"),
        "border": Color.parse("#CCCCCC"),
        "text": Color.parse("#333333"),
        "shadow": True,
    },
    "windows": {
        "titlebar": Color.parse("#FFFFFF"),
        "border": Color.parse("#CCCCCC"),
        "text": Color.parse("#333333"),
        "shadow": True,
    },
    "minimal": {
        "titlebar": Color.parse("#1F2937"),
        "border": Color.parse("#374151"),
        "text": Color.parse("#D1D5DB"),
        "shadow": False,
    },
}


@dataclass
class DesktopMockup(Clip):
    """Desktop window frame around a content clip.

    Args:
        content_clip: The clip to display inside the desktop window.
        os_theme: Desktop theme ("macos", "windows", "minimal").
        window_title: Title text in the title bar.
        animate_in_frames: Frames for enter animation.
        animate_out_frames: Frames for exit animation.
    """

    content_clip: Clip | None = None
    os_theme: str = "macos"
    window_title: str = "Window"
    animate_in_frames: int = 0
    animate_out_frames: int = 0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a desktop mockup frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        theme_key = self.os_theme if self.os_theme in _DESKTOP_THEMES else "macos"
        t = _DESKTOP_THEMES[theme_key]

        scale, opacity = self._compute_animation(ctx)
        if scale < 0.01:
            return _surface_to_frame(surface, h, w)

        cr.save()
        cr.translate(w / 2, h / 2)
        cr.scale(scale, scale)
        cr.translate(-w / 2, -h / 2)

        margin = 60.0
        bx, by = margin, margin
        bw, bh = w - margin * 2, h - margin * 2
        titlebar_h = 36.0
        r = 8.0

        # Shadow
        if t["shadow"]:
            cr.set_source_rgba(0, 0, 0, 0.15 * opacity)
            _rounded_rect(cr, bx + 4, by + 4, bw, bh, r)
            cr.fill()

        # Window frame
        _rounded_rect(cr, bx, by, bw, bh, r)
        titlebar_color: Color = t["titlebar"]  # type: ignore[assignment]
        cr.set_source_rgba(titlebar_color.r, titlebar_color.g, titlebar_color.b, opacity)
        cr.fill()

        # Title bar
        if self.os_theme == "macos":
            # Traffic lights
            for i, color_hex in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
                c = Color.parse(color_hex)
                cx_dot = bx + 16 + i * 22
                cy_dot = by + titlebar_h / 2
                cr.set_source_rgba(c.r, c.g, c.b, opacity)
                cr.arc(cx_dot, cy_dot, 6, 0, 2 * math.pi)
                cr.fill()
        elif self.os_theme == "windows":
            # Minimize, maximize, close boxes on right
            btn_size = 12
            for i, color_hex in enumerate(["#888888", "#888888", "#FF5F57"]):
                c = Color.parse(color_hex)
                cx_btn = bx + bw - 20 - i * 30
                cy_btn = by + titlebar_h / 2 - btn_size / 2
                cr.set_source_rgba(c.r, c.g, c.b, opacity)
                cr.rectangle(cx_btn, cy_btn, btn_size, btn_size)
                cr.fill()

        # Window title
        text_color: Color = t["text"]  # type: ignore[assignment]
        cr.set_source_rgba(text_color.r, text_color.g, text_color.b, opacity)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(13)
        ext = cr.text_extents(self.window_title)
        cr.move_to(bx + bw / 2 - ext.width / 2, by + titlebar_h / 2 + ext.height / 2)
        cr.show_text(self.window_title)

        # Border line under titlebar
        border_color: Color = t["border"]  # type: ignore[assignment]
        cr.set_source_rgba(border_color.r, border_color.g, border_color.b, opacity)
        cr.set_line_width(1)
        cr.move_to(bx, by + titlebar_h)
        cr.line_to(bx + bw, by + titlebar_h)
        cr.stroke()

        # Content area
        content_y = by + titlebar_h
        content_h = bh - titlebar_h
        _composite_content(cr, self.content_clip, ctx, bx, content_y, bw, content_h)

        cr.restore()

        return _surface_to_frame(surface, h, w)

    def _compute_animation(self, ctx: RenderContext) -> tuple[float, float]:
        """Compute scale and opacity for enter/exit animations.

        Args:
            ctx: Current render context.

        Returns:
            Tuple of (scale, opacity).
        """
        dur = self.duration if self.duration > 0 else 1
        scale = 1.0
        opacity = 1.0

        if self.animate_in_frames > 0 and ctx.local_frame < self.animate_in_frames:
            t = _ease_out_cubic(ctx.local_frame / self.animate_in_frames)
            scale = 0.8 + 0.2 * t
            opacity = t
        if self.animate_out_frames > 0 and ctx.local_frame > dur - self.animate_out_frames:
            remaining = dur - ctx.local_frame
            t = _ease_out_cubic(remaining / max(1, self.animate_out_frames))
            scale = 0.8 + 0.2 * t
            opacity = t

        return scale, opacity
