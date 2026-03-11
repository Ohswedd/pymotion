"""Visual effects — blur, grain, sharpen, glow, bloom, chromatic aberration, lens flare.

All effects operate on BGRA numpy arrays and are stateless.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter  # type: ignore[import-untyped]

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.color import Color, ColorInput
from pymotion.utils.math import Vec2


@dataclass
class GaussianBlur(Effect):
    """Gaussian blur effect.

    Args:
        radius: Blur radius in pixels.
    """

    radius: float = 5.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply Gaussian blur to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Blurred BGRA frame.
        """
        if self.radius <= 0:
            return frame.copy()

        result = frame.astype(np.float32)
        # Blur RGB channels, preserve alpha
        for c in range(3):
            result[:, :, c] = gaussian_filter(result[:, :, c], sigma=self.radius)
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class MotionBlur(Effect):
    """Motion blur effect — directional blur along a specified angle.

    Args:
        angle: Direction of motion blur in degrees (0 = horizontal right).
        distance: Blur distance in pixels.
    """

    angle: float = 0.0
    distance: float = 10.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply motion blur to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Motion-blurred BGRA frame.
        """
        if self.distance <= 0:
            return frame.copy()

        h, w = frame.shape[:2]
        result = frame.astype(np.float32)
        alpha = result[:, :, 3:4].copy()

        rad = np.radians(self.angle)
        dx = np.cos(rad)
        dy = np.sin(rad)
        n_samples = max(2, int(self.distance))
        offsets = np.linspace(-self.distance / 2, self.distance / 2, n_samples)

        accum = np.zeros_like(result[:, :, :3])
        for offset in offsets:
            ox = int(round(offset * dx))
            oy = int(round(offset * dy))
            shifted = np.roll(np.roll(result[:, :, :3], ox, axis=1), oy, axis=0)
            accum += shifted
        accum /= n_samples

        out = np.empty_like(result)
        out[:, :, :3] = accum
        out[:, :, 3:4] = alpha
        return np.clip(out, 0, 255).astype(np.uint8)


@dataclass
class Vignette(Effect):
    """Vignette effect — darkens edges of the frame.

    Args:
        strength: How dark the vignette is (0.0 = none, 1.0 = full).
        radius: Size of the clear center area (0.0-1.0).
        feather: How gradual the falloff is (0.0-1.0).
    """

    strength: float = 0.5
    radius: float = 0.8
    feather: float = 0.3

    _cached_mask: np.ndarray | None = None
    _cached_key: tuple[int, int, float, float, float] | None = None

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply vignette effect to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with vignette applied.
        """
        h, w = frame.shape[:2]

        # Cache the vignette mask — it only depends on resolution and params
        cache_key = (h, w, self.strength, self.radius, self.feather)
        if self._cached_key != cache_key or self._cached_mask is None:
            y = np.linspace(-1, 1, h, dtype=np.float32)
            x = np.linspace(-1, 1, w, dtype=np.float32)
            xx, yy = np.meshgrid(x, y)
            dist = np.sqrt(xx**2 + yy**2)

            t = np.clip((dist - self.radius) / max(self.feather, 0.001), 0.0, 1.0)
            vignette = 1.0 - t * t * (3.0 - 2.0 * t)  # smoothstep
            self._cached_mask = (1.0 - self.strength * (1.0 - vignette)).astype(np.float32)
            self._cached_key = cache_key

        result = frame.astype(np.float32)
        # Apply to BGR channels only, preserve alpha
        result[:, :, :3] *= self._cached_mask[:, :, np.newaxis]

        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class FilmGrain(Effect):
    """Film grain effect — adds noise to simulate analog film grain.

    Args:
        strength: Grain intensity (0.0-1.0).
        size: Grain size multiplier.
        monochrome: Whether grain is monochrome or colored.
    """

    strength: float = 0.3
    size: float = 1.0
    monochrome: bool = True

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply film grain to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with grain applied.
        """
        h, w = frame.shape[:2]
        rng = np.random.default_rng(ctx.frame)

        # Generate grain at possibly reduced resolution, then tile/resize
        grain_h = max(1, int(h / max(self.size, 0.1)))
        grain_w = max(1, int(w / max(self.size, 0.1)))

        if self.monochrome:
            noise_small = rng.standard_normal((grain_h, grain_w)).astype(np.float32)
            noise_small = np.stack([noise_small] * 3, axis=-1)
        else:
            noise_small = rng.standard_normal((grain_h, grain_w, 3)).astype(np.float32)

        # Resize to full frame
        y_idx = np.clip((np.arange(h) * grain_h / h).astype(np.intp), 0, grain_h - 1)
        x_idx = np.clip((np.arange(w) * grain_w / w).astype(np.intp), 0, grain_w - 1)
        noise = noise_small[np.ix_(y_idx, x_idx)]

        result = frame.astype(np.float32)
        result[:, :, :3] += noise * self.strength * 50
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class Sharpen(Effect):
    """Sharpen effect — unsharp mask sharpening.

    Args:
        amount: Sharpening strength.
    """

    amount: float = 1.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply sharpening to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Sharpened BGRA frame.
        """
        if self.amount <= 0:
            return frame.copy()

        result = frame.astype(np.float32)
        blurred = np.empty_like(result)
        blurred[:, :, 3] = result[:, :, 3]
        for c in range(3):
            blurred[:, :, c] = gaussian_filter(result[:, :, c], sigma=1.0)

        # Unsharp mask: original + amount * (original - blurred)
        sharpened = result.copy()
        sharpened[:, :, :3] += self.amount * (result[:, :, :3] - blurred[:, :, :3])
        return np.clip(sharpened, 0, 255).astype(np.uint8)


