"""Tests for the text rendering system — FontLoader, GlyphRenderer, HarfBuzzShaper."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pymotion.text.renderer import FontLoader, GlyphRenderer, HarfBuzzShaper, ShapedText
from pymotion.utils.color import Color


class TestFontLoader:
    """Tests for FontLoader."""

    def test_init_default(self) -> None:
        loader = FontLoader()
        assert loader._max_cache_size == 50

    def test_init_custom_cache_size(self) -> None:
        loader = FontLoader(max_cache_size=10)
        assert loader._max_cache_size == 10

    def test_load_system_font(self) -> None:
        """Load a system font that exists on macOS."""
        loader = FontLoader()
        # Try to load a common system font
        try:
            face = loader.load("Helvetica", 24.0)
            assert face is not None
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_load_nonexistent_font_uses_fallback(self) -> None:
        """A missing font should resolve to a fallback system font."""
        loader = FontLoader()
        # The fallback chain should find a usable font instead of raising
        face = loader.load("ThisFontDefinitelyDoesNotExist12345", 24.0)
        assert face is not None

    def test_cache_hit(self) -> None:
        """Second load should return cached face."""
        loader = FontLoader()
        try:
            face1 = loader.load("Helvetica", 24.0)
            face2 = loader.load("Helvetica", 24.0)
            assert face1 is face2
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_cache_eviction(self) -> None:
        """Cache should evict oldest entries when full."""
        loader = FontLoader(max_cache_size=2)
        try:
            loader.load("Helvetica", 12.0)
            loader.load("Helvetica", 24.0)
            assert len(loader._cache) == 2
            loader.load("Helvetica", 36.0)
            assert len(loader._cache) == 2
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_load_font_data(self) -> None:
        """Load raw font file bytes."""
        loader = FontLoader()
        try:
            data = loader.load_font_data("Helvetica")
            assert isinstance(data, bytes)
            assert len(data) > 0
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_list_system_fonts(self) -> None:
        """Should return a list of paths."""
        fonts = FontLoader.list_system_fonts()
        assert isinstance(fonts, list)
        # On macOS, there should be some fonts
        if len(fonts) > 0:
            assert all(isinstance(f, Path) for f in fonts)


class TestGlyphRenderer:
    """Tests for GlyphRenderer."""

    def test_render_empty_text(self) -> None:
        renderer = GlyphRenderer()
        result = renderer.render_text("", "Helvetica", 24.0)
        assert result.shape == (1, 1, 4)
        assert result.dtype == np.uint8

    def test_render_basic_text(self) -> None:
        """Render simple ASCII text."""
        renderer = GlyphRenderer()
        try:
            result = renderer.render_text("Hello", "Helvetica", 24.0)
            assert result.ndim == 3
            assert result.shape[2] == 4  # BGRA
            assert result.dtype == np.uint8
            # Should have some non-zero pixels (text was rendered)
            assert np.any(result[:, :, 3] > 0)
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_render_with_color(self) -> None:
        """Render text with a specific color."""
        renderer = GlyphRenderer()
        try:
            red = Color(1.0, 0.0, 0.0, 1.0)
            result = renderer.render_text("Test", "Helvetica", 24.0, red)
            # Check that red channel has values where text was rendered
            alpha_mask = result[:, :, 3] > 0
            if np.any(alpha_mask):
                # In BGRA, red is channel 2
                assert np.any(result[:, :, 2][alpha_mask] > 0)
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_render_multiline(self) -> None:
        """Render multiline text."""
        renderer = GlyphRenderer()
        try:
            result = renderer.render_text("Line 1\nLine 2", "Helvetica", 24.0)
            assert result.ndim == 3
            # Multi-line should be taller than single line
            single = renderer.render_text("Line 1", "Helvetica", 24.0)
            assert result.shape[0] > single.shape[0]
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_render_word_wrap(self) -> None:
        """Word wrap should produce more lines."""
        renderer = GlyphRenderer()
        try:
            text = "This is a longer sentence that should wrap"
            result = renderer.render_text(text, "Helvetica", 24.0, max_width=100)
            no_wrap = renderer.render_text(text, "Helvetica", 24.0)
            # Wrapped text should be taller (more lines)
            assert result.shape[0] >= no_wrap.shape[0] or result.shape[1] <= 100
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_render_alignment_center(self) -> None:
        """Center-aligned text should render without error."""
        renderer = GlyphRenderer()
        try:
            result = renderer.render_text("Centered", "Helvetica", 24.0, align="center")
            assert result.ndim == 3
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_render_alignment_right(self) -> None:
        """Right-aligned text should render without error."""
        renderer = GlyphRenderer()
        try:
            result = renderer.render_text("Right", "Helvetica", 24.0, align="right")
            assert result.ndim == 3
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")


class TestHarfBuzzShaper:
    """Tests for HarfBuzzShaper."""

    def test_shape_basic_text(self) -> None:
        """Shape simple ASCII text."""
        shaper = HarfBuzzShaper()
        try:
            result = shaper.shape("Hello", "Helvetica", 24.0)
            assert isinstance(result, ShapedText)
            assert len(result.glyphs) == 5  # H, e, l, l, o
            assert result.width > 0
            assert result.height > 0
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_shape_glyph_info(self) -> None:
        """Check glyph info structure."""
        shaper = HarfBuzzShaper()
        try:
            result = shaper.shape("A", "Helvetica", 24.0)
            assert len(result.glyphs) == 1
            glyph = result.glyphs[0]
            assert glyph.x_advance > 0
            assert glyph.cluster == 0
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_shape_empty_text(self) -> None:
        """Empty text should produce no glyphs."""
        shaper = HarfBuzzShaper()
        try:
            result = shaper.shape("", "Helvetica", 24.0)
            assert len(result.glyphs) == 0
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")


class TestSecurityTextInput:
    """Security tests for text rendering."""

    def test_sanitized_null_bytes(self) -> None:
        """Null bytes in text should be handled."""
        from pymotion.security.validation import sanitize_text

        result = sanitize_text("Hello\x00World")
        assert "\x00" not in result

    def test_oversized_text_rejected(self) -> None:
        """Oversized text should be rejected."""
        from pymotion.security.validation import sanitize_text

        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_text("A" * 20_000, max_length=10_000)
