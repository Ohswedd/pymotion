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
from pymotion.design.renderer import (
    draw_pill,
    draw_rounded_rect,
    draw_shadow_surface,
    set_text_rendering,
)
from pymotion.design.tokens import (
    NEUTRAL,
    RADIUS_FULL,
    get_theme,
    safe_h,
    safe_v,
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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions (scale all values by comp_height/1080)
        # Background: none (transparent overlay)
        # Z-order (bottom to top):
        #   1. Accent bar: 3*scale wide, full component height, #6366F1
        #   2. Name chip: pill shape, neutral_800 bg, 8*scale gap from bar
        #      Name text: Inter SemiBold 13*scale, ALL CAPS, 0.08em tracking
        #      Color: neutral_100 (#F4F4F5)
        #   3. Title text: Inter Regular 13*scale, neutral_400, below chip
        # Text baseline: vertically centered in chip (name), top-aligned (title)
        # Contrast mechanism: neutral_800 chip on any dark bg; accent bar provides color
        # Position: safe_h from left, safe_v from bottom
        # ─────────────────────────────────────────────────────
        """
        set_text_rendering(cr)
        t = get_theme()
        scale = h / 1080

        # Token-scaled sizes
        name_size = 13.0 * scale
        title_size = 13.0 * scale
        pad_h = 16.0 * scale  # horizontal padding inside chip
        pad_v = 8.0 * scale  # vertical padding inside chip
        accent_w = 3.0 * scale
        bar_gap = 8.0 * scale  # gap between accent bar and chip
        chip_title_gap = 6.0 * scale  # gap between chip bottom and title
        sh = safe_h(w)
        sv = safe_v(h)

        # Measure name text (ALL CAPS with letter spacing)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(name_size)
        name_upper = self.name.upper()
        name_ext = cr.text_extents(name_upper)
        # Approximate 0.08em letter spacing
        letter_spacing = name_size * 0.08
        name_text_w = name_ext.width + letter_spacing * max(0, len(name_upper) - 1)

        # Measure title text
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(title_size)
        title_ext = cr.text_extents(self.title)

        # Chip dimensions
        chip_w = name_text_w + 2.0 * pad_h
        chip_h = name_size + 2.0 * pad_v

        # Total height: accent bar spans chip + gap + title
        title_h = title_ext.height if self.title else 0.0
        total_h = chip_h + chip_title_gap + title_h

        # Bounding box position
        bx = sh
        by = h - sv - total_h

        # Animation: slide in from left
        x_offset = (1.0 - progress) * (-24.0 * scale)
        bx += x_offset

        # LAYER 1: Accent bar (full component height)
        cr.set_source_rgba(t.accent.r, t.accent.g, t.accent.b, progress)
        cr.rectangle(bx, by, accent_w, total_h)
        cr.fill()

        # LAYER 2: Name chip (pill shape)
        chip_x = bx + accent_w + bar_gap
        chip_y = by
        # Use neutral_800 (#27272A) for chip bg — distinct from both n950 and n900
        n800 = NEUTRAL.n800
        draw_pill(cr, chip_x, chip_y, chip_w, chip_h, None)
        cr.set_source_rgba(n800.r, n800.g, n800.b, 0.95 * progress)
        cr.fill()

        # Name text inside chip (ALL CAPS, letter-spaced)
        n100 = NEUTRAL.n100
        cr.set_source_rgba(n100.r, n100.g, n100.b, progress)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(name_size)
        # Vertically center text in chip
        text_y = chip_y + chip_h / 2.0 + name_ext.height / 2.0
        # Draw with letter spacing
        cx = chip_x + pad_h
        for i, ch in enumerate(name_upper):
            cr.move_to(cx, text_y)
            cr.show_text(ch)
            char_ext = cr.text_extents(ch)
            cx += char_ext.x_advance + (letter_spacing if i < len(name_upper) - 1 else 0)

        # LAYER 3: Title text below chip
        if self.title:
            title_progress = _clamp01((progress - 0.3) / 0.7) if progress < 1.0 else 1.0
            n400 = NEUTRAL.n400
            cr.set_source_rgba(n400.r, n400.g, n400.b, title_progress)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(title_size)
            title_y = chip_y + chip_h + chip_title_gap + title_ext.height
            # Align title X with name text left edge
            cr.move_to(chip_x + pad_h, title_y)
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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Z-order:
        #   1. Logo area: rounded rect (radius 16*scale), centered,
        #      scaled logo_size by (comp_height / 1080)
        #   2. Reveal animation: style-dependent (fade, grow, slice, etc.)
        #      All animations use ease_out_quart
        # Design tokens: rounded corners, scaled dimensions, set_text_rendering
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

        if self.style not in _LOGO_REVEAL_STYLES:
            valid = ", ".join(sorted(_LOGO_REVEAL_STYLES))
            msg = f"Unknown logo reveal style '{self.style}'. Valid: {valid}"
            raise ValueError(msg)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        # Animation progress — use design-system easing
        if self.reveal_duration > 0 and ctx.local_frame < self.reveal_duration:
            t = ease_out_quart(ctx.local_frame / self.reveal_duration)
        else:
            t = 1.0

        # Return cached static frame when reveal is complete
        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        # Scale logo size with resolution
        lw = self.logo_size[0] * scale
        lh = self.logo_size[1] * scale
        lx = (w - lw) / 2.0
        ly = (h - lh) / 2.0
        c = self.logo_color
        corner_r = 16.0 * scale

        if self.style == "fade":
            s_val = 0.95 + 0.05 * t
            cr.save()
            cr.translate(w / 2.0, h / 2.0)
            cr.scale(s_val, s_val)
            cr.translate(-w / 2.0, -h / 2.0)
            cr.set_source_rgba(c.r, c.g, c.b, c.a * t)
            draw_rounded_rect(cr, lx, ly, lw, lh, corner_r)
            cr.fill()
            cr.restore()
        elif self.style == "grow":
            s = max(t, 1e-6)
            cr.save()
            cr.translate(w / 2.0, h / 2.0)
            cr.scale(s, s)
            cr.translate(-w / 2.0, -h / 2.0)
            cr.set_source_rgba(c.r, c.g, c.b, c.a)
            draw_rounded_rect(cr, lx, ly, lw, lh, corner_r)
            cr.fill()
            cr.restore()
        elif self.style == "slice":
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
            n_slices = 12
            for i in range(n_slices):
                slice_h = lh / n_slices
                sy = ly + i * slice_h
                offset = math.sin(i * 3.7 + ctx.local_frame * 0.5) * 20.0 * scale * (1.0 - t)
                cr.set_source_rgba(c.r, c.g, c.b, c.a * min(1.0, t * 1.5))
                cr.rectangle(lx + offset, sy, lw, slice_h)
                cr.fill()
        elif self.style == "draw":
            perimeter = 2 * (lw + lh)
            drawn = perimeter * t
            cr.set_source_rgba(c.r, c.g, c.b, c.a)
            cr.set_line_width(3.0 * scale)
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
            if t > 0.5:
                fill_t = (t - 0.5) * 2
                cr.set_source_rgba(c.r, c.g, c.b, c.a * fill_t * 0.8)
                draw_rounded_rect(cr, lx, ly, lw, lh, corner_r)
                cr.fill()
        elif self.style == "shatter":
            nx, ny = 4, 4
            pw = lw / nx
            ph = lh / ny
            for ix in range(nx):
                for iy in range(ny):
                    px = lx + ix * pw
                    py_base = ly + iy * ph
                    scatter = (1.0 - t) * 150.0 * scale
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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent overlay)
        # Z-order (bottom to top):
        #   1. Glow: same pill blurred, accent at 19% opacity
        #   2. Pill bg: accent #6366F1, full radius
        #   3. Main text: Inter SemiBold 22*scale, white, centered in pill
        #   4. Sub text: Inter Regular 13*scale, neutral_400, below pill
        # Position: horizontal center, bottom safe zone
        # Contrast: bright accent pill on dark bg
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        if self.animate_in > 0 and ctx.local_frame < self.animate_in:
            t = ease_out_quart(ctx.local_frame / self.animate_in)
        else:
            t = 1.0

        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        theme = get_theme()
        scale = h / 1080

        text_size = 22.0 * scale
        sub_size = 13.0 * scale
        pad_h = 32.0 * scale
        pad_v = 16.0 * scale
        sv = safe_v(h)

        # Measure main text
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(text_size)
        text_ext = cr.text_extents(self.text)

        pill_w = text_ext.width + 2.0 * pad_h
        pill_h = text_size + 2.0 * pad_v
        pill_x = (w - pill_w) / 2.0
        pill_y = h - sv - pill_h

        # Scale animation (0.92→1.0)
        cr.save()
        s_val = 0.92 + 0.08 * t
        cr.translate(w / 2.0, pill_y + pill_h / 2.0)
        cr.scale(s_val, s_val)
        cr.translate(-w / 2.0, -(pill_y + pill_h / 2.0))

        # LAYER 1: Glow (accent at 19% opacity, blurred)
        glow_color = Color(theme.accent.r, theme.accent.g, theme.accent.b, 0.19 * t)
        draw_shadow_surface(
            cr,
            pill_x,
            pill_y,
            pill_w,
            pill_h,
            RADIUS_FULL,
            24.0 * scale,
            0.0,
            glow_color,
        )

        # LAYER 2: Pill background
        draw_pill(cr, pill_x, pill_y, pill_w, pill_h, None)
        cr.set_source_rgba(theme.accent.r, theme.accent.g, theme.accent.b, t)
        cr.fill()

        # LAYER 3: Main text (centered in pill)
        cr.set_source_rgba(1.0, 1.0, 1.0, t)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(text_size)
        text_x = pill_x + (pill_w - text_ext.width) / 2.0
        text_y = pill_y + pill_h / 2.0 + text_ext.height / 2.0
        cr.move_to(text_x, text_y)
        cr.show_text(self.text)

        cr.restore()

        # LAYER 4: Sub text below pill (outside scale transform)
        if self.sub_text:
            sub_progress = _clamp01((t - 0.3) / 0.7) if t < 1.0 else 1.0
            n400 = NEUTRAL.n400
            cr.set_source_rgba(n400.r, n400.g, n400.b, sub_progress)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(sub_size)
            sub_ext = cr.text_extents(self.sub_text)
            sub_x = (w - sub_ext.width) / 2.0
            sub_y = pill_y + pill_h + 8.0 * scale + sub_ext.height
            cr.move_to(sub_x, sub_y)
            cr.show_text(self.sub_text)

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

    def _draw_platform_icon(
        self,
        cr: cairo.Context[cairo.ImageSurface],
        cx: float,
        cy: float,
        size: float,
        color: Color,
        opacity: float,
    ) -> None:
        """Draw a platform-specific icon as Cairo paths.

        Args:
            cr: Cairo context.
            cx: Center X of the icon area.
            cy: Center Y of the icon area.
            size: Icon size (16*scale).
            color: Icon color.
            opacity: Alpha multiplier.
        """
        cr.set_source_rgba(color.r, color.g, color.b, opacity)
        half = size / 2.0
        lw = 1.5 * (size / 16.0)

        if self.platform == "youtube":
            # Rounded rect + triangle
            rr = 3.0 * (size / 16.0)
            draw_rounded_rect(cr, cx - half, cy - half * 0.7, size, size * 0.7, rr)
            cr.fill()
            # Play triangle in chip bg color
            n800 = NEUTRAL.n800
            cr.set_source_rgba(n800.r, n800.g, n800.b, 0.9 * opacity)
            tri_size = size * 0.25
            cr.move_to(cx - tri_size * 0.4, cy - tri_size)
            cr.line_to(cx + tri_size * 0.8, cy)
            cr.line_to(cx - tri_size * 0.4, cy + tri_size)
            cr.close_path()
            cr.fill()
        elif self.platform == "instagram":
            # Rounded square + inner circle + small circle
            rr = 4.0 * (size / 16.0)
            cr.set_line_width(lw)
            draw_rounded_rect(cr, cx - half, cy - half, size, size, rr)
            cr.stroke()
            cr.arc(cx, cy, size * 0.28, 0, 2 * math.pi)
            cr.stroke()
            cr.arc(cx + half * 0.55, cy - half * 0.55, size * 0.08, 0, 2 * math.pi)
            cr.fill()
        elif self.platform == "x":
            # Two crossing diagonal strokes
            margin = 2.0 * (size / 16.0)
            cr.set_line_width(lw)
            cr.move_to(cx - half + margin, cy - half + margin)
            cr.line_to(cx + half - margin, cy + half - margin)
            cr.stroke()
            cr.move_to(cx + half - margin, cy - half + margin)
            cr.line_to(cx - half + margin, cy + half - margin)
            cr.stroke()
        elif self.platform == "linkedin":
            # Rounded square with "in" text
            rr = 2.0 * (size / 16.0)
            draw_rounded_rect(cr, cx - half, cy - half, size, size, rr)
            cr.fill()
            n800 = NEUTRAL.n800
            cr.set_source_rgba(n800.r, n800.g, n800.b, 0.9 * opacity)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(size * 0.6)
            in_ext = cr.text_extents("in")
            cr.move_to(cx - in_ext.width / 2.0, cy + in_ext.height / 2.0)
            cr.show_text("in")
        elif self.platform == "tiktok":
            # Music note shape: vertical stroke + horizontal cap
            cr.set_line_width(size * 0.22)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(cx, cy + half * 0.6)
            cr.line_to(cx, cy - half * 0.5)
            cr.stroke()
            cr.set_line_width(size * 0.15)
            cr.move_to(cx, cy - half * 0.5)
            cr.line_to(cx + half * 0.5, cy - half * 0.7)
            cr.stroke()
        else:
            # Fallback: filled circle
            cr.arc(cx, cy, size * 0.25, 0, 2 * math.pi)
            cr.fill()

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a social handle overlay frame.

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent overlay)
        # Z-order (bottom to top):
        #   1. Chip bg: rgba(27,27,42,0.9) neutral_800 90%, pill shape
        #      Border: 1*scale, neutral_700 60%
        #   2. Platform icon: Cairo path, 16*scale, neutral_400
        #   3. Handle text: Inter Medium 13*scale, neutral_200
        # Position: safe_h from left, safe_v from bottom
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        if self.animate_in > 0 and ctx.local_frame < self.animate_in:
            t = ease_out_quart(ctx.local_frame / self.animate_in)
        else:
            t = 1.0

        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        scale = h / 1080
        chip_h = 36.0 * scale
        icon_size = 16.0 * scale
        pad_h = 12.0 * scale
        icon_gap = 8.0 * scale
        sh = safe_h(w)
        sv = safe_v(h)

        # Measure handle text
        text_size = 13.0 * scale
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(text_size)
        ext = cr.text_extents(self.handle)

        chip_w = pad_h + icon_size + icon_gap + ext.width + pad_h
        bx = sh
        by = h - sv - chip_h

        # Y-drift animation
        y_drift = (1.0 - t) * 8.0 * scale

        # LAYER 1: Chip background (pill, frosted glass)
        n800 = NEUTRAL.n800
        draw_pill(cr, bx, by + y_drift, chip_w, chip_h, None)
        cr.set_source_rgba(n800.r, n800.g, n800.b, 0.9 * t)
        cr.fill_preserve()
        # Border
        n700 = NEUTRAL.n700
        cr.set_source_rgba(n700.r, n700.g, n700.b, 0.6 * t)
        cr.set_line_width(1.0 * scale)
        cr.stroke()

        # LAYER 2: Platform icon
        icon_cx = bx + pad_h + icon_size / 2.0
        icon_cy = by + y_drift + chip_h / 2.0
        n400 = NEUTRAL.n400
        self._draw_platform_icon(cr, icon_cx, icon_cy, icon_size, n400, t)

        # LAYER 3: Handle text
        n200 = NEUTRAL.n200
        cr.set_source_rgba(n200.r, n200.g, n200.b, t)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(text_size)
        text_x = bx + pad_h + icon_size + icon_gap
        text_y = by + y_drift + chip_h / 2.0 + ext.height / 2.0
        cr.move_to(text_x, text_y)
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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent overlay)
        # Z-order (bottom to top):
        #   1. Digit: JetBrains Mono Bold 120*scale, neutral_100, centered
        #   2. Label: Inter Medium 11*scale, ALL CAPS 0.15em, neutral_400
        #      "SECONDS", centered below digit
        # Transition: outgoing digit y 0→-20*scale opacity 1→0 (9f)
        #             incoming digit y 20*scale→0 opacity 0→1 (9f)
        # Position: horizontal center, comp_height * 0.45
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

        n100 = NEUTRAL.n100
        n400 = NEUTRAL.n400

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

        # Digit transition: overlapping outgoing + incoming
        frames_per_number = self.count_duration / max(1, self.from_n)
        within = ctx.local_frame % max(1, int(frames_per_number))
        transition_frames = 9

        digit_size = 120.0 * scale
        center_y = h * 0.45

        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(digit_size)

        if within < transition_frames and ctx.local_frame > 0:
            # Transition phase: render both outgoing and incoming digits
            trans_t = within / max(1, transition_frames)

            # Outgoing digit (previous number)
            prev = min(self.from_n, current + 1)
            prev_text = str(prev)
            out_t = ease_in_quart(trans_t)
            out_y_offset = -20.0 * scale * out_t
            out_alpha = 1.0 - out_t

            ext = cr.text_extents(prev_text)
            cr.set_source_rgba(n100.r, n100.g, n100.b, out_alpha)
            cr.move_to(
                w / 2.0 - ext.width / 2.0,
                center_y + ext.height / 2.0 + out_y_offset,
            )
            cr.show_text(prev_text)

            # Incoming digit (current number)
            in_t = ease_out_quart(trans_t)
            in_y_offset = 20.0 * scale * (1.0 - in_t)
            in_alpha = in_t

            ext2 = cr.text_extents(text)
            cr.set_source_rgba(n100.r, n100.g, n100.b, in_alpha)
            cr.move_to(
                w / 2.0 - ext2.width / 2.0,
                center_y + ext2.height / 2.0 + in_y_offset,
            )
            cr.show_text(text)
            digit_bottom = center_y + ext2.height / 2.0
        else:
            # Static phase: just render current digit
            ext = cr.text_extents(text)
            cr.set_source_rgba(n100.r, n100.g, n100.b, 1.0)
            cr.move_to(w / 2.0 - ext.width / 2.0, center_y + ext.height / 2.0)
            cr.show_text(text)
            digit_bottom = center_y + ext.height / 2.0

        # LAYER 2: Label
        label_size = 11.0 * scale
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(label_size)
        label = "SECONDS"
        lext = cr.text_extents(label)
        label_y = digit_bottom + 12.0 * scale + lext.height
        # Draw with 0.15em letter spacing
        ls = label_size * 0.15
        total_label_w = lext.width + ls * max(0, len(label) - 1)
        lx = w / 2.0 - total_label_w / 2.0
        cr.set_source_rgba(n400.r, n400.g, n400.b, 1.0)
        for i, ch in enumerate(label):
            cr.move_to(lx, label_y)
            cr.show_text(ch)
            cext = cr.text_extents(ch)
            lx += cext.x_advance + (ls if i < len(label) - 1 else 0)

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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent overlay)
        # Z-order (bottom to top):
        #   1. Accent bar: 3*scale wide, full content height, accent color
        #   2. Opening quote mark: accent color, same font/size
        #   3. Quote text: Inter Regular italic 32*scale, neutral_100, line_height 1.35
        #   4. Attribution: Inter Medium 11*scale, ALL CAPS 0.1em, neutral_400
        # Position: safe_h from left, vertically centered at 44%
        # Contrast: bright text on transparent bg
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        style_key = self.style if self.style in _QUOTE_STYLES else "default"
        _ = _QUOTE_STYLES[style_key]
        theme = get_theme()
        scale = h / 1080

        if self.animate_in > 0 and ctx.local_frame < self.animate_in:
            t = ease_out_quart(ctx.local_frame / self.animate_in)
        else:
            t = 1.0

        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        sh = safe_h(w)
        accent_bar_w = 3.0 * scale
        text_gap = 16.0 * scale
        max_text_w = w * 0.55

        quote_size = 32.0 * scale
        attr_size = 11.0 * scale
        line_h = quote_size * 1.35

        # Word wrap
        cr.select_font_face("serif", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(quote_size)
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

        attr_block = (16.0 * scale + attr_size) if self.attribution else 0
        content_h = len(lines) * line_h + attr_block

        # Center content at optical center (44%)
        content_y = h * 0.44 - content_h / 2.0
        text_x = sh + accent_bar_w + text_gap

        # Opening quote mark measurement
        cr.select_font_face("serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(quote_size)
        qmark_ext = cr.text_extents("\u201c")

        # LAYER 1: Accent bar
        bar_scale = _clamp01(t * 1.5)
        cr.set_source_rgba(theme.accent.r, theme.accent.g, theme.accent.b, t)
        cr.rectangle(sh, content_y, accent_bar_w, content_h * bar_scale)
        cr.fill()

        # LAYER 2: Opening quote mark
        cr.set_source_rgba(theme.accent.r, theme.accent.g, theme.accent.b, 0.6 * t)
        cr.select_font_face("serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(quote_size)
        cr.move_to(text_x - qmark_ext.width - 4.0 * scale, content_y + quote_size)
        cr.show_text("\u201c")

        # LAYER 3: Quote text
        quote_progress = _clamp01((t - 0.2) / 0.8) if t < 1.0 else 1.0
        y_drift = (1.0 - quote_progress) * 16.0 * scale
        n100 = NEUTRAL.n100
        cr.set_source_rgba(n100.r, n100.g, n100.b, quote_progress)
        cr.select_font_face("serif", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(quote_size)

        text_y = content_y + y_drift
        for line in lines:
            cr.move_to(text_x, text_y + quote_size)
            cr.show_text(line)
            text_y += line_h

        # LAYER 4: Attribution
        if self.attribution:
            attr_progress = _clamp01((t - 0.5) / 0.5) if t < 1.0 else 1.0
            n400 = NEUTRAL.n400
            cr.set_source_rgba(n400.r, n400.g, n400.b, attr_progress)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(attr_size)
            attr_text = self.attribution.upper()
            # Letter spacing 0.1em
            ls = attr_size * 0.1
            attr_y = text_y + 16.0 * scale + attr_size
            ax = text_x
            for i, ch in enumerate(attr_text):
                cr.move_to(ax, attr_y)
                cr.show_text(ch)
                cext = cr.text_extents(ch)
                ax += cext.x_advance + (ls if i < len(attr_text) - 1 else 0)

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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: comp dimensions
        # Background: none (transparent overlay)
        # Element: hairline rule, 1*scale thick, neutral_700
        # Animation: draws from center outward (horizontal) or
        #            from center outward (vertical)
        # Position: centered at comp_height/2 (h) or comp_width/2 (v)
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height
        scale = h / 1080

        if self.div_duration > 0 and ctx.local_frame < self.div_duration:
            t = ease_in_out_quart(ctx.local_frame / self.div_duration)
        else:
            t = 1.0

        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)

        # Use neutral_700 for visibility on dark backgrounds
        n700 = NEUTRAL.n700
        c = self.color
        if c.r == 1.0 and c.g == 1.0 and c.b == 1.0 and c.a == 0.8:
            c = n700
        cr.set_source_rgba(c.r, c.g, c.b, c.a)
        cr.set_line_width(max(1.0, self.thickness * scale))

        sh = safe_h(w)
        sv_val = safe_v(h)

        if self.direction == "vertical":
            cx = w / 2.0
            full_length = h - sv_val * 2
            length = full_length * t
            # Draw from center outward
            mid_y = h / 2.0
            if self.style == "dashed":
                cr.set_dash([10.0 * scale, 10.0 * scale])
            cr.move_to(cx, mid_y - length / 2.0)
            cr.line_to(cx, mid_y + length / 2.0)
            cr.stroke()
        else:
            cy = h / 2.0
            full_length = w - sh * 2
            length = full_length * t
            # Draw from center outward
            mid_x = w / 2.0
            if self.style == "dashed":
                cr.set_dash([10.0 * scale, 10.0 * scale])
            if self.style == "dots":
                dot_spacing = 20.0 * scale
                n_dots = max(1, int(length / dot_spacing))
                start_x = mid_x - length / 2.0
                for i in range(n_dots):
                    dx = start_x + i * dot_spacing
                    cr.arc(dx, cy, self.thickness * 1.5 * scale, 0, 2 * math.pi)
                    cr.fill()
            elif self.style == "wave":
                start_x = mid_x - length / 2.0
                cr.move_to(start_x, cy)
                n_points = max(2, int(length / (5.0 * scale)))
                for i in range(n_points):
                    px = start_x + (i / n_points) * length
                    py = cy + math.sin(i * 0.3) * 8.0 * scale
                    cr.line_to(px, py)
                cr.stroke()
            else:
                cr.move_to(mid_x - length / 2.0, cy)
                cr.line_to(mid_x + length / 2.0, cy)
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

        # RENDER INTENT
        # ─────────────────────────────────────────────────────
        # Canvas: full frame (1920x1080 or comp dims)
        # Background: neutral_950 flat fill
        # Z-order (bottom to top):
        #   1. Full background fill
        #   2. Title text: Inter Bold 56*scale, centered, y=44% optical center
        #      letter_spacing: -0.02em, color neutral_100
        #   3. Hairline rule: 80*scale wide, 1*scale, neutral_700
        #      y = title_bottom + 24*scale, draws from center outward
        # Contrast: white text on near-black background
        # ─────────────────────────────────────────────────────

        Args:
            ctx: The render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        w = ctx.resolution.width
        h = ctx.resolution.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr: cairo.Context[cairo.ImageSurface] = cairo.Context(surface)
        set_text_rendering(cr)

        style_key = self.style if self.style in _TRANSITION_TITLE_STYLES else "default"
        _ = _TRANSITION_TITLE_STYLES[style_key]
        theme = get_theme()
        scale = h / 1080

        dur = self.duration if self.duration > 0 else self.title_duration
        t_in = 1.0
        t_out = 1.0
        if ctx.local_frame < self.animate_in:
            t_in = ease_out_quart(ctx.local_frame / max(1, self.animate_in))
        if ctx.local_frame > dur - self.animate_out:
            remaining = dur - ctx.local_frame
            t_out = ease_in_quart(remaining / max(1, self.animate_out))

        t = min(t_in, t_out)

        if t == 1.0 and self._static_cache is not None:
            if self._static_cache.shape[:2] == (h, w):
                return self._static_cache.copy()

        # LAYER 1: Background fill
        cr.set_source_rgba(theme.background.r, theme.background.g, theme.background.b, 1.0)
        cr.paint()

        # LAYER 2: Title text
        title_size = 56.0 * scale
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(title_size)
        ext = cr.text_extents(self.text)

        # Negative letter spacing (-0.02em)
        neg_tracking = title_size * -0.02
        # Compute total text width with tracking
        total_text_w = ext.width + neg_tracking * max(0, len(self.text) - 1)

        y_center = h * 0.44
        y_drift_in = (1.0 - t_in) * 24.0 * scale
        y_drift_out = (1.0 - t_out) * -12.0 * scale if t_out < 1.0 else 0.0

        # Draw title with negative tracking
        n100 = NEUTRAL.n100
        cr.set_source_rgba(n100.r, n100.g, n100.b, t)
        cx = (w - total_text_w) / 2.0
        text_baseline = y_center + y_drift_in + y_drift_out + ext.height / 2.0
        for i, ch in enumerate(self.text):
            cr.move_to(cx, text_baseline)
            cr.show_text(ch)
            char_ext = cr.text_extents(ch)
            cx += char_ext.x_advance + (neg_tracking if i < len(self.text) - 1 else 0)

        # LAYER 3: Hairline rule
        rule_delay = 12
        if ctx.local_frame > rule_delay:
            rule_t = ease_in_out_quart(_clamp01((ctx.local_frame - rule_delay) / 12.0))
            rule_full_w = 80.0 * scale
            rule_w = rule_full_w * rule_t
            rule_y = y_center + ext.height / 2.0 + 24.0 * scale + y_drift_in + y_drift_out
            n700 = NEUTRAL.n700
            cr.set_source_rgba(n700.r, n700.g, n700.b, t)
            cr.set_line_width(1.0 * scale)
            cr.move_to(w / 2.0 - rule_w / 2.0, rule_y)
            cr.line_to(w / 2.0 + rule_w / 2.0, rule_y)
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
