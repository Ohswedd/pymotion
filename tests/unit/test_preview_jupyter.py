"""Tests for Jupyter integration in preview/server.py."""

from __future__ import annotations

import numpy as np

from pymotion.composition import Composition
from pymotion.preview.server import export_frame_inline


class TestExportFrameInline:
    """Tests for export_frame_inline."""

    def test_returns_pil_image(self) -> None:
        """Returns a PIL Image in RGBA mode."""
        from PIL import Image

        comp = Composition(64, 48, fps=30, duration=10)
        img = export_frame_inline(comp, frame=0)
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"
        assert img.size == (64, 48)

    def test_scaled_output(self) -> None:
        """Scale=0.5 halves the dimensions."""
        from PIL import Image

        comp = Composition(64, 48, fps=30, duration=10)
        img = export_frame_inline(comp, frame=0, scale=0.5)
        assert isinstance(img, Image.Image)
        assert img.size == (32, 24)

    def test_frame_has_content(self) -> None:
        """Exported frame contains non-zero pixel data."""
        comp = Composition(64, 48, fps=30, duration=10, background="#FF0000")
        img = export_frame_inline(comp, frame=0)
        arr = np.array(img)
        assert np.any(arr[:, :, :3] > 0)
