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
from pymotion.design.renderer import (
    draw_pill,
    draw_rounded_rect,
    draw_shadow_surface,
    set_text_rendering,
)
from pymotion.design.tokens import (
    NEUTRAL,
)
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
    mockup_theme: str = "dark"
    url_text: str = "https://example.com"
    animate_in_frames: int = 0
    animate_out_frames: int = 0
    corner_radius: float = 12.0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a browser mockup frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Z-order (bottom to top):
        #   1. Shadow: blurred rect, radius 24*scale, offset (0, 12*scale), rgba(0,0,0,0.4)
        #   2. Container: rounded rect, radius 12*scale
        #   3. Chrome bar: 40*scale high, neutral_900, border_bottom neutral_700
        #      Traffic lights: 12*scale diameter, 8*scale gap, macOS colors
        #      URL bar: centered, 280*scale wide, 24*scale high, neutral_800
        #        Lock icon + "yourwebsite.com" in JetBrains Mono 11*scale
        #   4. Content area: neutral_950 bg, content clip composited
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

        anim_scale, opacity = self._compute_animation(ctx)
        if anim_scale < 0.01:
            return _surface_to_frame(surface, h, w)

        cr.save()
        cr.translate(w / 2.0, h / 2.0)
        cr.scale(anim_scale, anim_scale)
        cr.translate(-w / 2.0, -h / 2.0)

        margin = 40.0 * scale
        bx, by = margin, margin
        bw = w - margin * 2
        bh = h - margin * 2
        chrome_h = 40.0 * scale
        r = 12.0 * scale

        n900 = NEUTRAL.n900
        n800 = NEUTRAL.n800
        n700 = NEUTRAL.n700
        n500 = NEUTRAL.n500
        n950 = NEUTRAL.n950

        # LAYER 1: Shadow
        shadow_color = Color(0.0, 0.0, 0.0, 0.40 * opacity)
        draw_shadow_surface(cr, bx, by, bw, bh, r, 24.0 * scale, 12.0 * scale, shadow_color)

        # LAYER 2: Container background
        draw_rounded_rect(cr, bx, by, bw, bh, r)
        cr.set_source_rgba(n900.r, n900.g, n900.b, opacity)
        cr.fill()

        # LAYER 3: Chrome bar
        # Traffic lights
        dot_r = 6.0 * scale
        for i, color_hex in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
            c = Color.parse(color_hex)
            cx_dot = bx + 16.0 * scale + i * (dot_r * 2 + 8.0 * scale)
            cy_dot = by + chrome_h / 2.0
            cr.set_source_rgba(c.r, c.g, c.b, opacity)
            cr.arc(cx_dot, cy_dot, dot_r, 0, 2 * math.pi)
            cr.fill()

        # URL bar (centered)
        url_w = 280.0 * scale
        url_h = 24.0 * scale
        url_x = bx + (bw - url_w) / 2.0
        url_y = by + (chrome_h - url_h) / 2.0
        draw_rounded_rect(cr, url_x, url_y, url_w, url_h, 6.0 * scale)
        cr.set_source_rgba(n800.r, n800.g, n800.b, opacity)
        cr.fill()

        # Lock icon (simple padlock shape)
        lock_x = url_x + 8.0 * scale
        lock_cy = url_y + url_h / 2.0
        lock_size = 8.0 * scale
        cr.set_source_rgba(n500.r, n500.g, n500.b, opacity)
        # Lock body (small rect)
        cr.rectangle(lock_x, lock_cy - lock_size * 0.15, lock_size * 0.7, lock_size * 0.55)
        cr.fill()
        # Lock shackle (arc above body)
        cr.set_line_width(1.5 * scale)
        cr.arc(lock_x + lock_size * 0.35, lock_cy - lock_size * 0.15, lock_size * 0.25, math.pi, 0)
        cr.stroke()

        # URL text
        url_text = "yourwebsite.com"
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11.0 * scale)
        cr.set_source_rgba(n500.r, n500.g, n500.b, opacity)
        cr.move_to(lock_x + lock_size + 4.0 * scale, url_y + url_h / 2.0 + 4.0 * scale)
        cr.show_text(url_text)

        # Chrome border bottom
        cr.set_source_rgba(n700.r, n700.g, n700.b, opacity)
        cr.set_line_width(1.0 * scale)
        cr.move_to(bx, by + chrome_h)
        cr.line_to(bx + bw, by + chrome_h)
        cr.stroke()

        # LAYER 4: Content area
        content_y = by + chrome_h
        content_h = bh - chrome_h
        # Fill with neutral_950 behind content
        cr.set_source_rgba(n950.r, n950.g, n950.b, opacity)
        cr.rectangle(bx, content_y, bw, content_h)
        cr.fill()
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
    bezel_color: Color = field(default_factory=lambda: NEUTRAL.n900)
    animate_in_frames: int = 0
    animate_out_frames: int = 0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a phone mockup frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Z-order:
        #   1. Shadow: shadow_xl beneath device body
        #   2. Device body: neutral_900, border neutral_700 1.5*scale
        #      border_radius: comp_height*0.055
        #   3. Screen area: inset 4*scale, neutral_950 bg
        #   4. Status bar: 28*scale, "9:41" left, icons right
        #   5. Content clip: between status bar and home indicator
        #   6. Home indicator: 120*scale wide, 5*scale tall, neutral_500
        #   7. Notch/dynamic island if model requires
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

        anim_scale, opacity = self._compute_animation(ctx)
        if anim_scale < 0.01:
            return _surface_to_frame(surface, h, w)

        cr.save()
        cr.translate(w / 2.0, h / 2.0)
        cr.scale(anim_scale, anim_scale)
        cr.translate(-w / 2.0, -h / 2.0)

        # Compute phone size (9:19.5 aspect, fit within frame)
        phone_w = min(w * 0.4, h * 0.4 * (9.0 / 19.5))
        phone_h = phone_w * (19.5 / 9.0)
        px = (w - phone_w) / 2.0
        py = (h - phone_h) / 2.0
        corner_r = h * 0.055
        inset = 4.0 * scale

        n900 = NEUTRAL.n900
        n700 = NEUTRAL.n700
        n950 = NEUTRAL.n950
        n500 = NEUTRAL.n500
        n100 = NEUTRAL.n100
        n400 = NEUTRAL.n400
        bc = self.bezel_color

        # LAYER 1: Shadow
        shadow_color = Color(0.0, 0.0, 0.0, 0.45 * opacity)
        draw_shadow_surface(
            cr,
            px,
            py,
            phone_w,
            phone_h,
            corner_r,
            40.0 * scale,
            20.0 * scale,
            shadow_color,
        )

        # LAYER 2: Device body
        _rounded_rect(cr, px, py, phone_w, phone_h, corner_r)
        cr.set_source_rgba(bc.r, bc.g, bc.b, opacity)
        cr.fill()

        # Border
        _rounded_rect(cr, px, py, phone_w, phone_h, corner_r)
        cr.set_source_rgba(n700.r, n700.g, n700.b, opacity)
        cr.set_line_width(1.5 * scale)
        cr.stroke()

        # LAYER 3: Screen area
        sx = px + inset
        sy = py + inset
        sw = phone_w - inset * 2
        sh_screen = phone_h - inset * 2
        screen_r = max(1.0, corner_r - inset)

        _rounded_rect(cr, sx, sy, sw, sh_screen, screen_r)
        cr.set_source_rgba(n950.r, n950.g, n950.b, opacity)
        cr.fill()

        # LAYER 4: Status bar
        status_h = 28.0 * scale
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(11.0 * scale)
        cr.set_source_rgba(n100.r, n100.g, n100.b, opacity)
        cr.move_to(sx + 20.0 * scale, sy + status_h / 2.0 + 4.0 * scale)
        cr.show_text("9:41")

        # Right side: simple battery/signal icons as shapes
        icon_x = sx + sw - 20.0 * scale
        icon_cy = sy + status_h / 2.0
        cr.set_source_rgba(n400.r, n400.g, n400.b, opacity)
        # Battery (small rect)
        bat_w = 18.0 * scale
        bat_h = 9.0 * scale
        cr.rectangle(icon_x - bat_w, icon_cy - bat_h / 2.0, bat_w, bat_h)
        cr.stroke()
        cr.rectangle(icon_x, icon_cy - 2.0 * scale, 2.0 * scale, 4.0 * scale)
        cr.fill()

        # LAYER 5: Content clip
        content_y = sy + status_h
        content_h = sh_screen - status_h - 40.0 * scale  # leave room for home indicator
        _rounded_rect(cr, sx, content_y, sw, content_h, 0)
        cr.clip()
        _composite_content(cr, self.content_clip, ctx, sx, content_y, sw, content_h)
        cr.reset_clip()

        # LAYER 6: Home indicator
        hi_w = 120.0 * scale
        hi_h = 5.0 * scale
        hi_x = sx + (sw - hi_w) / 2.0
        hi_y = sy + sh_screen - 20.0 * scale
        draw_pill(cr, hi_x, hi_y, hi_w, hi_h, None)
        cr.set_source_rgba(n500.r, n500.g, n500.b, opacity)
        cr.fill()

        # LAYER 7: Notch/Dynamic Island
        if self.model == "notch":
            notch_w = 120.0 * scale
            notch_h = 28.0 * scale
            notch_x = px + (phone_w - notch_w) / 2.0
            notch_y = py
            draw_pill(cr, notch_x, notch_y, notch_w, notch_h, None)
            cr.set_source_rgba(n950.r, n950.g, n950.b, opacity)
            cr.fill()
        elif self.model == "dynamic_island":
            di_w = 120.0 * scale
            di_h = 36.0 * scale
            di_x = px + (phone_w - di_w) / 2.0
            di_y = sy + 6.0 * scale
            draw_pill(cr, di_x, di_y, di_w, di_h, None)
            cr.set_source_rgba(n900.r, n900.g, n900.b, opacity)
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
        "titlebar": NEUTRAL.n900,
        "border": NEUTRAL.n700,
        "text": NEUTRAL.n100,
        "shadow": True,
    },
    "windows": {
        "titlebar": NEUTRAL.n900,
        "border": NEUTRAL.n700,
        "text": NEUTRAL.n100,
        "shadow": True,
    },
    "minimal": {
        "titlebar": NEUTRAL.n900,
        "border": NEUTRAL.n700,
        "text": NEUTRAL.n300,
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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Z-order (bottom to top):
        #   1. Shadow: shadow_xl via draw_shadow_surface (macos/windows only)
        #   2. Container: rounded rect, radius 12*scale, neutral_900
        #   3. Title bar: 36*scale high, neutral_900, border_bottom neutral_700
        #      macOS: traffic lights 6*scale radius, 22*scale spacing
        #      windows: minimize/maximize/close boxes on right
        #      minimal: no controls
        #      Centered window title: Inter 13*scale, neutral_100
        #   4. Content area: neutral_950 bg, content clip composited
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

        theme_key = self.os_theme if self.os_theme in _DESKTOP_THEMES else "macos"
        t = _DESKTOP_THEMES[theme_key]

        anim_scale, opacity = self._compute_animation(ctx)
        if anim_scale < 0.01:
            return _surface_to_frame(surface, h, w)

        cr.save()
        cr.translate(w / 2.0, h / 2.0)
        cr.scale(anim_scale, anim_scale)
        cr.translate(-w / 2.0, -h / 2.0)

        margin = 60.0 * scale
        bx, by = margin, margin
        bw = w - margin * 2
        bh = h - margin * 2
        titlebar_h = 36.0 * scale
        r = 12.0 * scale

        n900 = NEUTRAL.n900
        n950 = NEUTRAL.n950

        # LAYER 1: Shadow
        if t["shadow"]:
            shadow_color = Color(0.0, 0.0, 0.0, 0.45 * opacity)
            draw_shadow_surface(cr, bx, by, bw, bh, r, 40.0 * scale, 20.0 * scale, shadow_color)

        # LAYER 2: Container background
        draw_rounded_rect(cr, bx, by, bw, bh, r)
        cr.set_source_rgba(n900.r, n900.g, n900.b, opacity)
        cr.fill()

        # LAYER 3: Title bar controls
        dot_r = 6.0 * scale
        if self.os_theme == "macos":
            for i, color_hex in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
                c = Color.parse(color_hex)
                cx_dot = bx + 16.0 * scale + i * 22.0 * scale
                cy_dot = by + titlebar_h / 2.0
                cr.set_source_rgba(c.r, c.g, c.b, opacity)
                cr.arc(cx_dot, cy_dot, dot_r, 0, 2 * math.pi)
                cr.fill()
        elif self.os_theme == "windows":
            btn_size = 12.0 * scale
            for i, color_hex in enumerate(["#888888", "#888888", "#FF5F57"]):
                c = Color.parse(color_hex)
                cx_btn = bx + bw - 20.0 * scale - i * 30.0 * scale
                cy_btn = by + titlebar_h / 2.0 - btn_size / 2.0
                cr.set_source_rgba(c.r, c.g, c.b, opacity)
                cr.rectangle(cx_btn, cy_btn, btn_size, btn_size)
                cr.fill()

        # Window title (centered)
        text_color: Color = t["text"]  # type: ignore[assignment]
        cr.set_source_rgba(text_color.r, text_color.g, text_color.b, opacity)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(13.0 * scale)
        ext = cr.text_extents(self.window_title)
        cr.move_to(bx + bw / 2.0 - ext.width / 2.0, by + titlebar_h / 2.0 + ext.height / 2.0)
        cr.show_text(self.window_title)

        # Border line under titlebar
        border_color: Color = t["border"]  # type: ignore[assignment]
        cr.set_source_rgba(border_color.r, border_color.g, border_color.b, opacity)
        cr.set_line_width(1.0 * scale)
        cr.move_to(bx, by + titlebar_h)
        cr.line_to(bx + bw, by + titlebar_h)
        cr.stroke()

        # LAYER 4: Content area
        content_y = by + titlebar_h
        content_h = bh - titlebar_h
        cr.set_source_rgba(n950.r, n950.g, n950.b, opacity)
        cr.rectangle(bx, content_y, bw, content_h)
        cr.fill()
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
