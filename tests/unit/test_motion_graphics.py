"""Tests for motion graphics components."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.motion_graphics import (
    CallToAction,
    Countdown,
    Divider,
    LogoReveal,
    LowerThird,
    QuoteCard,
    SocialHandle,
    TransitionTitle,
    Watermark,
)
from pymotion.utils.color import Color


def _ctx(
    frame: int = 0, w: int = 1920, h: int = 1080, fps: int = 30, duration: int = 90
) -> RenderContext:
    """Build a RenderContext for testing."""
    return RenderContext(
        frame=frame,
        fps=fps,
        resolution=Resolution(w, h),
        time_range=TimeRange(0, duration),
        local_frame=frame,
        progress=frame / duration if duration > 0 else 0.0,
    )


# ── LowerThird ──────────────────────────────────────────────────────────


class TestLowerThird:
    """LowerThird tests."""

    def test_render_basic(self) -> None:
        clip = LowerThird(name="John Doe", title="CEO")
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize(
        "style",
        ["modern", "clean", "bold", "minimal", "news", "gradient_bar", "corporate", "neon"],
    )
    def test_all_styles(self, style: str) -> None:
        clip = LowerThird(name="Test", title="Role", style=style)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_invalid_style_raises(self) -> None:
        clip = LowerThird(name="Test", style="nonexistent")
        clip.set_duration(30)
        with pytest.raises(ValueError, match="Unknown lower third style"):
            clip.render_frame(_ctx(frame=0))

    def test_animation_in(self) -> None:
        clip = LowerThird(name="Test", title="Role", animate_in=15)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f15 = clip.render_frame(_ctx(frame=15))
        assert not np.array_equal(f0, f15)

    def test_animation_out(self) -> None:
        clip = LowerThird(name="Test", title="Role", animate_out=15)
        clip.set_duration(60)
        f45 = clip.render_frame(_ctx(frame=45))
        f58 = clip.render_frame(_ctx(frame=58))
        assert not np.array_equal(f45, f58)

    def test_empty_text(self) -> None:
        clip = LowerThird(name="", title="")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "LowerThird")


# ── LogoReveal ──────────────────────────────────────────────────────────


class TestLogoReveal:
    """LogoReveal tests."""

    @pytest.mark.parametrize("style", ["fade", "slice", "grow", "glitch", "draw", "shatter"])
    def test_all_styles(self, style: str) -> None:
        clip = LogoReveal(style=style, reveal_duration=30)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_invalid_style_raises(self) -> None:
        clip = LogoReveal(style="nonexistent")
        clip.set_duration(30)
        with pytest.raises(ValueError, match="Unknown logo reveal style"):
            clip.render_frame(_ctx(frame=0))

    def test_animation(self) -> None:
        clip = LogoReveal(style="fade", reveal_duration=30)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f29 = clip.render_frame(_ctx(frame=29))
        assert not np.array_equal(f0, f29)

    def test_after_animation(self) -> None:
        clip = LogoReveal(style="fade", reveal_duration=10)
        clip.set_duration(60)
        f30 = clip.render_frame(_ctx(frame=30))
        f50 = clip.render_frame(_ctx(frame=50))
        np.testing.assert_array_equal(f30, f50)

    def test_custom_color_and_size(self) -> None:
        clip = LogoReveal(
            logo_color=Color.parse("#FF0000"),
            logo_size=(300.0, 150.0),
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "LogoReveal")


# ── CallToAction ────────────────────────────────────────────────────────


class TestCallToAction:
    """CallToAction tests."""

    def test_render_basic(self) -> None:
        clip = CallToAction(text="Subscribe Now!")
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize("style", ["subscribe", "buy", "visit", "default"])
    def test_all_styles(self, style: str) -> None:
        clip = CallToAction(text="Click", style=style)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_with_sub_text(self) -> None:
        clip = CallToAction(text="Subscribe", sub_text="Don't miss out!")
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_animation(self) -> None:
        clip = CallToAction(text="Buy", animate_in=15)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f15 = clip.render_frame(_ctx(frame=15))
        assert not np.array_equal(f0, f15)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "CallToAction")


# ── SocialHandle ────────────────────────────────────────────────────────


class TestSocialHandle:
    """SocialHandle tests."""

    @pytest.mark.parametrize("platform", ["youtube", "instagram", "tiktok", "x", "linkedin"])
    def test_all_platforms(self, platform: str) -> None:
        clip = SocialHandle(platform=platform, handle="@testuser")
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_unknown_platform(self) -> None:
        clip = SocialHandle(platform="mastodon", handle="@test")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_animation(self) -> None:
        clip = SocialHandle(platform="youtube", handle="@test", animate_in=15)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f15 = clip.render_frame(_ctx(frame=15))
        assert not np.array_equal(f0, f15)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "SocialHandle")


# ── Countdown ───────────────────────────────────────────────────────────


class TestCountdown:
    """Countdown tests."""

    def test_render_basic(self) -> None:
        clip = Countdown(from_n=10, count_duration=300)
        clip.set_duration(300)
        frame = clip.render_frame(_ctx(frame=0, duration=300))
        assert frame.shape == (1080, 1920, 4)

    def test_numbers_style(self) -> None:
        clip = Countdown(from_n=5, count_duration=150, style="numbers")
        clip.set_duration(150)
        frame = clip.render_frame(_ctx(frame=75, duration=150))
        assert frame.shape == (1080, 1920, 4)

    def test_clock_style(self) -> None:
        clip = Countdown(from_n=120, count_duration=300, style="clock")
        clip.set_duration(300)
        frame = clip.render_frame(_ctx(frame=100, duration=300))
        assert frame.shape == (1080, 1920, 4)

    def test_at_end(self) -> None:
        clip = Countdown(from_n=5, count_duration=150)
        clip.set_duration(150)
        frame = clip.render_frame(_ctx(frame=149, duration=150))
        assert frame.shape == (1080, 1920, 4)

    def test_custom_color_size(self) -> None:
        clip = Countdown(
            from_n=3,
            count_duration=90,
            color=Color.parse("#FF0000"),
            size=200.0,
        )
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=45))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "Countdown")


# ── QuoteCard ───────────────────────────────────────────────────────────


class TestQuoteCard:
    """QuoteCard tests."""

    def test_render_basic(self) -> None:
        clip = QuoteCard(
            text="The only way to do great work is to love what you do.",
            attribution="— Steve Jobs",
        )
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=45))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize("style", ["elegant", "light", "minimal", "default"])
    def test_all_styles(self, style: str) -> None:
        clip = QuoteCard(text="Test quote", style=style)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_no_attribution(self) -> None:
        clip = QuoteCard(text="No author")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_long_text_wraps(self) -> None:
        clip = QuoteCard(
            text="This is a very long quote that should be wrapped across "
            "multiple lines to fit within the card boundaries properly."
        )
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_animation(self) -> None:
        clip = QuoteCard(text="Test", animate_in=20)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f20 = clip.render_frame(_ctx(frame=20))
        assert not np.array_equal(f0, f20)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "QuoteCard")


# ── Divider ─────────────────────────────────────────────────────────────


class TestDivider:
    """Divider tests."""

    @pytest.mark.parametrize("style", ["line", "dashed", "dots", "gradient", "wave"])
    def test_all_styles_horizontal(self, style: str) -> None:
        clip = Divider(style=style, direction="horizontal")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_vertical(self) -> None:
        clip = Divider(direction="vertical")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_vertical_dashed(self) -> None:
        clip = Divider(style="dashed", direction="vertical")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_animation(self) -> None:
        clip = Divider(div_duration=20)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f19 = clip.render_frame(_ctx(frame=19))
        assert not np.array_equal(f0, f19)

    def test_custom_color_thickness(self) -> None:
        clip = Divider(color=Color.parse("#FF0000"), thickness=4.0)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "Divider")


# ── TransitionTitle ─────────────────────────────────────────────────────


class TestTransitionTitle:
    """TransitionTitle tests."""

    def test_render_basic(self) -> None:
        clip = TransitionTitle(text="Chapter 1")
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=45))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize("style", ["fade", "slide_up", "zoom", "split", "default"])
    def test_all_styles(self, style: str) -> None:
        clip = TransitionTitle(text="Title", style=style)
        clip.set_duration(90)
        frame = clip.render_frame(_ctx(frame=45))
        assert frame.shape == (1080, 1920, 4)

    def test_animation_in_out(self) -> None:
        clip = TransitionTitle(text="Test", animate_in=15, animate_out=15)
        clip.set_duration(90)
        f0 = clip.render_frame(_ctx(frame=0))
        f45 = clip.render_frame(_ctx(frame=45))
        f89 = clip.render_frame(_ctx(frame=89))
        assert not np.array_equal(f0, f45)
        assert not np.array_equal(f45, f89)

    def test_custom_font_size(self) -> None:
        clip = TransitionTitle(text="Big", font_size=96.0)
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "TransitionTitle")


# ── Watermark ───────────────────────────────────────────────────────────


class TestWatermark:
    """Watermark tests."""

    def test_render_basic(self) -> None:
        clip = Watermark(image_or_text="PyMotion")
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize(
        "position",
        ["top-left", "top-right", "bottom-left", "bottom-right", "center"],
    )
    def test_all_positions(self, position: str) -> None:
        clip = Watermark(image_or_text="WM", position=position)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_empty_text(self) -> None:
        clip = Watermark(image_or_text="")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (1080, 1920, 4)

    def test_custom_opacity(self) -> None:
        clip = Watermark(image_or_text="Brand", watermark_opacity=0.1)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_custom_color_size(self) -> None:
        clip = Watermark(
            image_or_text="Logo",
            color=Color.parse("#FF0000"),
            font_size=36.0,
        )
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_unknown_position_falls_back(self) -> None:
        clip = Watermark(image_or_text="Test", position="invalid")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=0))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "Watermark")
