"""Tests for text/renderer.py — FontLoader variable font support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pymotion.text.renderer import FontLoader


class TestFontLoaderVariable:
    """Test variable font loading."""

    def test_load_variable_caches(self) -> None:
        loader = FontLoader()
        mock_face = MagicMock()
        mock_face.size.ascender = 16 << 6
        mock_face.size.descender = -(4 << 6)

        with patch.object(loader, "_resolve_font_path") as mock_resolve:
            mock_resolve.return_value = MagicMock()
            with patch.object(loader, "_load_face", return_value=mock_face):
                with patch.object(loader, "_apply_variation_axes"):
                    face1 = loader.load_variable("test", 24, weight=700)
                    face2 = loader.load_variable("test", 24, weight=700)
                    assert face1 is face2

    def test_load_variable_different_weights_cached_separately(self) -> None:
        loader = FontLoader()
        mock_face_400 = MagicMock()
        mock_face_700 = MagicMock()

        call_count = 0

        def make_face(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return mock_face_400 if call_count == 1 else mock_face_700

        with patch.object(loader, "_resolve_font_path") as mock_resolve:
            mock_resolve.return_value = MagicMock()
            with patch.object(loader, "_load_face", side_effect=make_face):
                with patch.object(loader, "_apply_variation_axes"):
                    f1 = loader.load_variable("test", 24, weight=400)
                    f2 = loader.load_variable("test", 24, weight=700)
                    assert f1 is not f2

    def test_apply_variation_axes_no_axes(self) -> None:
        FontLoader._apply_variation_axes(MagicMock(), {})

    def test_apply_variation_axes_no_support(self) -> None:
        # Object with no set_var_design_coordinates attribute
        face = MagicMock(spec=["some_method"])
        FontLoader._apply_variation_axes(face, {"wght": 700})

    def test_load_variable_lru_eviction(self) -> None:
        loader = FontLoader(max_cache_size=2)

        with patch.object(loader, "_resolve_font_path") as mock_resolve:
            mock_resolve.return_value = MagicMock()
            with patch.object(loader, "_load_face", return_value=MagicMock()):
                with patch.object(loader, "_apply_variation_axes"):
                    loader.load_variable("a", 24, weight=400)
                    loader.load_variable("b", 24, weight=400)
                    loader.load_variable("c", 24, weight=400)
                    # First entry should be evicted
                    assert len(loader._cache) == 2
