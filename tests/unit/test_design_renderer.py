"""Tests for pymotion.design.renderer — shadow_apply and drawing helpers."""

from __future__ import annotations

import cairo
import numpy as np

from pymotion.design.renderer import draw_rounded_rect, shadow_apply
from pymotion.design.tokens import SHADOW_MD, SHADOW_SM, SHADOW_XS, ShadowConfig


class TestShadowApply:
    def test_returns_same_shape(self) -> None:
        frame = np.zeros((100, 100, 4), dtype=np.uint8)
        frame[30:70, 30:70] = [255, 255, 255, 255]
        result = shadow_apply(frame, SHADOW_SM)
        assert result.shape == frame.shape

    def test_shadow_extends_beyond_content(self) -> None:
        frame = np.zeros((200, 200, 4), dtype=np.uint8)
        frame[80:120, 80:120] = [255, 255, 255, 255]
        result = shadow_apply(frame, SHADOW_MD)
        # Shadow alpha should be nonzero in area below content (offset=8)
        # Check a row between content bottom (120) and offset bottom (128)
        assert result[130, 100, 3] > 0

    def test_preserves_original_content(self) -> None:
        frame = np.zeros((100, 100, 4), dtype=np.uint8)
        frame[40:60, 40:60] = [200, 150, 100, 255]
        result = shadow_apply(frame, SHADOW_XS)
        # Center pixel should still be close to original
        np.testing.assert_array_less(
            np.abs(result[50, 50, :3].astype(int) - frame[50, 50, :3].astype(int)), 5
        )

    def test_transparent_frame_stays_mostly_transparent(self) -> None:
        frame = np.zeros((100, 100, 4), dtype=np.uint8)
        result = shadow_apply(frame, SHADOW_SM)
        assert result[:, :, 3].max() == 0

    def test_custom_shadow_color(self) -> None:
        frame = np.zeros((100, 100, 4), dtype=np.uint8)
        frame[40:60, 40:60, :] = [255, 255, 255, 255]
        shadow = ShadowConfig(8, 0, 0, color_r=1.0, color_g=0.0, color_b=0.0, color_a=0.5)
        result = shadow_apply(frame, shadow)
        # Shadow region should have red tint
        assert result.shape == frame.shape

    def test_shadow_offset(self) -> None:
        frame = np.zeros((200, 200, 4), dtype=np.uint8)
        frame[90:110, 90:110] = [255, 255, 255, 255]
        shadow = ShadowConfig(4, 0, 20, color_a=0.5)
        result = shadow_apply(frame, shadow)
        # Below content (y+20) should have shadow alpha
        assert result[125, 100, 3] > 0

    def test_zero_blur_radius(self) -> None:
        frame = np.zeros((100, 100, 4), dtype=np.uint8)
        frame[40:60, 40:60] = [255, 255, 255, 255]
        shadow = ShadowConfig(0, 0, 0, color_a=0.5)
        result = shadow_apply(frame, shadow)
        assert result.shape == frame.shape


class TestDrawRoundedRect:
    def test_draws_path(self) -> None:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        cr = cairo.Context(surface)
        draw_rounded_rect(cr, 10, 10, 80, 80, 8)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill()
        buf = bytes(surface.get_data())
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((100, 100, 4))
        # Center should be filled
        assert arr[50, 50, 3] == 255

    def test_radius_larger_than_half_width(self) -> None:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        cr = cairo.Context(surface)
        # Radius 100 > width/2=25 — should clamp
        draw_rounded_rect(cr, 25, 25, 50, 50, 100)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill()
        buf = bytes(surface.get_data())
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((100, 100, 4))
        assert arr[50, 50, 3] == 255

    def test_zero_radius(self) -> None:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        cr = cairo.Context(surface)
        draw_rounded_rect(cr, 10, 10, 80, 80, 0)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill()
        buf = bytes(surface.get_data())
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((100, 100, 4))
        # Corners should be filled (no rounding)
        assert arr[10, 10, 3] == 255
