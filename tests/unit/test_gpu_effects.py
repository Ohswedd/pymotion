"""Tests for GPU-accelerated batch effect processing.

Verifies that the GPUEffectPipeline produces results matching
sequential CPU effect application within acceptable tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.effects.color import Brightness, Contrast, HueSaturationLuminance, Saturation
from pymotion.effects.visual import GaussianBlur
from pymotion.render.gpu_effects import (
    GPUEffectPipeline,
    get_gpu_effect_pipeline,
    is_gpu_effect,
)

_MAX_TOLERANCE = 2


def _ctx() -> RenderContext:
    return RenderContext(
        frame=0,
        fps=30,
        resolution=Resolution(64, 64),
        time_range=TimeRange(0, 60),
        local_frame=0,
        progress=0.0,
    )


def _random_frame(h: int = 64, w: int = 64, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    f = rng.randint(30, 230, (h, w, 4), dtype=np.uint8)
    f[:, :, 3] = 255
    return f


@pytest.fixture()
def pipeline() -> GPUEffectPipeline:
    p = GPUEffectPipeline()
    if not p.available:
        pytest.skip("WGPU GPU not available")
    return p


class TestIsGPUEffect:
    """Test is_gpu_effect classification."""

    def test_brightness_is_gpu(self) -> None:
        assert is_gpu_effect(Brightness(1.2)) is True

    def test_contrast_is_gpu(self) -> None:
        assert is_gpu_effect(Contrast(1.1)) is True

    def test_saturation_is_gpu(self) -> None:
        assert is_gpu_effect(Saturation(0.8)) is True

    def test_hsl_is_gpu(self) -> None:
        assert is_gpu_effect(HueSaturationLuminance(hue=10.0)) is True

    def test_gaussian_blur_not_gpu(self) -> None:
        assert is_gpu_effect(GaussianBlur(radius=5)) is False


class TestGPUEffectPipelineSingleEffect:
    """Test each GPU-compatible effect individually."""

    def test_brightness(self, pipeline: GPUEffectPipeline) -> None:
        frame = _random_frame()
        effects = [Brightness(value=1.3)]
        gpu_result = pipeline.apply_batch(frame.copy(), effects, _ctx())
        cpu_result = effects[0].apply(frame.copy(), _ctx())
        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE

    def test_contrast(self, pipeline: GPUEffectPipeline) -> None:
        frame = _random_frame()
        effects = [Contrast(value=1.5)]
        gpu_result = pipeline.apply_batch(frame.copy(), effects, _ctx())
        cpu_result = effects[0].apply(frame.copy(), _ctx())
        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE

    def test_saturation(self, pipeline: GPUEffectPipeline) -> None:
        frame = _random_frame()
        effects = [Saturation(value=0.5)]
        gpu_result = pipeline.apply_batch(frame.copy(), effects, _ctx())
        cpu_result = effects[0].apply(frame.copy(), _ctx())
        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE

    def test_hsl_runs_without_error(self, pipeline: GPUEffectPipeline) -> None:
        """HSL effect executes on GPU and produces valid output.

        Note: GPU HSL uses an RGB-space rotation approximation which differs
        from the CPU's exact HSL→RGB conversion. We verify the output is
        valid but do not compare pixel values exactly.
        """
        frame = _random_frame()
        effects = [HueSaturationLuminance(hue=0.0, saturation=1.2, luminance=0.9)]
        result = pipeline.apply_batch(frame.copy(), effects, _ctx())
        assert result.shape == frame.shape
        assert result.dtype == np.uint8
        # Alpha should be preserved
        assert np.array_equal(result[:, :, 3], frame[:, :, 3])


class TestGPUEffectPipelineBatch:
    """Test batching multiple effects in a single pass."""

    def test_batch_brightness_contrast_saturation(self, pipeline: GPUEffectPipeline) -> None:
        frame = _random_frame()
        effects = [Brightness(1.2), Contrast(1.1), Saturation(0.8)]

        gpu_result = pipeline.apply_batch(frame.copy(), effects, _ctx())

        cpu_result = frame.copy()
        for e in effects:
            cpu_result = e.apply(cpu_result, _ctx())

        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE

    def test_empty_effects_returns_original(self, pipeline: GPUEffectPipeline) -> None:
        frame = _random_frame()
        result = pipeline.apply_batch(frame.copy(), [], _ctx())
        assert np.array_equal(result, frame)

    def test_mixed_gpu_cpu_effects(self, pipeline: GPUEffectPipeline) -> None:
        """GPU effects are batched, CPU effects applied in order."""
        frame = _random_frame()
        effects = [
            Brightness(1.2),  # GPU
            Contrast(1.1),  # GPU
            GaussianBlur(radius=3),  # CPU — forces flush of GPU batch
            Saturation(0.8),  # GPU (new batch)
        ]

        gpu_result = pipeline.apply_batch(frame.copy(), effects, _ctx())

        cpu_result = frame.copy()
        for e in effects:
            cpu_result = e.apply(cpu_result, _ctx())

        diff = np.abs(gpu_result.astype(int) - cpu_result.astype(int))
        assert diff.max() <= _MAX_TOLERANCE

    def test_preserves_alpha(self, pipeline: GPUEffectPipeline) -> None:
        """GPU effects should not modify the alpha channel."""
        frame = _random_frame()
        original_alpha = frame[:, :, 3].copy()

        effects = [Brightness(1.5), Contrast(0.8)]
        result = pipeline.apply_batch(frame.copy(), effects, _ctx())

        assert np.array_equal(result[:, :, 3], original_alpha)

    def test_large_frame_1080p(self, pipeline: GPUEffectPipeline) -> None:
        """Test with a 1080p frame."""
        frame = np.full((1080, 1920, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255

        effects = [Brightness(1.1), Saturation(0.9)]
        result = pipeline.apply_batch(frame.copy(), effects, _ctx())
        assert result.shape == (1080, 1920, 4)
        assert result.dtype == np.uint8


class TestGPUEffectPipelineSingleton:
    """Test module-level singleton."""

    def test_singleton_returns_same(self) -> None:
        a = get_gpu_effect_pipeline()
        b = get_gpu_effect_pipeline()
        assert a is b

    def test_release_clears_state(self) -> None:
        p = GPUEffectPipeline()
        p.release()
        assert p._device is None
