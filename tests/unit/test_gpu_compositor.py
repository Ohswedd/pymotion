"""Tests for GPU-accelerated compositor (WGPU compute shaders).

Tests the GPUCompositor class and gpu_composite_layers function,
verifying that GPU compositing produces results matching the CPU
compositor within acceptable tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import BlendMode
from pymotion.config import PyMotionConfig, get_config, reset_config, set_config
from pymotion.render.compositor import composite_layers as cpu_composite
from pymotion.render.gpu_compositor import (
    GPUCompositor,
    get_gpu_compositor,
    gpu_composite_layers,
)

# Maximum allowed per-pixel difference between GPU and CPU results.
# Differences of 1-2 are expected due to float32 vs uint16 rounding.
_MAX_TOLERANCE = 2


def _make_frame(h: int, w: int, color: tuple[int, int, int, int] = (0, 0, 0, 255)) -> np.ndarray:
    """Create a solid BGRA frame."""
    frame = np.zeros((h, w, 4), dtype=np.uint8)
    frame[:, :, 0] = color[0]
    frame[:, :, 1] = color[1]
    frame[:, :, 2] = color[2]
    frame[:, :, 3] = color[3]
    return frame


def _random_frame(h: int, w: int, seed: int = 42) -> np.ndarray:
    """Create a random BGRA frame."""
    rng = np.random.RandomState(seed)
    return rng.randint(0, 256, (h, w, 4), dtype=np.uint8)


@pytest.fixture()
def gpu() -> GPUCompositor:
    """Get a GPUCompositor instance, skip if unavailable."""
    comp = GPUCompositor()
    if not comp.available:
        pytest.skip("WGPU GPU not available")
    return comp


class TestGPUCompositorAvailability:
    """Tests for GPU compositor availability and initialization."""

    def test_available_property(self) -> None:
        gpu = GPUCompositor()
        # Should return a bool without raising
        result = gpu.available
        assert isinstance(result, bool)

    def test_singleton_returns_same_instance(self) -> None:
        a = get_gpu_compositor()
        b = get_gpu_compositor()
        assert a is b

    def test_release_clears_state(self, gpu: GPUCompositor) -> None:
        gpu.release()
        assert gpu._device is None
        assert gpu._buffer_size == 0


class TestGPUCompositorBlendModes:
    """Tests for each blend mode matching CPU output."""

    @pytest.mark.parametrize(
        "blend_mode",
        [
            BlendMode.NORMAL,
            BlendMode.MULTIPLY,
            BlendMode.SCREEN,
            BlendMode.OVERLAY,
            BlendMode.ADD,
            BlendMode.SOFT_LIGHT,
            BlendMode.HARD_LIGHT,
            BlendMode.DIFFERENCE,
        ],
    )
    def test_blend_mode_matches_cpu(self, gpu: GPUCompositor, blend_mode: BlendMode) -> None:
        h, w = 64, 64
        bg = _random_frame(h, w, seed=42)
        bg[:, :, 3] = 255  # Opaque background
        layer = _random_frame(h, w, seed=123)

        gpu_result = gpu.composite_layers(bg.copy(), [(layer, blend_mode, 0.8)])
        cpu_result = cpu_composite(bg.copy(), [(layer, blend_mode, 0.8)])

        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE, (
            f"{blend_mode.value}: max pixel diff {diff.max()} > {_MAX_TOLERANCE}"
        )

    @pytest.mark.parametrize(
        "blend_mode",
        [
            BlendMode.NORMAL,
            BlendMode.MULTIPLY,
            BlendMode.SCREEN,
            BlendMode.ADD,
        ],
    )
    def test_blend_mode_with_semitransparent_bg(
        self, gpu: GPUCompositor, blend_mode: BlendMode
    ) -> None:
        """Test blend modes when background has partial transparency."""
        h, w = 32, 32
        bg = _random_frame(h, w, seed=55)
        bg[:, :, 3] = 180  # Semi-transparent
        layer = _random_frame(h, w, seed=77)

        gpu_result = gpu.composite_layers(bg.copy(), [(layer, blend_mode, 1.0)])
        cpu_result = cpu_composite(bg.copy(), [(layer, blend_mode, 1.0)])

        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE


class TestGPUCompositorEdgeCases:
    """Tests for edge cases in GPU compositing."""

    def test_empty_layers(self, gpu: GPUCompositor) -> None:
        bg = _make_frame(32, 32, (100, 150, 200, 255))
        result = gpu.composite_layers(bg.copy(), [])
        assert np.array_equal(result, bg)

    def test_zero_opacity_layer(self, gpu: GPUCompositor) -> None:
        bg = _make_frame(32, 32, (100, 150, 200, 255))
        layer = _make_frame(32, 32, (255, 0, 0, 255))
        result = gpu.composite_layers(bg.copy(), [(layer, BlendMode.NORMAL, 0.0)])
        assert np.array_equal(result, bg)

    def test_fully_transparent_layer(self, gpu: GPUCompositor) -> None:
        bg = _make_frame(32, 32, (100, 150, 200, 255))
        layer = _make_frame(32, 32, (255, 0, 0, 0))  # alpha=0
        result = gpu.composite_layers(bg.copy(), [(layer, BlendMode.NORMAL, 1.0)])
        # GPU skips pixels with alpha < 0.5, so result should be unchanged
        assert np.array_equal(result, bg)

    def test_fully_opaque_normal_overwrites(self, gpu: GPUCompositor) -> None:
        bg = _make_frame(32, 32, (100, 150, 200, 255))
        layer = _make_frame(32, 32, (10, 20, 30, 255))
        result = gpu.composite_layers(bg.copy(), [(layer, BlendMode.NORMAL, 1.0)])
        # Fully opaque normal layer at 100% opacity should overwrite
        diff = np.abs(result.astype(int) - layer.astype(int))
        assert diff.max() <= 1

    def test_multiple_layers(self, gpu: GPUCompositor) -> None:
        h, w = 48, 48
        bg = _random_frame(h, w, seed=1)
        bg[:, :, 3] = 255

        layers = [
            (_random_frame(h, w, seed=2), BlendMode.NORMAL, 0.5),
            (_random_frame(h, w, seed=3), BlendMode.SCREEN, 0.7),
            (_random_frame(h, w, seed=4), BlendMode.MULTIPLY, 1.0),
        ]

        gpu_result = gpu.composite_layers(bg.copy(), layers)
        cpu_result = cpu_composite(bg.copy(), layers)

        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= 3  # Multi-layer may accumulate 1 extra rounding error

    def test_opaque_layer_skips_below(self, gpu: GPUCompositor) -> None:
        """Topmost fully-opaque NORMAL layer should skip everything below."""
        h, w = 32, 32
        bg = _make_frame(h, w, (100, 100, 100, 255))
        bottom = _make_frame(h, w, (200, 200, 200, 255))
        top = _make_frame(h, w, (50, 50, 50, 255))

        layers = [
            (bottom, BlendMode.NORMAL, 1.0),
            (top, BlendMode.NORMAL, 1.0),
        ]

        result = gpu.composite_layers(bg.copy(), layers)
        diff = np.abs(result.astype(int) - top.astype(int))
        assert diff.max() <= 1

    def test_region_based_compositing(self, gpu: GPUCompositor) -> None:
        """Layer with small non-transparent region should only affect that region."""
        h, w = 64, 64
        bg = _make_frame(h, w, (100, 100, 100, 255))

        # Layer with only a small patch of color
        layer = _make_frame(h, w, (0, 0, 0, 0))  # All transparent
        layer[10:20, 10:20] = [255, 0, 0, 255]  # Red patch

        gpu_result = gpu.composite_layers(bg.copy(), [(layer, BlendMode.NORMAL, 1.0)])
        cpu_result = cpu_composite(bg.copy(), [(layer, BlendMode.NORMAL, 1.0)])

        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE

    def test_large_frame_1080p(self, gpu: GPUCompositor) -> None:
        """Test with a 1080p-sized frame."""
        h, w = 1080, 1920
        bg = _make_frame(h, w, (20, 40, 60, 255))
        layer = _make_frame(h, w, (200, 100, 50, 128))

        result = gpu.composite_layers(bg.copy(), [(layer, BlendMode.NORMAL, 0.9)])
        assert result.shape == (h, w, 4)
        assert result.dtype == np.uint8

    def test_buffer_reuse_different_sizes(self, gpu: GPUCompositor) -> None:
        """Buffers should resize correctly for larger frames."""
        # Small frame first
        bg1 = _make_frame(32, 32, (100, 100, 100, 255))
        layer1 = _make_frame(32, 32, (200, 0, 0, 255))
        r1 = gpu.composite_layers(bg1.copy(), [(layer1, BlendMode.NORMAL, 0.5)])
        assert r1.shape == (32, 32, 4)

        # Larger frame second — should trigger buffer reallocation
        bg2 = _make_frame(128, 128, (100, 100, 100, 255))
        layer2 = _make_frame(128, 128, (200, 0, 0, 255))
        r2 = gpu.composite_layers(bg2.copy(), [(layer2, BlendMode.NORMAL, 0.5)])
        assert r2.shape == (128, 128, 4)


class TestGPUCompositorFallback:
    """Tests for automatic CPU fallback."""

    def test_gpu_composite_layers_fallback(self) -> None:
        """gpu_composite_layers falls back to CPU when GPU unavailable."""
        h, w = 32, 32
        bg = _make_frame(h, w, (100, 150, 200, 255))
        layer = _make_frame(h, w, (255, 0, 0, 200))

        # This should work regardless of GPU availability (falls back to CPU)
        result = gpu_composite_layers(bg.copy(), [(layer, BlendMode.NORMAL, 1.0)])
        assert result.shape == (h, w, 4)
        assert result.dtype == np.uint8


class TestGPUCompositorConfig:
    """Tests for config-based GPU compositing toggle."""

    def test_config_gpu_compositing_default_off(self) -> None:
        reset_config()
        assert get_config().gpu_compositing is False

    def test_config_gpu_compositing_toggle(self) -> None:
        reset_config()
        set_config(PyMotionConfig(gpu_compositing=True))
        assert get_config().gpu_compositing is True
        reset_config()

    def test_config_gpu_vram_limit(self) -> None:
        reset_config()
        assert get_config().gpu_vram_limit_bytes == 2 * 1024 * 1024 * 1024
        reset_config()

    def test_composition_uses_gpu_when_enabled(self) -> None:
        """Composition._render_frame uses GPU when config is enabled."""
        reset_config()
        set_config(PyMotionConfig(gpu_compositing=True))
        try:
            from pymotion.clip.color import ColorClip
            from pymotion.composition import Composition

            comp = Composition(64, 64, fps=30, duration=5)
            bg = ColorClip("#1A1A2E").set_duration(5)
            fg = ColorClip("#E94560").set_duration(5)
            fg._opacity = 0.5
            comp.add(bg, fg)

            frame = comp._render_frame(0)
            assert frame.shape == (64, 64, 4)
            assert frame.dtype == np.uint8
        finally:
            reset_config()
