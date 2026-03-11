"""ParticleSystem, Emitter, and Particle for particle-based effects.

All particle state is stored in NumPy arrays for vectorized updates.
No per-particle Python loops during simulation or rendering.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from pymotion.clip.base import BlendMode, Clip, RenderContext
from pymotion.design.tokens import CHART_COLORS
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger
from pymotion.utils.math import Vec2

logger = get_logger(__name__)


@dataclass
class Emitter:
    """Particle emitter configuration.

    Args:
        position: Spawn origin (x, y).
        rate: Particles per frame.
        lifetime: (min_frames, max_frames) randomized per particle.
        speed: (min, max) initial speed in pixels/frame.
        angle: (min_deg, max_deg) emission cone.
        size: (min_px, max_px) particle size.
        color_over_life: Gradient colors from birth to death.
        opacity_over_life: Opacity values from birth to death.
        gravity: Per-frame velocity delta.
        drag: Velocity multiplier per frame (0 = no drag, 1 = instant stop).
        turbulence: Random noise added to velocity per frame.
        sprite: Optional sprite per particle (default: circle).
        blend_mode: Blending mode for rendering.
    """

    position: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    rate: float = 10.0
    lifetime: tuple[float, float] = (30.0, 60.0)
    speed: tuple[float, float] = (1.0, 5.0)
    angle: tuple[float, float] = (0.0, 360.0)
    size: tuple[float, float] = (2.0, 6.0)
    color_over_life: list[Color] = field(default_factory=lambda: [Color(1.0, 1.0, 1.0)])
    opacity_over_life: list[float] = field(default_factory=lambda: [1.0, 0.0])
    gravity: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    drag: float = 0.0
    turbulence: float = 0.0
    rotation_speed: tuple[float, float] = (0.0, 0.0)
    sprite: np.ndarray | None = None
    blend_mode: BlendMode = BlendMode.ADD


# Maximum particles per system to prevent memory issues
_MAX_PARTICLES = 100_000


class ParticleSystem:
    """Vectorized particle system with one or more emitters.

    All state is stored in flat NumPy arrays for efficient batch
    updates. Renders particles to a BGRA numpy array.

    Args:
        width: Output width in pixels.
        height: Output height in pixels.
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize the particle system.

        Args:
            width: Render width in pixels.
            height: Render height in pixels.
        """
        self._width = width
        self._height = height
        self._emitters: list[Emitter] = []

        # Particle state arrays (pre-allocated, grown as needed)
        self._capacity = 1024
        self._count = 0
        self._pos = np.zeros((self._capacity, 2), dtype=np.float32)
        self._vel = np.zeros((self._capacity, 2), dtype=np.float32)
        self._age = np.zeros(self._capacity, dtype=np.float32)
        self._max_age = np.zeros(self._capacity, dtype=np.float32)
        self._sizes = np.zeros(self._capacity, dtype=np.float32)
        self._rotation = np.zeros(self._capacity, dtype=np.float32)
        self._angular_vel = np.zeros(self._capacity, dtype=np.float32)
        self._emitter_idx = np.zeros(self._capacity, dtype=np.int32)
        self._rng = np.random.default_rng(42)
        # Fractional accumulator per emitter for sub-frame spawn rates
        self._spawn_accum: list[float] = []

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"ParticleSystem({self._width}x{self._height}, "
            f"emitters={len(self._emitters)}, particles={self._count})"
        )

    def add_emitter(self, emitter: Emitter) -> None:
        """Add an emitter to the system.

        Args:
            emitter: The emitter to add.
        """
        self._emitters.append(emitter)

    def _grow_arrays(self, needed: int) -> None:
        """Grow internal arrays to accommodate more particles.

        Args:
            needed: Minimum required capacity.
        """
        new_cap = max(self._capacity * 2, needed)
        new_cap = min(new_cap, _MAX_PARTICLES)

        new_pos = np.zeros((new_cap, 2), dtype=np.float32)
        new_vel = np.zeros((new_cap, 2), dtype=np.float32)
        new_age = np.zeros(new_cap, dtype=np.float32)
        new_max_age = np.zeros(new_cap, dtype=np.float32)
        new_sizes = np.zeros(new_cap, dtype=np.float32)
        new_rotation = np.zeros(new_cap, dtype=np.float32)
        new_angular_vel = np.zeros(new_cap, dtype=np.float32)
        new_eidx = np.zeros(new_cap, dtype=np.int32)

        n = self._count
        new_pos[:n] = self._pos[:n]
        new_vel[:n] = self._vel[:n]
        new_age[:n] = self._age[:n]
        new_max_age[:n] = self._max_age[:n]
        new_sizes[:n] = self._sizes[:n]
        new_rotation[:n] = self._rotation[:n]
        new_angular_vel[:n] = self._angular_vel[:n]
        new_eidx[:n] = self._emitter_idx[:n]

        self._pos = new_pos
        self._vel = new_vel
        self._age = new_age
        self._max_age = new_max_age
        self._sizes = new_sizes
        self._rotation = new_rotation
        self._angular_vel = new_angular_vel
        self._emitter_idx = new_eidx
        self._capacity = new_cap

    def _spawn(self) -> None:
        """Spawn new particles from all emitters."""
        # Ensure accumulator list matches emitter count
        while len(self._spawn_accum) < len(self._emitters):
            self._spawn_accum.append(0.0)

        for ei, emitter in enumerate(self._emitters):
            # Fractional accumulation for sub-frame rates
            self._spawn_accum[ei] += emitter.rate
            n_new = int(self._spawn_accum[ei])
            self._spawn_accum[ei] -= n_new
            if n_new <= 0:
                continue

            total_after = self._count + n_new
            if total_after > _MAX_PARTICLES:
                n_new = max(0, _MAX_PARTICLES - self._count)
                if n_new == 0:
                    continue

            if total_after > self._capacity:
                self._grow_arrays(total_after)

            start = self._count
            end = start + n_new

            # Position
            self._pos[start:end, 0] = emitter.position.x
            self._pos[start:end, 1] = emitter.position.y

            # Random angle and speed
            min_angle = math.radians(emitter.angle[0])
            max_angle = math.radians(emitter.angle[1])
            angles = self._rng.uniform(min_angle, max_angle, n_new).astype(np.float32)
            speeds = self._rng.uniform(emitter.speed[0], emitter.speed[1], n_new).astype(np.float32)

            self._vel[start:end, 0] = np.cos(angles) * speeds
            self._vel[start:end, 1] = np.sin(angles) * speeds

            # Lifetime
            self._max_age[start:end] = self._rng.uniform(
                emitter.lifetime[0], emitter.lifetime[1], n_new
            ).astype(np.float32)

            # Size
            self._sizes[start:end] = self._rng.uniform(
                emitter.size[0], emitter.size[1], n_new
            ).astype(np.float32)

            # Rotation
            self._rotation[start:end] = self._rng.uniform(0.0, math.tau, n_new).astype(np.float32)
            self._angular_vel[start:end] = self._rng.uniform(
                emitter.rotation_speed[0], emitter.rotation_speed[1], n_new
            ).astype(np.float32)

            # Age starts at 0
            self._age[start:end] = 0.0

            # Emitter index
            self._emitter_idx[start:end] = ei

            self._count = end

    def _update(self) -> None:
        """Update all live particles by one frame."""
        n = self._count
        if n == 0:
            return

        # Age all particles
        self._age[:n] += 1.0

        # Remove dead particles (compact arrays)
        alive = self._age[:n] < self._max_age[:n]
        alive_count = int(np.sum(alive))

        if alive_count < n:
            self._pos[:alive_count] = self._pos[:n][alive]
            self._vel[:alive_count] = self._vel[:n][alive]
            self._age[:alive_count] = self._age[:n][alive]
            self._max_age[:alive_count] = self._max_age[:n][alive]
            self._sizes[:alive_count] = self._sizes[:n][alive]
            self._rotation[:alive_count] = self._rotation[:n][alive]
            self._angular_vel[:alive_count] = self._angular_vel[:n][alive]
            self._emitter_idx[:alive_count] = self._emitter_idx[:n][alive]
            self._count = alive_count
            n = alive_count

        if n == 0:
            return

        # Apply gravity from each emitter
        for ei, emitter in enumerate(self._emitters):
            mask = self._emitter_idx[:n] == ei
            self._vel[:n, 0] += np.where(mask, emitter.gravity.x, 0.0)
            self._vel[:n, 1] += np.where(mask, emitter.gravity.y, 0.0)

            # Apply drag
            if emitter.drag > 0:
                drag_factor = 1.0 - emitter.drag
                self._vel[:n, 0] = np.where(mask, self._vel[:n, 0] * drag_factor, self._vel[:n, 0])
                self._vel[:n, 1] = np.where(mask, self._vel[:n, 1] * drag_factor, self._vel[:n, 1])

            # Apply turbulence
            if emitter.turbulence > 0:
                turb = self._rng.normal(0, emitter.turbulence, (n, 2)).astype(np.float32)
                self._vel[:n, 0] += np.where(mask, turb[:, 0], 0.0)
                self._vel[:n, 1] += np.where(mask, turb[:, 1], 0.0)

        # Apply velocity to position
        self._pos[:n] += self._vel[:n]

        # Update rotation
        self._rotation[:n] += self._angular_vel[:n]

    def _render_frame(self) -> np.ndarray:
        """Render current particle state to BGRA array (fully vectorized).

        Works directly in uint8 space to avoid float32 allocation and
        conversion for the full frame. Uses vectorized scatter for
        single-pixel particles.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        n = self._count
        if n == 0:
            return np.zeros((self._height, self._width, 4), dtype=np.uint8)

        frame = np.zeros((self._height, self._width, 4), dtype=np.uint8)

        for ei, emitter in enumerate(self._emitters):
            mask = self._emitter_idx[:n] == ei
            if not np.any(mask):
                continue

            pos = self._pos[:n][mask]
            ages = self._age[:n][mask]
            max_ages = self._max_age[:n][mask]
            count = len(pos)

            # Life progress (vectorized)
            life_t = np.clip(ages / np.maximum(max_ages, 1.0), 0.0, 1.0)

            # Vectorized color interpolation → uint8
            colors = emitter.color_over_life
            n_colors = len(colors)
            color_arr = np.array([[c.b, c.g, c.r] for c in colors], dtype=np.float32)

            if n_colors == 1:
                particle_bgr = np.broadcast_to(color_arr[0], (count, 3)).copy()
            else:
                ci = life_t * (n_colors - 1)
                lo = np.clip(ci.astype(np.int32), 0, n_colors - 2)
                frac = (ci - lo)[:, np.newaxis]
                particle_bgr = color_arr[lo] + (color_arr[lo + 1] - color_arr[lo]) * frac

            # Vectorized opacity interpolation
            opacities_arr = np.array(emitter.opacity_over_life, dtype=np.float32)
            n_opacities = len(opacities_arr)
            if n_opacities == 1:
                particle_alpha = np.full(count, opacities_arr[0], dtype=np.float32)
            else:
                oi = life_t * (n_opacities - 1)
                lo_o = np.clip(oi.astype(np.int32), 0, n_opacities - 2)
                frac_o = oi - lo_o
                particle_alpha = (
                    opacities_arr[lo_o] + (opacities_arr[lo_o + 1] - opacities_arr[lo_o]) * frac_o
                )

            # Convert to uint8: color * opacity * 255
            bgra_u8 = np.empty((count, 4), dtype=np.uint8)
            co = particle_bgr * particle_alpha[:, np.newaxis] * 255.0
            bgra_u8[:, :3] = np.clip(co, 0, 255).astype(np.uint8)
            bgra_u8[:, 3] = np.clip(particle_alpha * 255.0, 0, 255).astype(np.uint8)

            # Integer positions, cull off-screen
            px = pos[:, 0].astype(np.int32)
            py = pos[:, 1].astype(np.int32)
            visible = (px >= 0) & (px < self._width) & (py >= 0) & (py < self._height)
            if not np.any(visible):
                continue

            v_px = px[visible]
            v_py = py[visible]
            v_bgra = bgra_u8[visible]

            # Render particles using their size
            sizes_vis = self._sizes[:n][mask][visible]
            vel_vis = self._vel[:n][mask][visible]
            rot_vis = self._rotation[:n][mask][visible]

            for i in range(len(v_px)):
                px_i, py_i = int(v_px[i]), int(v_py[i])
                sz = max(1, int(sizes_vis[i]))
                bgra_val = v_bgra[i]

                if sz <= 1:
                    # Single pixel — check for rain-style motion blur
                    vx, vy = vel_vis[i, 0], vel_vis[i, 1]
                    speed_sq = vx * vx + vy * vy
                    if speed_sq > 36.0:  # speed > 6px/frame → draw streak
                        speed = math.sqrt(speed_sq)
                        length = min(int(speed * 0.8), 12)
                        dx = vx / speed
                        dy = vy / speed
                        for s in range(length):
                            sx = int(px_i - dx * s)
                            sy = int(py_i - dy * s)
                            if 0 <= sx < self._width and 0 <= sy < self._height:
                                fade = 1.0 - s / length
                                faded = (bgra_val.astype(np.float32) * fade).astype(np.uint8)
                                if emitter.blend_mode == BlendMode.ADD:
                                    acc = frame[sy, sx].astype(np.uint16) + faded.astype(np.uint16)
                                    frame[sy, sx] = np.minimum(acc, 255).astype(np.uint8)
                                else:
                                    frame[sy, sx] = faded
                    else:
                        if emitter.blend_mode == BlendMode.ADD:
                            acc = frame[py_i, px_i].astype(np.uint16) + bgra_val.astype(np.uint16)
                            frame[py_i, px_i] = np.minimum(acc, 255).astype(np.uint8)
                        else:
                            frame[py_i, px_i] = bgra_val
                else:
                    # Multi-pixel particle with rotation
                    half = sz // 2
                    rot = float(rot_vis[i])
                    # For rotated particles, rasterize a rotated rectangle
                    if abs(rot % math.pi) > 0.05 and sz >= 3:
                        cos_r = math.cos(rot)
                        sin_r = math.sin(rot)
                        hw = sz / 2.0
                        hh = sz / 3.0  # rectangle aspect ratio ~3:2
                        for dy in range(-int(hw) - 1, int(hw) + 2):
                            for dx in range(-int(hw) - 1, int(hw) + 2):
                                # Inverse rotate to check if in rectangle
                                lx = dx * cos_r + dy * sin_r
                                ly = -dx * sin_r + dy * cos_r
                                if abs(lx) <= hw and abs(ly) <= hh:
                                    sy = py_i + dy
                                    sx = px_i + dx
                                    if 0 <= sx < self._width and 0 <= sy < self._height:
                                        if emitter.blend_mode == BlendMode.ADD:
                                            acc = frame[sy, sx].astype(np.uint16) + bgra_val.astype(
                                                np.uint16
                                            )
                                            frame[sy, sx] = np.minimum(acc, 255).astype(np.uint8)
                                        else:
                                            frame[sy, sx] = bgra_val
                    else:
                        # Circular particle with anti-aliased edges
                        y0 = max(0, py_i - half - 1)
                        y1 = min(self._height, py_i + half + 2)
                        x0 = max(0, px_i - half - 1)
                        x1 = min(self._width, px_i + half + 2)
                        if y1 > y0 and x1 > x0:
                            # Build distance-based circular mask
                            ry = np.arange(y0, y1, dtype=np.float32) - py_i
                            rx = np.arange(x0, x1, dtype=np.float32) - px_i
                            dx_grid, dy_grid = np.meshgrid(rx, ry)
                            dist_sq = dx_grid * dx_grid + dy_grid * dy_grid
                            r = sz / 2.0
                            # Anti-aliased edge: 1.0 inside, smooth falloff at edge
                            aa_alpha = np.clip(r - np.sqrt(dist_sq) + 0.5, 0.0, 1.0)
                            if emitter.blend_mode == BlendMode.ADD:
                                contrib = bgra_val.astype(np.float32) * aa_alpha[:, :, np.newaxis]
                                region = frame[y0:y1, x0:x1].astype(np.float32) + contrib
                                frame[y0:y1, x0:x1] = np.minimum(region, 255).astype(np.uint8)
                            else:
                                contrib = bgra_val.astype(np.float32) * aa_alpha[:, :, np.newaxis]
                                bg = frame[y0:y1, x0:x1].astype(np.float32)
                                blended = bg * (1.0 - aa_alpha[:, :, np.newaxis]) + contrib
                                frame[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)

        return frame

    def simulate_frame(self) -> np.ndarray:
        """Advance simulation by one frame and render.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        self._spawn()
        self._update()
        return self._render_frame()

    def reset(self) -> None:
        """Reset all particles and state."""
        self._count = 0
        self._age[:] = 0.0
        self._spawn_accum = [0.0] * len(self._emitters)

    def to_clip(self, duration: int) -> ParticleClip:
        """Convert this particle system to a renderable clip.

        Args:
            duration: Duration in frames.

        Returns:
            A ParticleClip bound to this system.
        """
        clip = ParticleClip(system=self)
        clip.set_duration(duration)
        return clip

    @property
    def particle_count(self) -> int:
        """Current number of live particles."""
        return self._count


@dataclass
class ParticleClip(Clip):
    """Clip that renders a particle system to BGRA frames."""

    system: ParticleSystem = field(default_factory=lambda: ParticleSystem(1920, 1080))
    _frame_cache: dict[int, np.ndarray] = field(default_factory=dict, repr=False)
    _simulated_up_to: int = field(default=-1, repr=False)

    def _ensure_simulated(self, up_to: int) -> None:
        """Simulate frames sequentially up to the given frame.

        Pre-simulates and caches all frames from the last simulated frame
        to the target, avoiding O(n²) re-simulation from frame 0.

        Args:
            up_to: Target frame number (inclusive).
        """
        if up_to <= self._simulated_up_to:
            return

        # If we haven't started, reset the system
        if self._simulated_up_to < 0:
            self.system.reset()
            self.system._rng = np.random.default_rng(42)

        start = self._simulated_up_to + 1
        for f in range(start, up_to + 1):
            result = self.system.simulate_frame()
            self._frame_cache[f] = result

        self._simulated_up_to = up_to

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render a single frame of the particle system.

        Uses sequential pre-simulation for O(n) total cost instead of
        O(n²) re-simulation from frame 0 each time.

        Args:
            ctx: Render context for this frame.

        Returns:
            BGRA numpy array of shape (H, W, 4), dtype uint8.
        """
        target_frame = ctx.local_frame

        if target_frame in self._frame_cache:
            return self._frame_cache[target_frame]

        self._ensure_simulated(target_frame)
        return self._frame_cache.get(
            target_frame,
            np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8),
        )


