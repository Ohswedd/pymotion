"""Tests for variable font loading with full axis support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pymotion.text.renderer import FontLoader


class TestVariableFontAxes:
    """Tests for FontLoader.load_variable with extended axis support."""

    def test_weight_axis(self) -> None:
        """Weight axis is passed through."""
        loader = FontLoader()
        with (
            patch.object(loader, "_resolve_font_path") as mock_path,
            patch.object(loader, "_load_face") as mock_face,
            patch.object(loader, "_apply_variation_axes") as mock_axes,
        ):
            mock_path.return_value = MagicMock()
            mock_face.return_value = MagicMock()
            loader.load_variable("TestFont", 24.0, weight=700)
            mock_axes.assert_called_once()
            axes_arg = mock_axes.call_args[0][1]
            assert axes_arg["wght"] == 700

    def test_italic_axis(self) -> None:
        """Italic axis is passed through."""
        loader = FontLoader()
        with (
            patch.object(loader, "_resolve_font_path") as mock_path,
            patch.object(loader, "_load_face") as mock_face,
            patch.object(loader, "_apply_variation_axes") as mock_axes,
        ):
            mock_path.return_value = MagicMock()
            mock_face.return_value = MagicMock()
            loader.load_variable("TestFont", 24.0, italic=1.0)
            axes_arg = mock_axes.call_args[0][1]
            assert axes_arg["ital"] == 1.0

    def test_optical_size_axis(self) -> None:
        """Optical size axis is passed through."""
        loader = FontLoader()
        with (
            patch.object(loader, "_resolve_font_path") as mock_path,
            patch.object(loader, "_load_face") as mock_face,
            patch.object(loader, "_apply_variation_axes") as mock_axes,
        ):
            mock_path.return_value = MagicMock()
            mock_face.return_value = MagicMock()
            loader.load_variable("TestFont", 24.0, optical_size=12.0)
            axes_arg = mock_axes.call_args[0][1]
            assert axes_arg["opsz"] == 12.0

    def test_custom_axes(self) -> None:
        """Custom axes dict is merged with named axes."""
        loader = FontLoader()
        with (
            patch.object(loader, "_resolve_font_path") as mock_path,
            patch.object(loader, "_load_face") as mock_face,
            patch.object(loader, "_apply_variation_axes") as mock_axes,
        ):
            mock_path.return_value = MagicMock()
            mock_face.return_value = MagicMock()
            loader.load_variable("TestFont", 24.0, weight=400, axes={"GRAD": 50.0, "XTRA": 420.0})
            axes_arg = mock_axes.call_args[0][1]
            assert axes_arg["wght"] == 400
            assert axes_arg["GRAD"] == 50.0
            assert axes_arg["XTRA"] == 420.0

    def test_all_standard_axes(self) -> None:
        """All 5 standard axes passed simultaneously."""
        loader = FontLoader()
        with (
            patch.object(loader, "_resolve_font_path") as mock_path,
            patch.object(loader, "_load_face") as mock_face,
            patch.object(loader, "_apply_variation_axes") as mock_axes,
        ):
            mock_path.return_value = MagicMock()
            mock_face.return_value = MagicMock()
            loader.load_variable(
                "TestFont",
                24.0,
                weight=700,
                width=100,
                slant=-12.0,
                italic=1.0,
                optical_size=24.0,
            )
            axes_arg = mock_axes.call_args[0][1]
            assert axes_arg == {
                "wght": 700,
                "wdth": 100,
                "slnt": -12.0,
                "ital": 1.0,
                "opsz": 24.0,
            }

    def test_caching(self) -> None:
        """Same parameters return cached face."""
        loader = FontLoader()
        with (
            patch.object(loader, "_resolve_font_path") as mock_path,
            patch.object(loader, "_load_face") as mock_face,
            patch.object(loader, "_apply_variation_axes"),
        ):
            mock_path.return_value = MagicMock()
            sentinel = MagicMock()
            mock_face.return_value = sentinel
            f1 = loader.load_variable("TestFont", 24.0, weight=700)
            f2 = loader.load_variable("TestFont", 24.0, weight=700)
            assert f1 is f2
            assert mock_face.call_count == 1