@dataclass
class ChromaticAberration(Effect):
    """Chromatic aberration effect — separates color channels spatially.

    Args:
        offset: Pixel offset for channel separation.
        angle: Direction angle in degrees.
    """

    offset: float = 3.0
    angle: float = 0.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply chromatic aberration to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with chromatic aberration.
        """
        if self.offset <= 0:
            return frame.copy()

        rad = np.radians(self.angle)
        dx = int(round(self.offset * np.cos(rad)))
        dy = int(round(self.offset * np.sin(rad)))

        result = frame.copy()
        # Shift R channel one direction, B the other; G stays
        result[:, :, 2] = np.roll(np.roll(frame[:, :, 2], dx, axis=1), dy, axis=0)  # R
        result[:, :, 0] = np.roll(np.roll(frame[:, :, 0], -dx, axis=1), -dy, axis=0)  # B
        return result


@dataclass
class Glow(Effect):
    """Glow effect — soft glow from bright areas.

    Args:
        radius: Blur radius for the glow.
        strength: Glow intensity.
        threshold: Brightness threshold (0-255) for glow source.
    """

    radius: float = 10.0
    strength: float = 0.5
    threshold: float = 200.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply glow effect to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with glow applied.
        """
        result = frame.astype(np.float32)

        # Extract bright areas
        luminance = 0.299 * result[:, :, 2] + 0.587 * result[:, :, 1] + 0.114 * result[:, :, 0]
        mask = (luminance > self.threshold).astype(np.float32)

        glow_layer = np.empty_like(result[:, :, :3])
        for c in range(3):
            bright = result[:, :, c] * mask
            glow_layer[:, :, c] = gaussian_filter(bright, sigma=self.radius)

        result[:, :, :3] += glow_layer * self.strength
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class Bloom(Effect):
    """Bloom effect — multi-pass glow from bright areas.

    Args:
        radius: Base blur radius.
        strength: Bloom intensity.
        threshold: Brightness threshold (0-255).
        iterations: Number of blur passes at increasing radii.
    """

    radius: float = 10.0
    strength: float = 0.5
    threshold: float = 200.0
    iterations: int = 3

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply bloom effect to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with bloom applied.
        """
        result = frame.astype(np.float32)

        luminance = 0.299 * result[:, :, 2] + 0.587 * result[:, :, 1] + 0.114 * result[:, :, 0]
        mask = (luminance > self.threshold).astype(np.float32)

        # Extract bright pixels
        bright = np.zeros_like(result[:, :, :3])
        for c in range(3):
            bright[:, :, c] = result[:, :, c] * mask

        # Downsample pyramid bloom — blur at successively lower resolutions
        h, w = bright.shape[:2]
        bloom_accum = np.zeros_like(bright)
        current = bright.copy()
        for _i in range(self.iterations):
            # Downsample by 2x
            dh, dw = max(1, current.shape[0] // 2), max(1, current.shape[1] // 2)
            if dh < 4 or dw < 4:
                break
            downsampled = current[::2, ::2][:dh, :dw]
            # Blur at reduced resolution (much faster, softer result)
            for c in range(3):
                downsampled[:, :, c] = gaussian_filter(downsampled[:, :, c], sigma=self.radius)
            # Upsample back to original size
            y_idx = np.clip((np.arange(h) * dh / h).astype(np.intp), 0, dh - 1)
            x_idx = np.clip((np.arange(w) * dw / w).astype(np.intp), 0, dw - 1)
            upsampled = downsampled[np.ix_(y_idx, x_idx)]
            bloom_accum += upsampled
            current = downsampled

        bloom_accum /= max(self.iterations, 1)
        result[:, :, :3] += bloom_accum * self.strength
        return np.clip(result, 0, 255).astype(np.uint8)


@dataclass
class LensFlare(Effect):
    """Lens flare effect — renders a flare at a specified position.

    Args:
        position: Flare center in normalized coordinates (0-1).
        intensity: Flare brightness.
        color: Flare color.
    """

    position: Vec2 = Vec2(0.5, 0.5)
    intensity: float = 0.8
    color: Color = Color(1.0, 0.9, 0.7, 1.0)

    def __init__(
        self,
        position: Vec2 | None = None,
        intensity: float = 0.8,
        color: ColorInput = "#FFE6B3",
    ) -> None:
        """Initialize LensFlare effect.

        Args:
            position: Flare center in normalized coordinates.
            intensity: Flare brightness.
            color: Flare color.
        """
        self.position = position if position is not None else Vec2(0.5, 0.5)
        self.intensity = intensity
        self.color = Color.parse(color)

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply lens flare effect to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            BGRA frame with lens flare.
        """
        h, w = frame.shape[:2]
        result = frame.astype(np.float32)

        cy = self.position.y * h
        cx = self.position.x * w

        y_coords = np.arange(h, dtype=np.float32) - cy
        x_coords = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")
        dist = np.sqrt(xx * xx + yy * yy)

        # Radial falloff for main flare
        max_dim = max(h, w) * 0.3
        flare = np.exp(-(dist * dist) / (2 * max_dim * max_dim))

        b, g, r, _a = self.color.to_bgra_uint8()
        result[:, :, 0] += flare * b * self.intensity
        result[:, :, 1] += flare * g * self.intensity
        result[:, :, 2] += flare * r * self.intensity

        return np.clip(result, 0, 255).astype(np.uint8)