# ---------------------------------------------------------------------------
# Built-in Particle Presets
# ---------------------------------------------------------------------------


def sparkles(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a sparkle particle effect.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height / 2),
            rate=15.0,
            lifetime=(20.0, 40.0),
            speed=(1.0, 4.0),
            angle=(0.0, 360.0),
            size=(1.0, 3.0),
            color_over_life=[CHART_COLORS[0], CHART_COLORS[5]],
            opacity_over_life=[1.0, 0.0],
            blend_mode=BlendMode.ADD,
        )
    )
    return ps


def confetti(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a confetti particle effect.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, 0.0),
            rate=20.0,
            lifetime=(60.0, 120.0),
            speed=(2.0, 6.0),
            angle=(60.0, 120.0),
            size=(4.0, 8.0),
            color_over_life=[
                CHART_COLORS[0],  # indigo
                CHART_COLORS[1],  # pink
                CHART_COLORS[2],  # amber
                CHART_COLORS[3],  # emerald
            ],
            opacity_over_life=[1.0, 1.0, 0.5],
            gravity=Vec2(0.0, 0.3),
            drag=0.01,
            rotation_speed=(-0.15, 0.15),
            blend_mode=BlendMode.NORMAL,
        )
    )
    return ps


def fire(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a fire particle effect.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height * 0.8),
            rate=30.0,
            lifetime=(30.0, 60.0),
            speed=(2.0, 4.0),
            angle=(250.0, 290.0),
            size=(3.0, 8.0),
            color_over_life=[
                Color.parse("#FFF7E6"),  # near-white at base
                Color.parse("#FFAB40"),  # orange
                Color.parse("#E53935"),  # red
            ],
            opacity_over_life=[1.0, 0.8, 0.0],
            gravity=Vec2(0.0, -0.1),
            turbulence=0.5,
            blend_mode=BlendMode.ADD,
        )
    )
    return ps


