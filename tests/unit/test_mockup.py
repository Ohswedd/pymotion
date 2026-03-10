"""Tests for screen and device mockup clips."""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip
from pymotion.clip.mockup import BrowserMockup, DesktopMockup, PhoneMockup
from pymotion.utils.color import Color


def _ctx(
    frame: int = 0,
    w: int = 1920,
    h: int = 1080,
    fps: int = 30,
    duration: int = 90,
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


def _content_clip() -> ColorClip:
    """Create a simple content clip for testing."""
    clip = ColorClip(color=Color.parse("#2563EB"))
    clip.set_duration(90)
    return clip


# ── BrowserMockup ───────────────────────────────────────────────────────


class TestBrowserMockup:
    """BrowserMockup tests."""

    def test_render_no_content(self) -> None:
        clip = BrowserMockup()
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)
        assert frame.dtype == np.uint8

    def test_render_with_content(self) -> None:
        clip = BrowserMockup(content_clip=_content_clip())
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_themes(self, theme: str) -> None:
        clip = BrowserMockup(mockup_theme=theme)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_custom_url(self) -> None:
        clip = BrowserMockup(url_text="https://pymotion.dev")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_animate_in(self) -> None:
        clip = BrowserMockup(animate_in_frames=15)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f20 = clip.render_frame(_ctx(frame=20))
        assert not np.array_equal(f0, f20)

    def test_animate_out(self) -> None:
        clip = BrowserMockup(animate_out_frames=15)
        clip.set_duration(60)
        f30 = clip.render_frame(_ctx(frame=30))
        f58 = clip.render_frame(_ctx(frame=58))
        assert not np.array_equal(f30, f58)

    def test_unknown_theme_fallback(self) -> None:
        clip = BrowserMockup(mockup_theme="unknown")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "BrowserMockup")


# ── PhoneMockup ─────────────────────────────────────────────────────────


class TestPhoneMockup:
    """PhoneMockup tests."""

    def test_render_no_content(self) -> None:
        clip = PhoneMockup()
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_render_with_content(self) -> None:
        clip = PhoneMockup(content_clip=_content_clip())
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize("model", ["flat", "notch", "dynamic_island"])
    def test_all_models(self, model: str) -> None:
        clip = PhoneMockup(model=model)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_custom_bezel_color(self) -> None:
        clip = PhoneMockup(bezel_color=Color.parse("#FF0000"))
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_animate_in(self) -> None:
        clip = PhoneMockup(animate_in_frames=15)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f20 = clip.render_frame(_ctx(frame=20))
        assert not np.array_equal(f0, f20)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "PhoneMockup")


# ── DesktopMockup ───────────────────────────────────────────────────────


class TestDesktopMockup:
    """DesktopMockup tests."""

    def test_render_no_content(self) -> None:
        clip = DesktopMockup()
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    def test_render_with_content(self) -> None:
        clip = DesktopMockup(content_clip=_content_clip())
        clip.set_duration(60)
        frame = clip.render_frame(_ctx(frame=30))
        assert frame.shape == (1080, 1920, 4)

    @pytest.mark.parametrize("os_theme", ["macos", "windows", "minimal"])
    def test_all_themes(self, os_theme: str) -> None:
        clip = DesktopMockup(os_theme=os_theme)
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_custom_window_title(self) -> None:
        clip = DesktopMockup(window_title="My Application")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_animate_in(self) -> None:
        clip = DesktopMockup(animate_in_frames=15)
        clip.set_duration(60)
        f0 = clip.render_frame(_ctx(frame=0))
        f20 = clip.render_frame(_ctx(frame=20))
        assert not np.array_equal(f0, f20)

    def test_animate_out(self) -> None:
        clip = DesktopMockup(animate_out_frames=15)
        clip.set_duration(60)
        f30 = clip.render_frame(_ctx(frame=30))
        f58 = clip.render_frame(_ctx(frame=58))
        assert not np.array_equal(f30, f58)

    def test_unknown_theme_fallback(self) -> None:
        clip = DesktopMockup(os_theme="linux")
        clip.set_duration(30)
        frame = clip.render_frame(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)

    def test_import_from_pymotion(self) -> None:
        import pymotion as pm

        assert hasattr(pm, "DesktopMockup")


# ── Cross-cutting ───────────────────────────────────────────────────────


class TestMockupClipBehavior:
    """All mockups behave as proper Clips."""

    def test_browser_set_duration(self) -> None:
        clip = BrowserMockup()
        clip.set_duration(120)
        assert clip.duration == 120

    def test_phone_set_position(self) -> None:
        clip = PhoneMockup().set_position(100, 200)
        assert clip._position.x == 100

    def test_desktop_render_with_effects(self) -> None:
        clip = DesktopMockup()
        clip.set_duration(30)
        frame = clip.render_with_effects(_ctx(frame=15))
        assert frame.shape == (1080, 1920, 4)
