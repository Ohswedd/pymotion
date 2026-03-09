# Particle Systems

PyMotion provides a vectorized particle system for adding effects like
sparkles, confetti, fire, smoke, and rain to your compositions. All
particle state is stored in flat NumPy arrays for efficient batch updates.

## Quick start with presets

The fastest way to add particles is with a built-in preset function.
Each returns a configured `ParticleSystem` ready to use:

```python
from pymotion import Composition, ColorClip, sparkles

comp = Composition(1920, 1080, fps=30, duration=120)

bg = ColorClip("#0a0a23")
bg.set_duration(120)

ps = sparkles(1920, 1080)
clip = ps.to_clip(duration=120)

comp.add(bg, clip)
comp.render("sparkles.mp4")
```

## Available presets

| Preset | Effect |
|--------|--------|
| `sparkles()` | Golden sparkle burst from center. |
| `confetti()` | Colored confetti falling from the top. |
| `fire()` | Flames rising from the bottom. |
| `smoke()` | Soft smoke drifting upward. |
| `rain()` | Rainfall streaking downward. |
| `stars()` | Twinkling stars with slow drift. |
| `dust()` | Floating dust motes with gentle turbulence. |
| `explosion()` | High-speed burst from center. |
| `bubbles()` | Translucent bubbles rising upward. |

All presets accept `width` and `height` parameters (default 1920x1080).

## Custom emitters

For full control, create a `ParticleSystem` and configure your own
`Emitter`:

```python
from pymotion import ParticleSystem, Emitter, Color, Vec2, BlendMode

ps = ParticleSystem(1920, 1080)

ps.add_emitter(Emitter(
    position=Vec2(960.0, 800.0),
    rate=25.0,
    lifetime=(20.0, 50.0),
    speed=(2.0, 6.0),
    angle=(250.0, 290.0),
    size=(3.0, 7.0),
    color_over_life=[
        Color(1.0, 1.0, 0.3),
        Color(1.0, 0.4, 0.0),
        Color(0.5, 0.1, 0.0),
    ],
    opacity_over_life=[1.0, 0.6, 0.0],
    gravity=Vec2(0.0, -0.1),
    drag=0.01,
    turbulence=0.4,
    blend_mode=BlendMode.ADD,
))

clip = ps.to_clip(duration=150)
```

## Emitter parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `position` | `Vec2` | Spawn origin (x, y) in pixels. |
| `rate` | `float` | Particles spawned per frame. |
| `lifetime` | `(min, max)` | Random lifetime range in frames. |
| `speed` | `(min, max)` | Initial speed range in pixels/frame. |
| `angle` | `(min, max)` | Emission cone in degrees. |
| `size` | `(min, max)` | Particle size range in pixels. |
| `color_over_life` | `list[Color]` | Gradient colors from birth to death. |
| `opacity_over_life` | `list[float]` | Opacity values from birth to death. |
| `gravity` | `Vec2` | Per-frame velocity delta. |
| `drag` | `float` | Velocity damping per frame (0 = none). |
| `turbulence` | `float` | Random noise added to velocity. |
| `blend_mode` | `BlendMode` | `ADD` for glowing, `NORMAL` for opaque. |

## Multiple emitters

A single `ParticleSystem` can hold multiple emitters. Each emitter spawns
and controls its own particles independently:

```python
from pymotion import ParticleSystem, Emitter, Color, Vec2, BlendMode

ps = ParticleSystem(1920, 1080)

# Fire base
ps.add_emitter(Emitter(
    position=Vec2(960.0, 900.0),
    rate=30.0,
    lifetime=(15.0, 30.0),
    speed=(2.0, 5.0),
    angle=(250.0, 290.0),
    size=(3.0, 8.0),
    color_over_life=[Color(1.0, 1.0, 0.3), Color(1.0, 0.5, 0.0)],
    opacity_over_life=[1.0, 0.0],
    gravity=Vec2(0.0, -0.1),
    blend_mode=BlendMode.ADD,
))

# Ember sparks
ps.add_emitter(Emitter(
    position=Vec2(960.0, 880.0),
    rate=5.0,
    lifetime=(30.0, 60.0),
    speed=(3.0, 8.0),
    angle=(240.0, 300.0),
    size=(1.0, 2.0),
    color_over_life=[Color(1.0, 0.8, 0.2)],
    opacity_over_life=[1.0, 0.5, 0.0],
    gravity=Vec2(0.0, -0.05),
    turbulence=0.6,
    blend_mode=BlendMode.ADD,
))

clip = ps.to_clip(duration=150)
```

## Converting to a clip

Call `to_clip(duration)` on any `ParticleSystem` to get a `ParticleClip`
you can add to a composition:

```python
clip = ps.to_clip(duration=120)
comp.add(clip)
```

The particle simulation runs deterministically from frame 0, so every
render produces identical output.

## Tips

- The maximum particle count is capped at 100,000 to prevent memory issues.
- Use `BlendMode.ADD` for glowing effects (fire, sparkles, stars) and
  `BlendMode.NORMAL` for opaque particles (confetti).
- The `color_over_life` list is linearly interpolated across the particle's
  lifetime. Two colors gives a simple gradient; more colors create richer
  transitions.
- The `opacity_over_life` list works the same way. A common pattern is
  `[1.0, 0.0]` for particles that fade out as they die.
- Higher `turbulence` values make motion more chaotic -- good for smoke and
  explosions, less so for rain.