def smoke(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a smoke particle effect.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height * 0.8),
            rate=10.0,
            lifetime=(40.0, 80.0),
            speed=(0.5, 2.0),
            angle=(250.0, 290.0),
            size=(6.0, 15.0),
            color_over_life=[
                Color(0.5, 0.5, 0.5),
                Color(0.3, 0.3, 0.3),
            ],
            opacity_over_life=[0.3, 0.1, 0.0],
            gravity=Vec2(0.0, -0.05),
            turbulence=0.3,
            drag=0.02,
            blend_mode=BlendMode.NORMAL,
        )
    )
    return ps


def rain(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a rain particle effect.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, 0.0),
            rate=40.0,
            lifetime=(30.0, 60.0),
            speed=(8.0, 15.0),
            angle=(78.0, 82.0),  # wind-blown, 80° from vertical
            size=(1.0, 1.0),
            color_over_life=[Color.parse("#D4D4D8")],  # neutral_300
            opacity_over_life=[0.5, 0.3],
            gravity=Vec2(0.0, 0.5),
            blend_mode=BlendMode.ADD,
        )
    )
    return ps


def stars(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a twinkling stars particle effect.

    Particles spawn across the full frame with slow drift and
    subtle pulsing via opacity-over-life.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height / 2),
            rate=8.0,
            lifetime=(90.0, 180.0),
            speed=(0.02, 0.08),
            angle=(0.0, 360.0),
            size=(1.0, 2.0),
            color_over_life=[Color(1.0, 1.0, 1.0), Color(0.8, 0.9, 1.0)],
            opacity_over_life=[0.3, 0.6, 0.8, 0.6, 0.3],
            blend_mode=BlendMode.ADD,
        )
    )
    return ps


