# Expressions

Expressions let you drive any animatable clip property with a Python
callable. Instead of keyframes, you write a function that receives
frame metadata and returns a value.

## Setting expressions

Use `set_expression()` on any clip. The function receives an
`ExpressionContext` and must return a `float`:

```python
from pymotion import ColorClip

clip = ColorClip("#e94560").set_duration(120)

# Move 3 pixels per frame
clip.set_expression("position.x", lambda ctx: ctx.frame * 3.0)

# Pulse opacity with a sine wave
import math
clip.set_expression("opacity", lambda ctx: 0.5 + 0.5 * math.sin(ctx.time * 4))
```

### Supported properties

| Property | Description |
|----------|-------------|
| `position.x` | Horizontal position |
| `position.y` | Vertical position |
| `scale.x` | Horizontal scale factor |
| `scale.y` | Vertical scale factor |
| `rotation` | Rotation in degrees |
| `opacity` | Opacity (clamped to 0.0-1.0) |

### ExpressionContext fields

Every expression receives an `ExpressionContext` with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `frame` | `int` | Global frame number |
| `local_frame` | `int` | Frame relative to clip start |
| `time` | `float` | Current time in seconds |
| `fps` | `int` | Composition frame rate |
| `progress` | `float` | Progress through clip (0.0-1.0) |
| `comp_width` | `int` | Composition width in pixels |
| `comp_height` | `int` | Composition height in pixels |

```python
from pymotion import ExpressionContext

def bounce(ctx: ExpressionContext) -> float:
    """Bounce position from top to bottom."""
    return ctx.comp_height * abs(math.sin(ctx.time * 2))

clip.set_expression("position.y", bounce)
```

---

## Expression helpers

### wiggle

Smooth random oscillation, similar to After Effects' `wiggle()`:

```python
from pymotion import wiggle

# 2 oscillations per second, 50px amplitude
clip.set_expression("position.x", wiggle(2.0, 50.0))

# Reproducible with a seed
clip.set_expression("position.y", wiggle(3.0, 30.0, seed=42))
```

The noise is deterministic -- the same seed and frame always produce the
same value.

### loop_in / loop_out

Loop the first or last N frames of an expression:

```python
from pymotion import loop_in, loop_out

# A ramp that loops every 30 frames at the start
ramp = lambda ctx: float(ctx.local_frame) * 2.0
clip.set_expression("position.x", loop_in(30, ramp))

# Loop the last 20 frames at the end
clip.set_expression("rotation", loop_out(20, lambda ctx: ctx.local_frame * 6.0))
```

`loop_in` repeats the first `duration_frames` frames indefinitely.
`loop_out` repeats the last `duration_frames` frames.

---

## Linking expressions between clips

Read one clip's animated property to drive another:

```python
from pymotion import ColorClip

leader = ColorClip("#FF0000").set_duration(120)
leader.set_opacity(0.7)

follower = ColorClip("#00FF00").set_duration(120)
follower.set_expression("opacity", lambda ctx: leader.opacity_at(ctx.frame))
```

The follower's opacity will always match the leader's.

---

## Clearing expressions

Remove all expressions from a clip:

```python
clip.clear_expressions()
```

## Tips

- Expressions are evaluated *before* `render_frame()` in the pipeline:
  expressions -> render -> effects -> masks.
- Opacity values are automatically clamped to 0.0-1.0.
- For complex motion, combine expressions with keyframe animation --
  use keyframes for the main path and expressions for secondary motion
  like wiggle.
- Expression functions should be fast. They run once per property per
  frame, so avoid heavy I/O or computation inside them.
