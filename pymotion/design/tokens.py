"""Design tokens — single source of truth for all visual defaults.

Defines color palettes, typography scale, spacing, geometry, shadows,
and theme system used by every component in the library.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from pymotion.utils.color import Color

# ── Color Palettes ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class NeutralPalette:
    """Zinc-based neutral color scale (matches shadcn/ui zinc)."""

    n950: Color = field(default_factory=lambda: Color.parse("#09090B"))
    n900: Color = field(default_factory=lambda: Color.parse("#18181B"))
    n800: Color = field(default_factory=lambda: Color.parse("#27272A"))
    n700: Color = field(default_factory=lambda: Color.parse("#3F3F46"))
    n600: Color = field(default_factory=lambda: Color.parse("#52525B"))
    n500: Color = field(default_factory=lambda: Color.parse("#71717A"))
    n400: Color = field(default_factory=lambda: Color.parse("#A1A1AA"))
    n300: Color = field(default_factory=lambda: Color.parse("#D4D4D8"))
    n200: Color = field(default_factory=lambda: Color.parse("#E4E4E7"))
    n100: Color = field(default_factory=lambda: Color.parse("#F4F4F5"))
    n50: Color = field(default_factory=lambda: Color.parse("#FAFAFA"))


@dataclass(frozen=True)
class AccentPalette:
    """Modern blue-violet accent scale."""

    a600: Color = field(default_factory=lambda: Color.parse("#4F46E5"))
    a500: Color = field(default_factory=lambda: Color.parse("#6366F1"))
    a400: Color = field(default_factory=lambda: Color.parse("#818CF8"))
    a300: Color = field(default_factory=lambda: Color.parse("#A5B4FC"))
    glow: Color = field(default_factory=lambda: Color(0.31, 0.27, 0.90, 0.12))


@dataclass(frozen=True)
class StatusPalette:
    """Semantic status colors."""

    success: Color = field(default_factory=lambda: Color.parse("#22C55E"))
    warning: Color = field(default_factory=lambda: Color.parse("#F59E0B"))
    error: Color = field(default_factory=lambda: Color.parse("#EF4444"))


NEUTRAL = NeutralPalette()
ACCENT = AccentPalette()
STATUS = StatusPalette()

CHART_COLORS: list[Color] = [
    Color.parse("#6366F1"),  # indigo
    Color.parse("#EC4899"),  # pink
    Color.parse("#F59E0B"),  # amber
    Color.parse("#10B981"),  # emerald
    Color.parse("#3B82F6"),  # blue
    Color.parse("#8B5CF6"),  # violet
    Color.parse("#F97316"),  # orange
    Color.parse("#14B8A6"),  # teal
]


# ── Theme System ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Theme:
    """Complete visual theme for a composition.

    Args:
        name: Theme identifier.
        background: Main background color.
        surface: Elevated surface color (cards, bars).
        border: Border/divider color.
        text: Primary text color.
        muted: Muted/secondary text color.
        accent: Primary accent color.
    """

    name: str
    background: Color
    surface: Color
    border: Color
    text: Color
    muted: Color
    accent: Color


THEMES: dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        background=NEUTRAL.n950,
        surface=NEUTRAL.n900,
        border=NEUTRAL.n700,
        text=NEUTRAL.n100,
        muted=NEUTRAL.n500,
        accent=ACCENT.a500,
    ),
    "light": Theme(
        name="light",
        background=NEUTRAL.n50,
        surface=NEUTRAL.n100,
        border=NEUTRAL.n200,
        text=NEUTRAL.n950,
        muted=NEUTRAL.n500,
        accent=ACCENT.a600,
    ),
    "midnight": Theme(
        name="midnight",
        background=Color.parse("#020817"),
        surface=Color.parse("#0F172A"),
        border=Color.parse("#1E3A5F"),
        text=Color.parse("#E2E8F0"),
        muted=Color.parse("#64748B"),
        accent=Color.parse("#38BDF8"),
    ),
    "warm": Theme(
        name="warm",
        background=Color.parse("#1C1917"),
        surface=Color.parse("#292524"),
        border=Color.parse("#44403C"),
        text=Color.parse("#FAFAF9"),
        muted=Color.parse("#78716C"),
        accent=Color.parse("#FB923C"),
    ),
}

_theme_lock = threading.Lock()
_active_theme: str = "dark"


def get_theme(name: str | None = None) -> Theme:
    """Get a theme by name, or the active theme if no name given.

    Args:
        name: Theme name. If None, returns the active theme.

    Returns:
        The requested Theme.

    Raises:
        ValueError: If the theme name is unknown.
    """
    if name is None:
        with _theme_lock:
            name = _active_theme
    if name not in THEMES:
        valid = ", ".join(sorted(THEMES))
        msg = f"Unknown theme '{name}'. Valid: {valid}"
        raise ValueError(msg)
    return THEMES[name]


def set_theme(name: str) -> None:
    """Set the active theme.

    Args:
        name: Theme name (dark, light, midnight, warm).

    Raises:
        ValueError: If the theme name is unknown.
    """
    global _active_theme  # noqa: PLW0603
    if name not in THEMES:
        valid = ", ".join(sorted(THEMES))
        msg = f"Unknown theme '{name}'. Valid: {valid}"
        raise ValueError(msg)
    with _theme_lock:
        _active_theme = name


def reset_theme() -> None:
    """Reset the active theme to 'dark'."""
    global _active_theme  # noqa: PLW0603
    with _theme_lock:
        _active_theme = "dark"


# ── Typography Scale ────────────────────────────────────────────────────

FONT_PRIMARY = "Inter"
FONT_DISPLAY = "Inter"
FONT_MONO = "JetBrains Mono"
FONT_FALLBACK = ["Inter", "system-ui", "sans-serif"]


@dataclass(frozen=True)
class TextStyle:
    """A text style definition from the typography scale.

    Args:
        size: Font size in px at 1080p.
        weight: Font weight (400=regular, 500=medium, 600=semibold,
            700=bold, 800=extrabold).
        tracking: Letter spacing in px.
        line_height: Line height multiplier.
        font: Font family name.
        uppercase: Whether text should be rendered in uppercase.
    """

    size: float
    weight: int
    tracking: float = 0.0
    line_height: float = 1.6
    font: str = FONT_PRIMARY
    uppercase: bool = False


# Text scale — all sizes at 1080p
DISPLAY_2XL = TextStyle(96, 800, tracking=-2.0, line_height=1.0)
DISPLAY_XL = TextStyle(72, 800, tracking=-2.0, line_height=1.0)
DISPLAY_LG = TextStyle(56, 700, tracking=-1.0, line_height=1.05)
DISPLAY_MD = TextStyle(40, 700, tracking=-1.0, line_height=1.1)
DISPLAY_SM = TextStyle(32, 700, tracking=-0.5, line_height=1.15)
HEADING = TextStyle(24, 600, tracking=0.0, line_height=1.3)
SUBHEADING = TextStyle(18, 600, tracking=0.0, line_height=1.4)
BODY_LG = TextStyle(16, 400, tracking=0.0, line_height=1.6)
BODY = TextStyle(14, 400, tracking=0.0, line_height=1.6)
BODY_SM = TextStyle(12, 400, tracking=0.0, line_height=1.6)
LABEL = TextStyle(11, 500, tracking=0.5, line_height=1.4, uppercase=True)
MONO_LG = TextStyle(18, 400, font=FONT_MONO)
MONO_MD = TextStyle(14, 400, font=FONT_MONO)
MONO_SM = TextStyle(12, 400, font=FONT_MONO)


def scale_size(size: float, comp_height: int) -> float:
    """Scale a token size value from 1080p to the target resolution.

    Args:
        size: Size in px at 1080p.
        comp_height: Actual composition height in pixels.

    Returns:
        Scaled size in px.
    """
    return size * (comp_height / 1080)


# ── Spacing & Geometry ──────────────────────────────────────────────────

BASE_UNIT = 8

SPACE_1 = BASE_UNIT  # 8px
SPACE_2 = BASE_UNIT * 2  # 16px
SPACE_3 = BASE_UNIT * 3  # 24px
SPACE_4 = BASE_UNIT * 4  # 32px
SPACE_5 = BASE_UNIT * 5  # 40px
SPACE_6 = BASE_UNIT * 6  # 48px
SPACE_8 = BASE_UNIT * 8  # 64px
SPACE_10 = BASE_UNIT * 10  # 80px
SPACE_12 = BASE_UNIT * 12  # 96px
SPACE_16 = BASE_UNIT * 16  # 128px

RADIUS_SM = 4.0
RADIUS_MD = 8.0
RADIUS_LG = 12.0
RADIUS_XL = 16.0
RADIUS_FULL = 9999.0

BORDER_THIN = 1.0
BORDER_BASE = 1.5
BORDER_THICK = 2.0

SAFE_H = 80.0  # left/right safe zone at 1920px
SAFE_V = 60.0  # top/bottom safe zone at 1080px


def safe_h(comp_width: int) -> float:
    """Get horizontal safe zone scaled to composition width.

    Args:
        comp_width: Composition width in pixels.

    Returns:
        Safe zone padding in pixels.
    """
    return SAFE_H * (comp_width / 1920)


def safe_v(comp_height: int) -> float:
    """Get vertical safe zone scaled to composition height.

    Args:
        comp_height: Composition height in pixels.

    Returns:
        Safe zone padding in pixels.
    """
    return SAFE_V * (comp_height / 1080)


# ── Shadow & Elevation ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ShadowConfig:
    """Shadow configuration for elevation effects.

    Args:
        blur_radius: Gaussian blur radius in pixels.
        offset_x: Horizontal offset in pixels.
        offset_y: Vertical offset in pixels.
        color_r: Red component (0-1).
        color_g: Green component (0-1).
        color_b: Blue component (0-1).
        color_a: Alpha component (0-1).
    """

    blur_radius: float
    offset_x: float
    offset_y: float
    color_r: float = 0.0
    color_g: float = 0.0
    color_b: float = 0.0
    color_a: float = 0.3


SHADOW_XS = ShadowConfig(4, 0, 2, color_a=0.25)
SHADOW_SM = ShadowConfig(8, 0, 4, color_a=0.30)
SHADOW_MD = ShadowConfig(16, 0, 8, color_a=0.35)
SHADOW_LG = ShadowConfig(24, 0, 12, color_a=0.40)
SHADOW_XL = ShadowConfig(40, 0, 20, color_a=0.45)


def glow_sm(accent: Color | None = None) -> ShadowConfig:
    """Small accent-colored glow.

    Args:
        accent: Accent color. Uses theme accent if None.

    Returns:
        ShadowConfig for a small glow effect.
    """
    if accent is None:
        accent = get_theme().accent
    return ShadowConfig(12, 0, 0, accent.r, accent.g, accent.b, 0.3)


def glow_md(accent: Color | None = None) -> ShadowConfig:
    """Medium accent-colored glow.

    Args:
        accent: Accent color. Uses theme accent if None.

    Returns:
        ShadowConfig for a medium glow effect.
    """
    if accent is None:
        accent = get_theme().accent
    return ShadowConfig(24, 0, 0, accent.r, accent.g, accent.b, 0.3)