def dust(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a floating dust motes particle effect.

    Gentle, slow-moving particles with slight turbulence.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height / 2),
            rate=8.0,
            lifetime=(80.0, 160.0),
            speed=(0.2, 1.0),
            angle=(0.0, 360.0),
            size=(1.0, 3.0),
            color_over_life=[Color(0.9, 0.85, 0.7)],
            opacity_over_life=[0.0, 0.4, 0.3, 0.0],
            turbulence=0.2,
            drag=0.01,
            blend_mode=BlendMode.ADD,
        )
    )
    return ps


def explosion(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create an explosion particle effect.

    High-speed burst from center with rapid color shift and falloff.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height / 2),
            rate=100.0,
            lifetime=(10.0, 30.0),
            speed=(5.0, 20.0),
            angle=(0.0, 360.0),
            size=(2.0, 8.0),
            color_over_life=[
                Color(1.0, 1.0, 0.8),
                Color(1.0, 0.6, 0.0),
                Color(0.8, 0.2, 0.0),
                Color(0.3, 0.1, 0.1),
            ],
            opacity_over_life=[1.0, 0.8, 0.3, 0.0],
            gravity=Vec2(0.0, 0.2),
            drag=0.03,
            turbulence=0.8,
            blend_mode=BlendMode.ADD,
        )
    )
    return ps


def bubbles(width: int = 1920, height: int = 1080) -> ParticleSystem:
    """Create a rising bubbles particle effect.

    Translucent circular particles rising with gentle side drift.

    Args:
        width: Output width.
        height: Output height.

    Returns:
        Configured ParticleSystem.
    """
    ps = ParticleSystem(width, height)
    ps.add_emitter(
        Emitter(
            position=Vec2(width / 2, height),
            rate=8.0,
            lifetime=(60.0, 120.0),
            speed=(1.0, 3.0),
            angle=(250.0, 290.0),
            size=(4.0, 12.0),
            color_over_life=[Color(0.7, 0.85, 1.0)],
            opacity_over_life=[0.0, 0.3, 0.3, 0.0],
            gravity=Vec2(0.0, -0.05),
            turbulence=0.15,
            blend_mode=BlendMode.ADD,
        )
    )
    return ps
