"""Unit tests for pymotion.render.compositor — alpha compositing and blending."""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import BlendMode
from pymotion.render.compositor import composite_layers


class TestCompositor:
    """Test frame compositing operations."""

    def _make_solid(self, h: int, w: int, b: int, g: int, r: int, a: int = 255) -> np.ndarray:
        """Create a solid BGRA frame."""
        frame = np.zeros((h, w, 4), dtype=np.uint8)
        frame[:, :, 0] = b
        frame[:, :, 1] = g
        frame[:, :, 2] = r
        frame[:, :, 3] = a
        return frame

    def test_no_layers(self) -> None:
        bg = self._make_solid(10, 10, 0, 0, 0, 255)
        result = composite_layers(bg, [])
        np.testing.assert_array_equal(result, bg)

    def test_normal_blend_opaque(self) -> None:
        bg = self._make_solid(10, 10, 0, 0, 0, 255)
        layer = self._make_solid(10, 10, 0, 0, 255, 255)  # Red
        result = composite_layers(bg, [(layer, BlendMode.NORMAL, 1.0)])
        # Should be fully red
        assert result[5, 5, 2] == 255  # R
        assert result[5, 5, 3] == 255  # A

    def test_normal_blend_half_opacity(self) -> None:
        bg = self._make_solid(10, 10, 0, 0, 0, 255)  # Black
        layer = self._make_solid(10, 10, 0, 0, 255, 255)  # Red
        result = composite_layers(bg, [(layer, BlendMode.NORMAL, 0.5)])
        # R should be approximately half
        r_val = result[5, 5, 2]
        assert 120 <= r_val <= 135, f"Expected ~128, got {r_val}"

    def test_add_blend(self) -> None:
        bg = self._make_solid(10, 10, 0, 0, 100, 255)
        layer = self._make_solid(10, 10, 0, 0, 100, 255)
        result = composite_layers(bg, [(layer, BlendMode.ADD, 1.0)])
        # Should add: 100 + 100 = 200
        r_val = result[5, 5, 2]
        assert 195 <= r_val <= 205, f"Expected ~200, got {r_val}"

    def test_multiply_blend(self) -> None:
        bg = self._make_solid(10, 10, 0, 0, 255, 255)
        layer = self._make_solid(10, 10, 0, 0, 128, 255)
        result = composite_layers(bg, [(layer, BlendMode.MULTIPLY, 1.0)])
        # multiply: 255 * 128 / 255 = 128
        r_val = result[5, 5, 2]
        assert 125 <= r_val <= 131, f"Expected ~128, got {r_val}"

    def test_transparent_layer(self) -> None:
        bg = self._make_solid(10, 10, 255, 0, 0, 255)  # Blue
        layer = self._make_solid(10, 10, 0, 0, 255, 0)  # Red, fully transparent
        result = composite_layers(bg, [(layer, BlendMode.NORMAL, 1.0)])
        # Background should show through
        assert result[5, 5, 0] == 255  # B

    def test_multiple_layers(self) -> None:
        bg = self._make_solid(10, 10, 0, 0, 0, 255)
        layer1 = self._make_solid(10, 10, 255, 0, 0, 255)
        layer2 = self._make_solid(10, 10, 0, 255, 0, 128)
        result = composite_layers(
            bg,
            [
                (layer1, BlendMode.NORMAL, 1.0),
                (layer2, BlendMode.NORMAL, 1.0),
            ],
        )
        # Should have some green and some blue
        assert result[5, 5, 3] == 255  # Fully opaque output
