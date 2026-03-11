"""Motion graphics components — reusable animated overlay clips.

Provides LowerThird, LogoReveal, CallToAction, SocialHandle, Countdown,
QuoteCard, Divider, TransitionTitle, and Watermark clip types for common
video production elements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cairo
import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.design.motion import ease_in_out_quart, ease_in_quart, ease_out_quart
from pymotion.design.renderer import draw_rounded_rect
from pymotion.design.tokens import (
    BODY,
    BODY_SM,
    DISPLAY_LG,
    DISPLAY_SM,
    HEADING,
    LABEL,
    RADIUS_FULL,
    RADIUS_MD,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    get_theme,
    safe_h,
    safe_v,
    scale_size,
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


def _ease_in_cubic(t: float) -> float:
    """Cubic ease-in."""
    return t**3


def _clamp01(v: float) -> float:
    """Clamp value to [0, 1]."""
    return max(0.0, min(1.0, v))


# ── Lower Third Styles ─────────────────────────────────────────────────

_LOWER_THIRD_STYLES: dict[str, dict[str, Color]] = {
    "modern": {
        "bg": Color.parse("#1A1A2E"),
        "accent": Color.parse("#E94560"),
        "name_color": Color(1.0, 1.0, 1.0, 1.0),
        "title_color": Color(0.8, 0.8, 0.8, 1.0),
    },
    "clean": {
        "bg": Color(1.0, 1.0, 1.0, 0.9),
        "accent": Color.parse("#2563EB"),
        "name_color": Color.parse("#111827"),
        "title_color": Color.parse("#6B7280"),
    },
    "bold": {
        "bg": Color.parse("#E94560"),
        "accent": Color(1.0, 1.0, 1.0, 1.0),
        "name_color": Color(1.0, 1.0, 1.0, 1.0),
        "title_color": Color(1.0, 1.0, 1.0, 0.8),
    },
    "minimal": {
        "bg": Color(0.0, 0.0, 0.0, 0.0),
        "accent": Color(1.0, 1.0, 1.0, 1.0),
        "name_color": Color(1.0, 1.0, 1.0, 1.0),
        "title_color": Color(0.8, 0.8, 0.8, 1.0),
    },
    "news": {
        "bg": Color.parse("#B91C1C"),
        "accent": Color(1.0, 1.0, 1.0, 1.0),
        "name_color": Color(1.0, 1.0, 1.0, 1.0),
        "title_color": Color(1.0, 1.0, 1.0, 0.9),
    },
    "gradient_bar": {
        "bg": Color.parse("#0F3460"),
        "accent": Color.parse("#E94560"),
        "name_color": Color(1.0, 1.0, 1.0, 1.0),
        "title_color": Color(0.9, 0.9, 0.9, 1.0),
    },
    "corporate": {
        "bg": Color.parse("#1E293B"),
        "accent": Color.parse("#3B82F6"),
        "name_color": Color(1.0, 1.0, 1.0, 1.0),
        "title_color": Color(0.8, 0.8, 0.9, 1.0),
    },
    "neon": {
        "bg": Color(0.0, 0.0, 0.0, 0.85),
        "accent": Color.parse("#00FF87"),
        "name_color": Color.parse("#00FF87"),
        "title_color": Color.parse("#00D4FF"),
    },
}


@dataclass
class LowerThird(Clip):
    """Animated lower third overlay — name and title with slide-in/out.

    Provides 8+ design styles with smooth enter and exit animations.
    The overlay is positioned in the lower portion of the frame.

    Args:
        name: Primary name text.
        title: Secondary title/role text.
        style: Design style name (modern, clean, bold, minimal, news,
            gradient_bar, corporate, neon).
        animate_in: Frames for enter animation.
        animate_out: Frames for exit animation.
        margin_bottom: Pixels from the bottom of the frame.
        margin_left: Pixels from the left edge.
    """

    name: str = ""
    title: str = ""
    style: str = "modern"
    animate_in: int = 15
    animate_out: int = 15
    margin_bottom: float = 80.0
    margin_left: float = 60.0
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def _render_modern(
        self,
        cr: cairo.Context[cairo.ImageSurface],
        w: int,
        h: int,
        progress: float,
    ) -> None:
        """Render the modern/default lower third using design tokens.

        # DESIGN INTENT: Modern broadcast chyron — pill-shaped name chip
        #   beside a thin vertical accent bar and a title line.
        # REFERENCE: Bloomberg TV lower thirds, Apple keynote speaker IDs.
        """
        t = get_theme()

        # Scaled sizes from token system
        name_size = scale_size(LABEL.size, h)
        title_size = scale_size(BODY.size, h)
        pad_x = scale_size(SPACE_2, h)
        pad_y = scale_size(SPACE_1, h)
        accent_w = 3.0 * (h / 1080)
        gap = 6.0 * (h / 1080)
        sh = safe_h(w)
        sv = safe_v(h)

        # Measure text
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(name_size)
        name_ext = cr.text_extents(self.name.upper())
        cr.set_font_size(title_size)
        _ = cr.text_extents(self.title)

        # Chip dimensions
        chip_w = accent_w + pad_x + name_ext.width + pad_x
        chip_h = pad_y * 2 + name_size

        # Position: safe zone from left/bottom
        bx = sh + (1.0 - progress) * -24 * (w / 1920)
        chip_y = h - sv - chip_h - title_size - gap

        # Chip background (pill shape)
        draw_rounded_rect(cr, bx, chip_y, chip_w, chip_h, RADIUS_FULL)
        cr.set_source_rgba(t.surface.r, t.surface.g, t.surface.b, 0.95 * progress)
        cr.fill()

        # Accent bar on left edge of chip
        cr.set_source_rgba(t.accent.r, t.accent.g, t.accent.b, progress)
        draw_rounded_rect(cr, bx, chip_y, accent_w, chip_h, accent_w / 2)
        cr.fill()

        # Name text (ALL CAPS, label style)
        cr.set_source_rgba(t.text.r, t.text.g, t.text.b, progress)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(name_size)
        cr.move_to(bx + accent_w + pad_x, chip_y + pad_y + name_size * 0.85)
        cr.show_text(self.name.upper())

        # Title line below chip
        title_y = chip_y + chip_h + gap
        title_progress = _clamp01((progress - 0.4) / 0.6) if progress < 1.0 else 1.0
        cr.set_source_rgba(t.muted.r, t.muted.g, t.muted.b, title_progress)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(title_size)
        cr.move_to(bx + accent_w + pad_x, title_y + title_size * 0.85)
        cr.show_text(self.title)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a lower third frame with slide animation.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        if self.style not in _LOWER_THIRD_STYLES:
            valid = ", ".join(sorted(_LOWER_THIRD_STYLES))
            msg = f"Unknown lower third style '{self.style}'. Valid: {valid}"
            raise ValueError(msg)

        # Animation with design-system easing
        dur = self.duration if self.duration > 0 else 1
        progress = 1.0
        if ctx.local_frame < self.animate_in:
            progress = ease_out_quart(ctx.local_frame / max(1, self.animate_in))
        elif ctx.local_frame > dur - self.animate_out:
            remaining = dur - ctx.local_frame
            progress = ease_in_quart(remaining / max(1, self.animate_out))

        # Return cached static frame when not animating
        if progress == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        # Use design-system rendering for modern style
        if self.style == "modern":
            self._render_modern(cr, w, h, progress)
            result = _surface_to_frame(surface, h, w)
            if progress == 1.0:
                self._static_cache = result.copy()
            return result

        # Legacy style rendering
        s = _LOWER_THIRD_STYLES[self.style]
        bg = s["bg"]
        accent = s["accent"]
        name_color = s["name_color"]
        title_color = s["title_color"]

        # Slide from left
        slide_offset = (1.0 - progress) * -300

        # Dimensions
        name_size = max(18.0, min(32.0, h * 0.04))
        title_size = max(12.0, min(22.0, h * 0.028))
        pad_x = 20.0
        pad_y = 12.0
        accent_w = 5.0

        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(name_size)
        name_ext = cr.text_extents(self.name)
        cr.set_font_size(title_size)
        title_ext = cr.text_extents(self.title)

        box_w = max(name_ext.width, title_ext.width) + pad_x * 2 + accent_w
        box_h = name_size + title_size + pad_y * 3

        bx = self.margin_left + slide_offset
        by = h - self.margin_bottom - box_h

        # Background
        cr.set_source_rgba(bg.r, bg.g, bg.b, bg.a * progress)
        cr.rectangle(bx, by, box_w, box_h)
        cr.fill()

        # Accent bar
        cr.set_source_rgba(accent.r, accent.g, accent.b, accent.a * progress)
        cr.rectangle(bx, by, accent_w, box_h)
        cr.fill()

        # Name text
        cr.set_source_rgba(name_color.r, name_color.g, name_color.b, name_color.a * progress)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(name_size)
        cr.move_to(bx + accent_w + pad_x, by + pad_y + name_size)
        cr.show_text(self.name)

        # Title text
        cr.set_source_rgba(title_color.r, title_color.g, title_color.b, title_color.a * progress)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(title_size)
        cr.move_to(bx + accent_w + pad_x, by + pad_y + name_size + pad_y + title_size)
        cr.show_text(self.title)

        result = _surface_to_frame(surface, h, w)
        if progress == 1.0:
            self._static_cache = result.copy()
        return result


# ── LogoReveal ──────────────────────────────────────────────────────────

_LOGO_REVEAL_STYLES = frozenset({"fade", "slice", "grow", "glitch", "draw", "shatter"})


@dataclass
class LogoReveal(Clip):
    """Animated logo reveal — renders a colored rectangle as logo placeholder.

    Since PyMotion is a library, LogoReveal renders a configurable logo area
    with one of 6+ reveal animation styles. In production, the rendered image
    would be composited over this clip.

    Args:
        image: Path or placeholder color for the logo area.
        style: Reveal animation style (fade, slice, grow, glitch, draw, shatter).
        reveal_duration: Frames for the reveal animation.
        logo_color: Color of the logo placeholder.
        logo_size: (width, height) of the logo area.
    """

    image: str = ""
    style: str = "fade"
    reveal_duration: int = 30
    logo_color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0, 1.0))
    logo_size: tuple[float, float] = (200.0, 200.0)
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a logo reveal frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        if self.style not in _LOGO_REVEAL_STYLES:
            valid = ", ".join(sorted(_LOGO_REVEAL_STYLES))
            msg = f"Unknown logo reveal style '{self.style}'. Valid: {valid}"
            raise ValueError(msg)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # Animation progress — use design-system easing
        if self.reveal_duration > 0 and ctx.local_frame < self.reveal_duration:
            t = ease_out_quart(ctx.local_frame / self.reveal_duration)
        else:
            t = 1.0

        # Return cached static frame when reveal is complete
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        lw, lh = self.logo_size
        lx = (w - lw) / 2
        ly = (h - lh) / 2
        c = self.logo_color

        if self.style == "fade":
            # DESIGN INTENT: Clean fade with subtle scale for presence
            s_val = 0.95 + 0.05 * t
            cr.save()
            cr.translate(w / 2, h / 2)
            cr.scale(s_val, s_val)
            cr.translate(-w / 2, -h / 2)
            cr.set_source_rgba(c.r, c.g, c.b, c.a * t)
            cr.rectangle(lx, ly, lw, lh)
            cr.fill()
            cr.restore()
        elif self.style == "grow":
            s = max(t, 1e-6)
            cr.save()
            cr.translate(w / 2, h / 2)
            cr.scale(s, s)
            cr.translate(-w / 2, -h / 2)
            cr.set_source_rgba(c.r, c.g, c.b, c.a)
            cr.rectangle(lx, ly, lw, lh)
            cr.fill()
            cr.restore()
        elif self.style == "slice":
            # Horizontal slices reveal
            n_slices = 8
            for i in range(n_slices):
                slice_t = _clamp01((t - i / n_slices / 2) * 2)
                slice_h = lh / n_slices
                sy = ly + i * slice_h
                sw = lw * slice_t
                cr.set_source_rgba(c.r, c.g, c.b, c.a)
                cr.rectangle(lx, sy, sw, slice_h)
                cr.fill()
        elif self.style == "glitch":
            # Glitchy reveal with offset slices
            n_slices = 12
            for i in range(n_slices):
                slice_h = lh / n_slices
                sy = ly + i * slice_h
                offset = math.sin(i * 3.7 + ctx.local_frame * 0.5) * 20 * (1.0 - t)
                cr.set_source_rgba(c.r, c.g, c.b, c.a * min(1.0, t * 1.5))
                cr.rectangle(lx + offset, sy, lw, slice_h)
                cr.fill()
        elif self.style == "draw":
            # Border draws around the logo
            perimeter = 2 * (lw + lh)
            drawn = perimeter * t
            cr.set_source_rgba(c.r, c.g, c.b, c.a)
            cr.set_line_width(3.0)
            # Top edge
            seg = min(drawn, lw)
            cr.move_to(lx, ly)
            cr.line_to(lx + seg, ly)
            drawn -= seg
            if drawn > 0:
                seg = min(drawn, lh)
                cr.line_to(lx + lw, ly + seg)
                drawn -= seg
            if drawn > 0:
                seg = min(drawn, lw)
                cr.line_to(lx + lw - seg, ly + lh)
                drawn -= seg
            if drawn > 0:
                seg = min(drawn, lh)
                cr.line_to(lx, ly + lh - seg)
            cr.stroke()
            # Fill with lower opacity
            if t > 0.5:
                fill_t = (t - 0.5) * 2
                cr.set_source_rgba(c.r, c.g, c.b, c.a * fill_t * 0.8)
                cr.rectangle(lx, ly, lw, lh)
                cr.fill()
        elif self.style == "shatter":
            # Pieces assemble from scattered positions
            nx, ny = 4, 4
            pw = lw / nx
            ph = lh / ny
            for ix in range(nx):
                for iy in range(ny):
                    px = lx + ix * pw
                    py_base = ly + iy * ph
                    scatter = (1.0 - t) * 150
                    angle = (ix * 7 + iy * 13) * 0.5
                    ox = math.cos(angle) * scatter
                    oy = math.sin(angle) * scatter
                    cr.set_source_rgba(c.r, c.g, c.b, c.a * t)
                    cr.rectangle(px + ox, py_base + oy, pw, ph)
                    cr.fill()

        result = _surface_to_frame(surface, h, w)
        if t == 1.0:
            self._static_cache = result.copy()
        return result


# ── CallToAction ────────────────────────────────────────────────────────

_CTA_STYLES: dict[str, dict[str, Color]] = {
    "subscribe": {
        "bg": Color.parse("#FF0000"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "buy": {
        "bg": Color.parse("#10B981"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "visit": {
        "bg": Color.parse("#2563EB"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "default": {
        "bg": Color.parse("#6366F1"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
}


@dataclass
class CallToAction(Clip):
    """Animated call-to-action overlay.

    Renders a button-like CTA with text and optional sub-text,
    with a pop-in animation.

    Args:
        text: Primary CTA text (e.g. "Subscribe").
        sub_text: Optional secondary text below the primary.
        style: Visual style (subscribe, buy, visit, default).
        animate_in: Frames for the pop-in animation.
    """

    text: str = "Subscribe"
    sub_text: str = ""
    style: str = "default"
    animate_in: int = 15
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a call-to-action frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # DESIGN INTENT: Pill button with accent fill, like a UI CTA component.
        # REFERENCE: Linear app tooltips, Vercel dashboard prompts.

        # Animation with design-system easing
        if self.animate_in > 0 and ctx.local_frame < self.animate_in:
            t = ease_out_quart(ctx.local_frame / self.animate_in)
        else:
            t = 1.0

        # Return cached static frame when not animating
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        theme = get_theme()
        text_size = scale_size(HEADING.size, h)
        sub_size = scale_size(BODY.size, h)
        pad_x = scale_size(SPACE_2 * 2, h)
        pad_y = scale_size(SPACE_2, h)
        sv = safe_v(h)

        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(text_size)
        text_ext = cr.text_extents(self.text)

        box_w = text_ext.width + pad_x * 2
        box_h = text_size + pad_y * 2
        if self.sub_text:
            box_h += sub_size + 4 * (h / 1080)

        bx = (w - box_w) / 2
        by = h - sv - box_h  # Bottom-aligned in safe zone

        # Scale animation (0.92→1.0)
        cr.save()
        cr.translate(w / 2, by + box_h / 2)
        s_val = 0.92 + 0.08 * t
        cr.scale(s_val, s_val)
        cr.translate(-w / 2, -(by + box_h / 2))

        # Pill background with accent color
        draw_rounded_rect(cr, bx, by, box_w, box_h, RADIUS_FULL)
        cr.set_source_rgba(theme.accent.r, theme.accent.g, theme.accent.b, t)
        cr.fill()

        # White text on accent
        cr.set_source_rgba(1.0, 1.0, 1.0, t)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(text_size)
        cr.move_to(bx + pad_x, by + pad_y + text_size * 0.8)
        cr.show_text(self.text)

        if self.sub_text:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.7 * t)
            cr.set_font_size(sub_size)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.move_to(bx + pad_x, by + pad_y + text_size + sub_size)
            cr.show_text(self.sub_text)

        cr.restore()

        result = _surface_to_frame(surface, h, w)
        if t == 1.0:
            self._static_cache = result.copy()
        return result


# ── SocialHandle ────────────────────────────────────────────────────────

_SOCIAL_COLORS: dict[str, Color] = {
    "youtube": Color.parse("#FF0000"),
    "instagram": Color.parse("#E4405F"),
    "tiktok": Color(0.0, 0.0, 0.0, 1.0),
    "x": Color(0.0, 0.0, 0.0, 1.0),
    "linkedin": Color.parse("#0A66C2"),
}


@dataclass
class SocialHandle(Clip):
    """Platform-styled social media handle overlay.

    Args:
        platform: Social platform (youtube, instagram, tiktok, x, linkedin).
        handle: Username or handle text.
        style: Visual style (currently "default").
        animate_in: Frames for the slide-in animation.
    """

    platform: str = "youtube"
    handle: str = "@user"
    style: str = "default"
    animate_in: int = 15
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a social handle overlay frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        # DESIGN INTENT: Minimal chip — platform icon + handle text on
        #   frosted-glass-style dark surface.
        # REFERENCE: Figma community cards, Vercel deployment metadata.

        theme = get_theme()

        if self.animate_in > 0 and ctx.local_frame < self.animate_in:
            t = ease_out_quart(ctx.local_frame / self.animate_in)
        else:
            t = 1.0

        # Return cached static frame when not animating
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        text_size = scale_size(BODY.size, h)
        pad_x = scale_size(SPACE_2, h)
        pad_y = scale_size(SPACE_1, h)
        icon_size = 16.0 * (h / 1080)
        icon_gap = scale_size(SPACE_1, h)
        sh = safe_h(w)
        sv = safe_v(h)

        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(text_size)
        ext = cr.text_extents(self.handle)

        box_w = pad_x + icon_size + icon_gap + ext.width + pad_x
        box_h = pad_y * 2 + max(text_size, icon_size)
        bx = sh
        by = h - sv - box_h

        # Y-drift animation
        y_drift = (1.0 - t) * 8.0 * (h / 1080)

        # Background chip (frosted glass style)
        draw_rounded_rect(cr, bx, by + y_drift, box_w, box_h, RADIUS_MD)
        cr.set_source_rgba(theme.surface.r, theme.surface.g, theme.surface.b, 0.9 * t)
        cr.fill_preserve()
        # Subtle border
        cr.set_source_rgba(theme.border.r, theme.border.g, theme.border.b, 0.6 * t)
        cr.set_line_width(1.0)
        cr.stroke()

        # Platform icon — monochrome geometric initial
        icon_x = bx + pad_x + icon_size / 2
        icon_y = by + y_drift + box_h / 2
        cr.set_source_rgba(theme.muted.r, theme.muted.g, theme.muted.b, t)
        cr.set_font_size(icon_size * 0.75)
        initial = self.platform[0].upper()
        iext = cr.text_extents(initial)
        cr.move_to(icon_x - iext.width / 2, icon_y + iext.height / 2)
        cr.show_text(initial)

        # Handle text
        cr.set_source_rgba(theme.text.r, theme.text.g, theme.text.b, t)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(text_size)
        text_x = bx + pad_x + icon_size + icon_gap
        cr.move_to(text_x, by + y_drift + box_h / 2 + text_size * 0.35)
        cr.show_text(self.handle)

        result = _surface_to_frame(surface, h, w)
        if t == 1.0:
            self._static_cache = result.copy()
        return result


# ── Countdown ───────────────────────────────────────────────────────────


@dataclass
class Countdown(Clip):
    """Animated countdown timer — numbers or clock display.

    Counts down from ``from_n`` to 0, displaying each number for an equal
    portion of the total ``count_duration`` frames.

    Args:
        from_n: Starting number for the countdown.
        count_duration: Total frames for the countdown.
        font: Font family name.
        style: Display style ("numbers" or "clock").
        color: Text color.
        size: Font size in pixels.
    """

    from_n: int = 10
    count_duration: int = 300
    font: str = "sans-serif"
    style: str = "numbers"
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0, 1.0))
    size: float = 120.0

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a countdown frame.

        # DESIGN INTENT: Large monospaced digit, centered, no decoration.
        # REFERENCE: Apple keynote countdown timers.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        theme = get_theme()

        if self.count_duration > 0:
            progress = _clamp01(ctx.local_frame / self.count_duration)
        else:
            progress = 1.0

        current = max(0, self.from_n - int(progress * self.from_n))

        if self.style == "clock":
            minutes = current // 60
            seconds = current % 60
            text = f"{minutes}:{seconds:02d}"
        else:
            text = str(current)

        # Ticker transition: y-drift between digits
        frames_per_number = self.count_duration / max(1, self.from_n)
        within = ctx.local_frame % max(1, int(frames_per_number))
        digit_t = within / max(1, frames_per_number)

        # Subtle Y drift on digit change (design system pattern)
        y_offset = 0.0
        alpha = 1.0
        if digit_t < 0.15:
            # Incoming: y+16→0, opacity 0→1
            enter_t = ease_out_quart(digit_t / 0.15)
            y_offset = 16.0 * (1.0 - enter_t) * (h / 1080)
            alpha = enter_t

        # Use design token colors if default
        c = self.color
        if c.r == 1.0 and c.g == 1.0 and c.b == 1.0:
            c = theme.text

        cr.save()
        cr.translate(w / 2, h / 2 + y_offset)

        cr.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(self.size)
        cr.set_source_rgba(c.r, c.g, c.b, c.a * alpha)

        ext = cr.text_extents(text)
        cr.move_to(-ext.width / 2, ext.height / 2)
        cr.show_text(text)

        # Label below: "SECONDS"
        label_size = scale_size(LABEL.size, h)
        cr.set_source_rgba(theme.muted.r, theme.muted.g, theme.muted.b, alpha)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(label_size)
        label = "SECONDS"
        lext = cr.text_extents(label)
        cr.move_to(-lext.width / 2, ext.height / 2 + label_size * 2)
        cr.show_text(label)

        cr.restore()

        return _surface_to_frame(surface, h, w)


# ── QuoteCard ───────────────────────────────────────────────────────────

_QUOTE_STYLES: dict[str, dict[str, Color]] = {
    "elegant": {
        "bg": Color.parse("#1A1A2E"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
        "attr_color": Color(0.7, 0.7, 0.7, 1.0),
        "accent": Color.parse("#E94560"),
    },
    "light": {
        "bg": Color(1.0, 1.0, 1.0, 0.95),
        "text_color": Color.parse("#111827"),
        "attr_color": Color.parse("#6B7280"),
        "accent": Color.parse("#2563EB"),
    },
    "minimal": {
        "bg": Color(0.0, 0.0, 0.0, 0.0),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
        "attr_color": Color(0.8, 0.8, 0.8, 1.0),
        "accent": Color(1.0, 1.0, 1.0, 0.3),
    },
    "default": {
        "bg": Color(0.1, 0.1, 0.15, 0.9),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
        "attr_color": Color(0.7, 0.7, 0.8, 1.0),
        "accent": Color.parse("#6366F1"),
    },
}


@dataclass
class QuoteCard(Clip):
    """Styled quote overlay with fade-in animation.

    Args:
        text: Quote text.
        attribution: Attribution line (e.g. "— Albert Einstein").
        style: Visual style (elegant, light, minimal, default).
        animate_in: Frames for fade-in animation.
    """

    text: str = ""
    attribution: str = ""
    style: str = "default"
    animate_in: int = 20
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a quote card frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # DESIGN INTENT: Editorial pull-quote — left accent bar, large
        #   quote text, small attribution. No box, no card border.
        # REFERENCE: Medium editorial pull-quotes.

        style_key = self.style if self.style in _QUOTE_STYLES else "default"
        _ = _QUOTE_STYLES[style_key]  # validate style exists
        theme = get_theme()

        if self.animate_in > 0 and ctx.local_frame < self.animate_in:
            t = ease_out_quart(ctx.local_frame / self.animate_in)
        else:
            t = 1.0

        # Return cached static frame when not animating
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        sh = safe_h(w)
        accent_bar_w = 3.0 * (h / 1080)
        text_left_pad = scale_size(SPACE_2, h)
        max_text_w = w * 0.55

        # Quote text setup
        quote_size = scale_size(DISPLAY_SM.size, h)
        attr_size = scale_size(BODY_SM.size, h)

        cr.select_font_face("serif", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(quote_size)

        # Word wrap
        words = self.text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            ext = cr.text_extents(test)
            if ext.width > max_text_w and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        line_h = quote_size * 1.3
        attr_block = scale_size(SPACE_2, h) + attr_size if self.attribution else 0
        content_h = len(lines) * line_h + attr_block
        content_y = (h - content_h) / 2

        # Left accent bar (scaleY animation)
        bar_x = sh
        bar_scale = _clamp01(t * 1.5)  # Bar animates first
        bar_h = content_h * bar_scale
        cr.set_source_rgba(theme.accent.r, theme.accent.g, theme.accent.b, t)
        cr.rectangle(bar_x, content_y, accent_bar_w, bar_h)
        cr.fill()

        text_x = bar_x + accent_bar_w + text_left_pad

        # Opening curly quote in accent color
        cr.set_source_rgba(theme.accent.r, theme.accent.g, theme.accent.b, 0.6 * t)
        cr.select_font_face("serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(quote_size * 1.5)
        quote_ext = cr.text_extents("\u201c")
        cr.move_to(text_x - quote_ext.width * 0.3, content_y + quote_size)
        cr.show_text("\u201c")

        # Quote text with y-drift
        quote_progress = _clamp01((t - 0.2) / 0.8) if t < 1.0 else 1.0
        y_drift = (1.0 - quote_progress) * 16.0 * (h / 1080)
        cr.set_source_rgba(theme.text.r, theme.text.g, theme.text.b, quote_progress)
        cr.select_font_face("serif", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(quote_size)

        text_y = content_y + y_drift
        for line in lines:
            cr.move_to(text_x, text_y + quote_size)
            cr.show_text(line)
            text_y += line_h

        # Attribution
        if self.attribution:
            attr_progress = _clamp01((t - 0.5) / 0.5) if t < 1.0 else 1.0
            cr.set_source_rgba(theme.muted.r, theme.muted.g, theme.muted.b, attr_progress)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(attr_size)
            cr.move_to(text_x, text_y + scale_size(SPACE_2, h) + attr_size)
            cr.show_text(self.attribution.upper())

        result = _surface_to_frame(surface, h, w)
        if t == 1.0:
            self._static_cache = result.copy()
        return result


# ── Divider ─────────────────────────────────────────────────────────────

_DIVIDER_STYLES = frozenset({"line", "dashed", "dots", "gradient", "wave"})


@dataclass
class Divider(Clip):
    """Animated line/shape divider between video sections.

    Args:
        style: Divider style (line, dashed, dots, gradient, wave).
        direction: "horizontal" or "vertical".
        div_duration: Frames for the draw-on animation.
        color: Divider color.
        thickness: Line thickness in pixels.
    """

    style: str = "line"
    direction: str = "horizontal"
    div_duration: int = 24
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0, 0.8))
    thickness: float = 1.0
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a divider frame.

        # DESIGN INTENT: A hairline rule that draws itself, nothing more.
        # REFERENCE: Apple keynote slide dividers.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        if self.div_duration > 0 and ctx.local_frame < self.div_duration:
            t = ease_in_out_quart(ctx.local_frame / self.div_duration)
        else:
            t = 1.0

        # Return cached static frame when not animating
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        theme = get_theme()

        # Default color from token system
        c = self.color
        if c.r == 1.0 and c.g == 1.0 and c.b == 1.0 and c.a == 0.8:
            c = theme.border
        cr.set_source_rgba(c.r, c.g, c.b, c.a)
        cr.set_line_width(self.thickness)

        sh = safe_h(w)
        sv_val = safe_v(h)

        if self.direction == "vertical":
            cx = w / 2
            full_length = h - sv_val * 2
            length = full_length * t
            y_start = (h - full_length) / 2
            if self.style == "dashed":
                dash_len = 10.0
                cr.set_dash([dash_len, dash_len])
            cr.move_to(cx, y_start)
            cr.line_to(cx, y_start + length)
            cr.stroke()
        else:
            cy = h / 2
            full_length = w - sh * 2
            length = full_length * t
            x_start = (w - full_length) / 2
            if self.style == "dashed":
                dash_len = 10.0
                cr.set_dash([dash_len, dash_len])
            if self.style == "dots":
                dot_spacing = 20.0
                n_dots = int(length / dot_spacing)
                for i in range(n_dots):
                    dx = x_start + i * dot_spacing
                    cr.arc(dx, cy, self.thickness * 1.5, 0, 2 * math.pi)
                    cr.fill()
            elif self.style == "wave":
                cr.move_to(x_start, cy)
                n_points = max(2, int(length / 5))
                for i in range(n_points):
                    px = x_start + (i / n_points) * length
                    py = cy + math.sin(i * 0.3) * 8
                    cr.line_to(px, py)
                cr.stroke()
            else:
                # Default: left-to-right draw
                cr.move_to(x_start, cy)
                cr.line_to(x_start + length, cy)
                cr.stroke()

        result = _surface_to_frame(surface, h, w)
        if t == 1.0:
            self._static_cache = result.copy()
        return result


# ── TransitionTitle ─────────────────────────────────────────────────────

_TRANSITION_TITLE_STYLES: dict[str, dict[str, Color]] = {
    "fade": {
        "bg": Color(0.0, 0.0, 0.0, 1.0),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "slide_up": {
        "bg": Color.parse("#1A1A2E"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "zoom": {
        "bg": Color(0.0, 0.0, 0.0, 0.9),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "split": {
        "bg": Color.parse("#0F3460"),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
    "default": {
        "bg": Color(0.05, 0.05, 0.1, 1.0),
        "text_color": Color(1.0, 1.0, 1.0, 1.0),
    },
}


@dataclass
class TransitionTitle(Clip):
    """Full-screen title card with enter/exit animation.

    Args:
        text: Title text.
        style: Animation style (fade, slide_up, zoom, split, default).
        title_duration: Total frames for the title card.
        animate_in: Frames for enter animation.
        animate_out: Frames for exit animation.
        font_size: Title font size.
    """

    text: str = ""
    style: str = "default"
    title_duration: int = 90
    animate_in: int = 15
    animate_out: int = 15
    font_size: float = 48.0
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a transition title frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # DESIGN INTENT: Full-bleed section break with a single centered
        #   text line on a solid dark background, no decorative elements.
        # REFERENCE: Apple WWDC section slides, Stripe marketing videos.

        style_key = self.style if self.style in _TRANSITION_TITLE_STYLES else "default"
        _ = _TRANSITION_TITLE_STYLES[style_key]  # validate style exists
        theme = get_theme()

        dur = self.duration if self.duration > 0 else self.title_duration
        t_in = 1.0
        t_out = 1.0
        if ctx.local_frame < self.animate_in:
            t_in = ease_out_quart(ctx.local_frame / max(1, self.animate_in))
        if ctx.local_frame > dur - self.animate_out:
            remaining = dur - ctx.local_frame
            t_out = ease_in_quart(remaining / max(1, self.animate_out))

        t = min(t_in, t_out)

        # Return cached static frame when not animating
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        # Background — always full opacity (dark)
        cr.set_source_rgba(theme.background.r, theme.background.g, theme.background.b, 1.0)
        cr.paint()

        # Title text — design token sized
        title_size = scale_size(DISPLAY_LG.size, h)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(title_size)
        ext = cr.text_extents(self.text)

        # Position: centered, slightly above vertical center (50% - 10%)
        y_center = h * 0.4
        y_offset = (1.0 - t_in) * 24.0 * (h / 1080)  # y+24→0 drift
        y_exit = 0.0
        if t_out < 1.0:
            y_exit = (1.0 - t_out) * -12.0 * (h / 1080)

        cr.save()
        cr.translate(w / 2, y_center + y_offset + y_exit)
        cr.set_source_rgba(theme.text.r, theme.text.g, theme.text.b, t)
        cr.move_to(-ext.width / 2, ext.height / 2)
        cr.show_text(self.text)
        cr.restore()

        # Hairline rule centered below title (draws outward from center)
        rule_delay_frames = 12
        if ctx.local_frame > rule_delay_frames:
            rule_t = ease_in_out_quart(_clamp01((ctx.local_frame - rule_delay_frames) / 12.0))
            rule_w = 80.0 * (w / 1920) * rule_t
            rule_y = y_center + ext.height / 2 + scale_size(SPACE_3, h)
            cr.set_source_rgba(theme.border.r, theme.border.g, theme.border.b, t)
            cr.set_line_width(1.0)
            cr.move_to(w / 2 - rule_w / 2, rule_y)
            cr.line_to(w / 2 + rule_w / 2, rule_y)
            cr.stroke()

        result = _surface_to_frame(surface, h, w)
        if t == 1.0:
            self._static_cache = result.copy()
        return result


# ── Watermark ───────────────────────────────────────────────────────────

_WATERMARK_POSITIONS = frozenset(
    {
        "top-left",
        "top-right",
        "bottom-left",
        "bottom-right",
        "center",
    }
)


@dataclass
class Watermark(Clip):
    """Persistent branded watermark overlay.

    Renders text (or a placeholder for an image) as a semi-transparent
    watermark at a named position.

    Args:
        image_or_text: Text to render as watermark. For image watermarks,
            use a compositing approach instead.
        position: Named position (top-left, top-right, bottom-left,
            bottom-right, center).
        watermark_opacity: Opacity of the watermark (0.0–1.0).
        font_size: Text size in pixels.
        color: Watermark text color.
        margin: Margin from edges in pixels.
    """

    image_or_text: str = ""
    position: str = "top-right"
    watermark_opacity: float = 0.15
    font_size: float = 18.0
    color: Color = field(default_factory=lambda: Color(1.0, 1.0, 1.0, 1.0))
    margin: float = 20.0
    _static_cache: np.ndarray | None = field(default=None, repr=False, compare=False)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a watermark frame.

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        # Watermark is fully static — cache after first render
        if self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        if not self.image_or_text:
            return _surface_to_frame(surface, h, w)

        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(self.font_size)
        ext = cr.text_extents(self.image_or_text)

        # Position calculation
        pos = self.position if self.position in _WATERMARK_POSITIONS else "bottom-right"
        if pos == "top-left":
            tx = self.margin
            ty = self.margin + ext.height
        elif pos == "top-right":
            tx = w - ext.width - self.margin
            ty = self.margin + ext.height
        elif pos == "bottom-left":
            tx = self.margin
            ty = h - self.margin
        elif pos == "bottom-right":
            tx = w - ext.width - self.margin
            ty = h - self.margin
        else:  # center
            tx = (w - ext.width) / 2
            ty = (h + ext.height) / 2

        c = self.color
        cr.set_source_rgba(c.r, c.g, c.b, c.a * self.watermark_opacity)
        cr.move_to(tx, ty)
        cr.show_text(self.image_or_text)

        result = _surface_to_frame(surface, h, w)
        self._static_cache = result.copy()
        return result
