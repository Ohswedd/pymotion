"""Distortion effects — wave warp, ripple, twirl, perspective warp, fisheye.

All effects operate on BGRA numpy arrays and are stateless.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pymotion.clip.base import RenderContext
from pymotion.effects.base import Effect
from pymotion.utils.math import Vec2


@dataclass
class WaveWarp(Effect):
    """Wave warp distortion — sinusoidal displacement.

    Args:
        amplitude: Wave amplitude in pixels.
        frequency: Wave frequency.
        phase: Phase offset in radians.
        axis: Warp axis ('x' or 'y').
    """

    amplitude: float = 10.0
    frequency: float = 0.05
    phase: float = 0.0
    axis: str = "x"

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply wave warp to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Wave-warped BGRA frame.
        """
        h, w = frame.shape[:2]
        y_coords = np.arange(h, dtype=np.float32)
        x_coords = np.arange(w, dtype=np.float32)
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

        if self.axis == "x":
            displacement = self.amplitude * np.sin(yy * self.frequency + self.phase)
            src_x = np.clip((xx + displacement).astype(np.intp), 0, w - 1)
            src_y = yy.astype(np.intp)
        else:
            displacement = self.amplitude * np.sin(xx * self.frequency + self.phase)
            src_x = xx.astype(np.intp)
            src_y = np.clip((yy + displacement).astype(np.intp), 0, h - 1)

        out: np.ndarray = frame[src_y, src_x]
        return out


@dataclass
class Ripple(Effect):
    """Ripple distortion — concentric wave from a center point.

    Args:
        center: Ripple center in normalized coordinates (0-1).
        amplitude: Wave amplitude in pixels.
        frequency: Wave frequency.
        decay: How quickly the ripple fades with distance.
    """

    center: Vec2 = Vec2(0.5, 0.5)
    amplitude: float = 10.0
    frequency: float = 0.1
    decay: float = 0.01

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply ripple distortion to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Rippled BGRA frame.
        """
        h, w = frame.shape[:2]
        cy = self.center.y * h
        cx = self.center.x * w

        y_coords = np.arange(h, dtype=np.float32) - cy
        x_coords = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")
        dist = np.sqrt(xx * xx + yy * yy)

        # Ripple displacement along radial direction
        safe_dist = np.where(dist > 0, dist, 1.0)
        angle = self.amplitude * np.sin(dist * self.frequency) * np.exp(-dist * self.decay)
        dx = angle * xx / safe_dist
        dy = angle * yy / safe_dist

        src_x = np.clip((xx + cx + dx).astype(np.intp), 0, w - 1)
        src_y = np.clip((yy + cy + dy).astype(np.intp), 0, h - 1)

        out: np.ndarray = frame[src_y, src_x]
        return out


@dataclass
class Twirl(Effect):
    """Twirl distortion — rotates pixels around a center point.

    Args:
        center: Twirl center in normalized coordinates (0-1).
        angle: Maximum rotation angle in radians.
        radius: Twirl effect radius in pixels.
    """

    center: Vec2 = Vec2(0.5, 0.5)
    angle: float = 1.0
    radius: float = 100.0

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply twirl distortion to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Twirled BGRA frame.
        """
        h, w = frame.shape[:2]
        cy = self.center.y * h
        cx = self.center.x * w

        y_coords = np.arange(h, dtype=np.float32) - cy
        x_coords = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")
        dist = np.sqrt(xx * xx + yy * yy)

        # Rotation angle decreases with distance from center
        effective_radius = max(self.radius, 1.0)
        rotation = self.angle * np.clip(1.0 - dist / effective_radius, 0, 1)

        cos_r = np.cos(rotation)
        sin_r = np.sin(rotation)

        src_x = np.clip((cos_r * xx - sin_r * yy + cx).astype(np.intp), 0, w - 1)
        src_y = np.clip((sin_r * xx + cos_r * yy + cy).astype(np.intp), 0, h - 1)

        out: np.ndarray = frame[src_y, src_x]
        return out


@dataclass
class PerspectiveWarp(Effect):
    """Perspective warp — maps frame to a quadrilateral defined by four corners.

    Args:
        corners: Four destination corners as Vec2 in normalized coordinates (0-1),
                 ordered: top-left, top-right, bottom-right, bottom-left.
    """

    corners: tuple[Vec2, Vec2, Vec2, Vec2] = (
        Vec2(0.0, 0.0),
        Vec2(1.0, 0.0),
        Vec2(1.0, 1.0),
        Vec2(0.0, 1.0),
    )

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply perspective warp to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Perspective-warped BGRA frame.
        """
        h, w = frame.shape[:2]
        tl, tr, br, bl = self.corners

        # Bilinear interpolation of destination → source mapping
        u = np.linspace(0, 1, w, dtype=np.float32).reshape(1, w)
        v = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1)

        # Interpolate corner positions
        top_x = tl.x * (1 - u) + tr.x * u
        top_y = tl.y * (1 - u) + tr.y * u
        bot_x = bl.x * (1 - u) + br.x * u
        bot_y = bl.y * (1 - u) + br.y * u

        src_x = (top_x * (1 - v) + bot_x * v) * (w - 1)
        src_y = (top_y * (1 - v) + bot_y * v) * (h - 1)

        src_xi = np.clip(src_x.astype(np.intp), 0, w - 1)
        src_yi = np.clip(src_y.astype(np.intp), 0, h - 1)

        out: np.ndarray = frame[src_yi, src_xi]
        return out


@dataclass
class Fisheye(Effect):
    """Fisheye distortion — barrel distortion from center.

    Args:
        strength: Distortion strength (>0 barrel, <0 pincushion).
    """

    strength: float = 0.5

    def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
        """Apply fisheye distortion to a BGRA frame.

        Args:
            frame: BGRA numpy array of shape (H, W, 4), dtype uint8.
            ctx: Render context.

        Returns:
            Fisheye-distorted BGRA frame.
        """
        h, w = frame.shape[:2]
        cy, cx = h / 2.0, w / 2.0

        y_coords = (np.arange(h, dtype=np.float32) - cy) / cy
        x_coords = (np.arange(w, dtype=np.float32) - cx) / cx
        yy, xx = np.meshgrid(y_coords, x_coords, indexing="ij")

        r = np.sqrt(xx * xx + yy * yy)
        # Barrel distortion formula
        r_new = r * (1.0 + self.strength * r * r)

        safe_r = np.where(r > 0, r, 1.0)
        scale = r_new / safe_r

        src_x = np.clip((xx * scale * cx + cx).astype(np.intp), 0, w - 1)
        src_y = np.clip((yy * scale * cy + cy).astype(np.intp), 0, h - 1)

        out: np.ndarray = frame[src_y, src_x]
        return out
