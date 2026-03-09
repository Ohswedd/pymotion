"""Tests for all visual, color, distortion, and light effects."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.effects.color import (
    BleachBypass,
    Brightness,
    ColorBalance,
    Contrast,
    Curves,
    HueSaturationLuminance,
    LUTEffect,
    Saturation,
    SplitToning,
)
from pymotion.effects.distortion import (
    Fisheye,
    PerspectiveWarp,
    Ripple,
    Twirl,
    WaveWarp,
)
from pymotion.effects.light import (
    GodRays,
    LensFlareLight,
    LightLeak,
    NeonGlow,
)
from pymotion.effects.visual import (
    Bloom,
    ChromaticAberration,
    FilmGrain,
    GaussianBlur,
    Glow,
    LensFlare,
    MotionBlur,
    Sharpen,
    Vignette,
)
from pymotion.utils.math import Vec2

_H, _W = 16, 16


@pytest.fixture()
def frame() -> np.ndarray:
    """Gradient BGRA test frame."""
    f = np.zeros((_H, _W, 4), dtype=np.uint8)
    for y in range(_H):
        for x in range(_W):
            f[y, x] = [x * 16, y * 16, (x + y) * 8, 255]
    return f


@pytest.fixture()
def ctx() -> RenderContext:
    """Standard render context."""
    return RenderContext(
        frame=10,
        fps=30,
        resolution=Resolution(_W, _H),
        time_range=TimeRange(0, 90),
        local_frame=10,
        progress=0.5,
    )


def _assert_valid(result: np.ndarray) -> None:
    assert result.shape == (_H, _W, 4)
    assert result.dtype == np.uint8


# ── Visual Effects ──


class TestGaussianBlur:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = GaussianBlur(radius=2.0).apply(frame, ctx)
        _assert_valid(result)

    def test_zero_radius_noop(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = GaussianBlur(radius=0.0).apply(frame, ctx)
        _assert_valid(result)
        np.testing.assert_array_equal(result, frame)

    def test_preserves_alpha(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = GaussianBlur(radius=3.0).apply(frame, ctx)
        np.testing.assert_array_equal(result[:, :, 3], frame[:, :, 3])


class TestMotionBlur:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = MotionBlur(angle=45, distance=5).apply(frame, ctx)
        _assert_valid(result)

    def test_zero_distance_noop(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = MotionBlur(distance=0).apply(frame, ctx)
        _assert_valid(result)
        np.testing.assert_array_equal(result, frame)


class TestVignette:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Vignette(strength=0.8).apply(frame, ctx)
        _assert_valid(result)

    def test_darkens_edges(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Vignette(strength=1.0, radius=0.2, feather=0.1).apply(frame, ctx)
        # Corners should be darker
        assert np.mean(result[0, 0, :3]) <= np.mean(frame[0, 0, :3])


class TestFilmGrain:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = FilmGrain(strength=0.5).apply(frame, ctx)
        _assert_valid(result)

    def test_monochrome(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = FilmGrain(strength=0.5, monochrome=True).apply(frame, ctx)
        _assert_valid(result)

    def test_colored(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = FilmGrain(strength=0.5, monochrome=False).apply(frame, ctx)
        _assert_valid(result)

    def test_deterministic_per_frame(self, frame: np.ndarray, ctx: RenderContext) -> None:
        r1 = FilmGrain(strength=0.5).apply(frame, ctx)
        r2 = FilmGrain(strength=0.5).apply(frame, ctx)
        np.testing.assert_array_equal(r1, r2)


class TestSharpen:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Sharpen(amount=1.0).apply(frame, ctx)
        _assert_valid(result)

    def test_zero_noop(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Sharpen(amount=0.0).apply(frame, ctx)
        np.testing.assert_array_equal(result, frame)


class TestChromaticAberration:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = ChromaticAberration(offset=3.0).apply(frame, ctx)
        _assert_valid(result)

    def test_zero_offset_noop(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = ChromaticAberration(offset=0.0).apply(frame, ctx)
        np.testing.assert_array_equal(result, frame)


class TestGlow:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Glow(radius=5, strength=0.5, threshold=100).apply(frame, ctx)
        _assert_valid(result)


class TestBloom:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Bloom(radius=5, strength=0.5, threshold=100, iterations=2).apply(frame, ctx)
        _assert_valid(result)


class TestLensFlare:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = LensFlare(position=Vec2(0.5, 0.5), intensity=0.8).apply(frame, ctx)
        _assert_valid(result)

    def test_brightens_center(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = LensFlare(position=Vec2(0.5, 0.5), intensity=1.0).apply(frame, ctx)
        center = _H // 2, _W // 2
        assert np.mean(result[center[0], center[1], :3]) >= np.mean(frame[center[0], center[1], :3])


# ── Color Effects ──


class TestBrightness:
    def test_brighter(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Brightness(value=1.5).apply(frame, ctx)
        _assert_valid(result)
        assert np.mean(result[:, :, :3]) >= np.mean(frame[:, :, :3])

    def test_darker(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Brightness(value=0.5).apply(frame, ctx)
        _assert_valid(result)
        assert np.mean(result[:, :, :3]) <= np.mean(frame[:, :, :3])

    def test_unity_noop(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Brightness(value=1.0).apply(frame, ctx)
        _assert_valid(result)
        np.testing.assert_array_equal(result, frame)


class TestContrast:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Contrast(value=1.5).apply(frame, ctx)
        _assert_valid(result)


class TestSaturation:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Saturation(value=0.5).apply(frame, ctx)
        _assert_valid(result)

    def test_grayscale(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Saturation(value=0.0).apply(frame, ctx)
        _assert_valid(result)


class TestHueSaturationLuminance:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = HueSaturationLuminance(hue=30, saturation=1.2, luminance=0.1).apply(frame, ctx)
        _assert_valid(result)

    def test_no_change(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = HueSaturationLuminance(hue=0, saturation=1.0, luminance=0.0).apply(frame, ctx)
        _assert_valid(result)


class TestColorBalance:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = ColorBalance(shadows="#330000", midtones="#003300", highlights="#000033").apply(
            frame, ctx
        )
        _assert_valid(result)


class TestCurves:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Curves(rgb_curve=[(0, 0), (128, 160), (255, 255)]).apply(frame, ctx)
        _assert_valid(result)

    def test_identity(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Curves().apply(frame, ctx)
        _assert_valid(result)
        np.testing.assert_array_equal(result, frame)

    def test_invert_curve(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Curves(rgb_curve=[(0, 255), (255, 0)]).apply(frame, ctx)
        _assert_valid(result)


class TestLUTEffect:
    def test_applies(self, ctx: RenderContext) -> None:
        # Create a minimal identity .cube LUT
        with NamedTemporaryFile(suffix=".cube", mode="w", delete=False) as f:
            f.write("LUT_3D_SIZE 2\n")
            for b in [0.0, 1.0]:
                for g in [0.0, 1.0]:
                    for r in [0.0, 1.0]:
                        f.write(f"{r} {g} {b}\n")
            lut_path = Path(f.name)

        frame = np.full((4, 4, 4), 128, dtype=np.uint8)
        frame[:, :, 3] = 255
        result = LUTEffect(lut_path=lut_path, intensity=1.0).apply(frame, ctx)
        assert result.shape == (4, 4, 4)
        assert result.dtype == np.uint8

    def test_resolves_path(self, tmp_path: Path) -> None:
        # Path should be resolved to absolute
        effect = LUTEffect(lut_path=tmp_path / "test.cube")
        assert effect.lut_path.is_absolute()


class TestSplitToning:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = SplitToning(
            highlights_color="#FFE6CC", shadows_color="#334D80", balance=0.0
        ).apply(frame, ctx)
        _assert_valid(result)


class TestBleachBypass:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = BleachBypass(strength=0.5).apply(frame, ctx)
        _assert_valid(result)


# ── Distortion Effects ──


class TestWaveWarp:
    def test_x_axis(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = WaveWarp(amplitude=5, frequency=0.1, axis="x").apply(frame, ctx)
        _assert_valid(result)

    def test_y_axis(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = WaveWarp(amplitude=5, frequency=0.1, axis="y").apply(frame, ctx)
        _assert_valid(result)


class TestRipple:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Ripple(center=Vec2(0.5, 0.5), amplitude=5).apply(frame, ctx)
        _assert_valid(result)


class TestTwirl:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Twirl(center=Vec2(0.5, 0.5), angle=1.0, radius=50).apply(frame, ctx)
        _assert_valid(result)


class TestPerspectiveWarp:
    def test_identity(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = PerspectiveWarp().apply(frame, ctx)
        _assert_valid(result)
        # Near-identity due to integer rounding
        np.testing.assert_allclose(result.astype(float), frame.astype(float), atol=20)

    def test_custom_corners(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = PerspectiveWarp(
            corners=(Vec2(0.1, 0.1), Vec2(0.9, 0.0), Vec2(1.0, 1.0), Vec2(0.0, 0.9))
        ).apply(frame, ctx)
        _assert_valid(result)


class TestFisheye:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Fisheye(strength=0.5).apply(frame, ctx)
        _assert_valid(result)

    def test_pincushion(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = Fisheye(strength=-0.3).apply(frame, ctx)
        _assert_valid(result)


# ── Light Effects ──


class TestLensFlareLight:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = LensFlareLight(position=Vec2(0.5, 0.5), intensity=0.8).apply(frame, ctx)
        _assert_valid(result)


class TestGodRays:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = GodRays(position=Vec2(0.5, 0.0), intensity=0.5, samples=10).apply(frame, ctx)
        _assert_valid(result)


class TestNeonGlow:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = NeonGlow(color="#FF00FF", radius=5, strength=0.5).apply(frame, ctx)
        _assert_valid(result)


class TestLightLeak:
    def test_applies(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = LightLeak(color="#FF9933", intensity=0.5, size=0.3).apply(frame, ctx)
        _assert_valid(result)

    def test_brightens_area(self, frame: np.ndarray, ctx: RenderContext) -> None:
        result = LightLeak(intensity=1.0, size=0.5).apply(frame, ctx)
        assert np.mean(result[:, :, :3]) >= np.mean(frame[:, :, :3])
