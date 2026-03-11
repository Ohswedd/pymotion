"""Tests for pymotion.design.tokens — color palettes, themes, typography, spacing."""

from __future__ import annotations

import pytest

from pymotion.design.tokens import (
    ACCENT,
    BASE_UNIT,
    BODY,
    BODY_LG,
    BODY_SM,
    BORDER_BASE,
    BORDER_THICK,
    BORDER_THIN,
    CHART_COLORS,
    DISPLAY_2XL,
    DISPLAY_LG,
    DISPLAY_MD,
    DISPLAY_SM,
    DISPLAY_XL,
    FONT_MONO,
    FONT_PRIMARY,
    HEADING,
    LABEL,
    MONO_LG,
    MONO_MD,
    MONO_SM,
    NEUTRAL,
    RADIUS_FULL,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RADIUS_XL,
    SAFE_H,
    SAFE_V,
    SHADOW_LG,
    SHADOW_MD,
    SHADOW_SM,
    SHADOW_XL,
    SHADOW_XS,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    STATUS,
    SUBHEADING,
    Theme,
    get_theme,
    glow_md,
    glow_sm,
    reset_theme,
    safe_h,
    safe_v,
    scale_size,
    set_theme,
)


class TestNeutralPalette:
    def test_neutral_has_all_shades(self) -> None:
        assert NEUTRAL.n950 is not None
        assert NEUTRAL.n50 is not None
        assert NEUTRAL.n500 is not None

    def test_neutral_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            NEUTRAL.n950 = NEUTRAL.n50  # type: ignore[misc]


class TestAccentPalette:
    def test_accent_has_all_shades(self) -> None:
        assert ACCENT.a600 is not None
        assert ACCENT.a500 is not None
        assert ACCENT.a400 is not None
        assert ACCENT.a300 is not None
        assert ACCENT.glow is not None

    def test_glow_has_low_alpha(self) -> None:
        assert ACCENT.glow.a < 0.2


class TestStatusPalette:
    def test_status_colors(self) -> None:
        assert STATUS.success is not None
        assert STATUS.warning is not None
        assert STATUS.error is not None


class TestChartColors:
    def test_chart_has_8_colors(self) -> None:
        assert len(CHART_COLORS) == 8

    def test_chart_colors_are_distinct(self) -> None:
        hex_set = {(c.r, c.g, c.b) for c in CHART_COLORS}
        assert len(hex_set) == 8


class TestThemeSystem:
    def setup_method(self) -> None:
        reset_theme()

    def test_default_theme_is_dark(self) -> None:
        t = get_theme()
        assert t.name == "dark"

    def test_get_named_theme(self) -> None:
        t = get_theme("midnight")
        assert t.name == "midnight"

    def test_set_theme(self) -> None:
        set_theme("light")
        t = get_theme()
        assert t.name == "light"

    def test_set_invalid_theme(self) -> None:
        with pytest.raises(ValueError, match="Unknown theme"):
            set_theme("invalid")

    def test_get_invalid_theme(self) -> None:
        with pytest.raises(ValueError, match="Unknown theme"):
            get_theme("invalid")

    def test_all_themes_exist(self) -> None:
        for name in ("dark", "light", "midnight", "warm"):
            t = get_theme(name)
            assert isinstance(t, Theme)
            assert t.background is not None
            assert t.surface is not None
            assert t.border is not None
            assert t.text is not None
            assert t.muted is not None
            assert t.accent is not None

    def test_reset_theme(self) -> None:
        set_theme("warm")
        reset_theme()
        assert get_theme().name == "dark"


class TestTypographyScale:
    def test_display_sizes_decrease(self) -> None:
        assert DISPLAY_2XL.size > DISPLAY_XL.size > DISPLAY_LG.size
        assert DISPLAY_LG.size > DISPLAY_MD.size > DISPLAY_SM.size

    def test_body_sizes_decrease(self) -> None:
        assert BODY_LG.size > BODY.size > BODY_SM.size

    def test_heading_chain(self) -> None:
        assert HEADING.size > SUBHEADING.size > BODY_LG.size

    def test_label_is_uppercase(self) -> None:
        assert LABEL.uppercase is True

    def test_mono_uses_mono_font(self) -> None:
        assert MONO_LG.font == FONT_MONO
        assert MONO_MD.font == FONT_MONO
        assert MONO_SM.font == FONT_MONO

    def test_body_uses_primary_font(self) -> None:
        assert BODY.font == FONT_PRIMARY

    def test_display_weights_are_heavy(self) -> None:
        assert DISPLAY_2XL.weight >= 700
        assert DISPLAY_XL.weight >= 700

    def test_scale_size_1080(self) -> None:
        assert scale_size(56, 1080) == 56.0

    def test_scale_size_720(self) -> None:
        assert abs(scale_size(56, 720) - 56 * 720 / 1080) < 0.01

    def test_scale_size_4k(self) -> None:
        assert abs(scale_size(56, 2160) - 112.0) < 0.01


class TestSpacing:
    def test_base_unit(self) -> None:
        assert BASE_UNIT == 8

    def test_space_multiples(self) -> None:
        assert SPACE_1 == 8
        assert SPACE_2 == 16
        assert SPACE_3 == 24
        assert SPACE_4 == 32

    def test_radius_values(self) -> None:
        assert RADIUS_SM < RADIUS_MD < RADIUS_LG < RADIUS_XL < RADIUS_FULL

    def test_border_widths(self) -> None:
        assert BORDER_THIN < BORDER_BASE < BORDER_THICK

    def test_safe_h_at_1920(self) -> None:
        assert safe_h(1920) == SAFE_H

    def test_safe_v_at_1080(self) -> None:
        assert safe_v(1080) == SAFE_V

    def test_safe_h_scales(self) -> None:
        assert safe_h(3840) == SAFE_H * 2


class TestShadows:
    def test_shadow_blur_increases(self) -> None:
        assert SHADOW_XS.blur_radius < SHADOW_SM.blur_radius
        assert SHADOW_SM.blur_radius < SHADOW_MD.blur_radius
        assert SHADOW_MD.blur_radius < SHADOW_LG.blur_radius
        assert SHADOW_LG.blur_radius < SHADOW_XL.blur_radius

    def test_shadow_alpha_increases(self) -> None:
        assert SHADOW_XS.color_a < SHADOW_XL.color_a

    def test_glow_sm_uses_accent(self) -> None:
        g = glow_sm()
        t = get_theme()
        assert g.color_r == t.accent.r

    def test_glow_md_uses_accent(self) -> None:
        g = glow_md()
        assert g.blur_radius == 24

    def test_shadow_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            SHADOW_SM.blur_radius = 999  # type: ignore[misc]
