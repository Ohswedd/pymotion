# Keyframe Animation

PyMotion provides a keyframe animation system that lets you animate any
numeric property over time. This guide covers keyframes, easing functions,
spring physics, and practical animation patterns.

## Core concepts

Animation is built from two primitives:

- **Keyframe** -- a value at a specific frame, with an easing function name.
- **KeyframeTrack** -- a sorted sequence of keyframes that interpolates between
  them.

```python
from pymotion import Keyframe, KeyframeTrack

track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=0.0),
    Keyframe(frame=30, value=100.0, easing="ease_out_cubic"),
    Keyframe(frame=60, value=100.0),
    Keyframe(frame=90, value=0.0, easing="ease_in_quad"),
])

# Query the value at any frame
position = track.value_at(15)  # interpolated between 0 and 100
```

Values before the first keyframe hold the first value. Values after the last
keyframe hold the last value.

## Animating clip properties

Use `KeyframeTrack.value_at()` inside a custom clip or by setting clip
properties per frame. A common pattern is to subclass `Clip` and read the
track value in `render_frame()`:

```python
from pymotion import (
    Composition, ColorClip, Keyframe, KeyframeTrack,
)

comp = Composition(1920, 1080, fps=30, duration=90)

bg = ColorClip("#1a1a2e")
bg.set_duration(90)

# Animate a box moving across the screen
box = ColorClip("#e94560")
box.set_size(200, 200)
box.set_duration(90)

x_track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=100.0, easing="ease_in_out_cubic"),
    Keyframe(frame=90, value=1720.0),
])

y_track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=440.0, easing="ease_out_bounce"),
    Keyframe(frame=45, value=100.0),
    Keyframe(frame=90, value=440.0, easing="ease_in_quad"),
])

# Apply animation by setting position per frame
for frame in range(90):
    x = x_track.value_at(frame)
    y = y_track.value_at(frame)
    # In practice, use this inside a custom clip's render_frame()
```

## Easing functions

PyMotion includes 30 built-in easing functions. Access them by name through
`get_easing()` or pass the name directly to `Keyframe(easing=...)`.

### Available easings

| Category | Functions |
|----------|-----------|
| Linear | `linear` |
| Quadratic | `ease_in_quad`, `ease_out_quad`, `ease_in_out_quad` |
| Cubic | `ease_in_cubic`, `ease_out_cubic`, `ease_in_out_cubic` |
| Quartic | `ease_in_quart`, `ease_out_quart` |
| Quintic | `ease_in_quint`, `ease_out_quint` |
| Sinusoidal | `ease_in_sine`, `ease_out_sine`, `ease_in_out_sine` |
| Exponential | `ease_in_expo`, `ease_out_expo`, `ease_in_out_expo` |
| Circular | `ease_in_circ`, `ease_out_circ`, `ease_in_out_circ` |
| Back | `ease_in_back`, `ease_out_back`, `ease_in_out_back` |
| Elastic | `ease_in_elastic`, `ease_out_elastic`, `ease_in_out_elastic` |
| Bounce | `ease_in_bounce`, `ease_out_bounce`, `ease_in_out_bounce` |

### Using get_easing directly

```python
from pymotion import get_easing

ease = get_easing("ease_out_elastic")
value = ease(0.5)  # returns the eased value at t=0.5
```

All easing functions take a float `t` in `[0.0, 1.0]` and return a float.

## Custom cubic bezier curves

Create CSS-compatible cubic bezier easing functions:

```python
from pymotion import cubic_bezier, Keyframe, KeyframeTrack

# CSS "ease" equivalent
ease_fn = cubic_bezier(0.25, 0.1, 0.25, 1.0)

# Use it directly
value = ease_fn(0.5)
```

Cubic bezier functions can be used anywhere an easing function is expected.
To use one in a `Keyframe`, register it first or apply it manually.

## Stepped animation

The `steps()` factory creates staircase easing functions, useful for
frame-by-frame or sprite-sheet animation:

```python
from pymotion import steps

# 4 discrete steps
step_fn = steps(4, direction="end")
step_fn(0.3)   # 0.25
step_fn(0.5)   # 0.5
step_fn(0.9)   # 0.75
step_fn(1.0)   # 1.0
```

The `direction` parameter controls when each step occurs:

- `"end"` (default) -- the value changes at the end of each interval.
- `"start"` -- the value changes at the start of each interval.

## Spring physics

The `spring()` factory creates easing functions based on a damped harmonic
oscillator. This produces natural, physically-motivated motion with optional
overshoot and oscillation.

```python
from pymotion import spring, Keyframe, KeyframeTrack

# Bouncy spring (underdamped)
bouncy = spring(stiffness=180.0, damping=12.0, mass=1.0)

# Stiff, no-overshoot spring (overdamped)
stiff = spring(stiffness=180.0, damping=40.0, mass=1.0)

# Use in a keyframe track
track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=0.0),
    Keyframe(frame=60, value=500.0),
])
```

### Spring parameters

| Parameter | Effect |
|-----------|--------|
| `stiffness` | Higher values = faster oscillation. Default: 180.0 |
| `damping` | Higher values = less oscillation. Default: 12.0 |
| `mass` | Higher values = slower, heavier feel. Default: 1.0 |

The damping ratio determines the behavior:

- **Underdamped** (ratio < 1) -- oscillates before settling.
- **Critically damped** (ratio = 1) -- fastest settling without overshoot.
- **Overdamped** (ratio > 1) -- slow settling, no overshoot.

## Animatable value types

`KeyframeTrack` can interpolate between several value types:

- **float** -- scalar values (position, opacity, size).
- **Vec2** -- 2D vectors (position, scale).
- **Vec3** -- 3D vectors (position, rotation, color components).
- **Color** -- RGBA colors with per-channel interpolation.

```python
from pymotion import Keyframe, KeyframeTrack, Color, Vec2

# Color animation
color_track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=Color.parse("#ff0000")),
    Keyframe(frame=60, value=Color.parse("#0000ff"), easing="ease_in_out_sine"),
])

# 2D position animation
pos_track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=Vec2(100.0, 100.0)),
    Keyframe(frame=60, value=Vec2(800.0, 600.0), easing="ease_out_back"),
])
```

## Multi-keyframe sequences

Chain multiple keyframes to create complex animation sequences:

```python
from pymotion import Keyframe, KeyframeTrack

opacity_track = KeyframeTrack(keyframes=[
    Keyframe(frame=0, value=0.0, easing="ease_out_quad"),   # fade in
    Keyframe(frame=30, value=1.0),                          # hold
    Keyframe(frame=60, value=1.0, easing="ease_in_quad"),   # start fade out
    Keyframe(frame=90, value=0.0),                          # fully faded
])

# Query at any frame
for frame in range(91):
    alpha = opacity_track.value_at(frame)
```

## Adding keyframes dynamically

Use `KeyframeTrack.add()` to insert keyframes after construction. The track
keeps its keyframes sorted by frame number automatically:

```python
from pymotion import Keyframe, KeyframeTrack

track = KeyframeTrack()
track.add(Keyframe(frame=0, value=0.0))
track.add(Keyframe(frame=60, value=1.0, easing="ease_out_expo"))
track.add(Keyframe(frame=30, value=0.5))  # inserted in sorted order
```
