# Masking

Masks control which parts of a clip are visible by defining alpha regions.
PyMotion provides shape masks, gradient masks, track mattes, and text
masks, all combinable with boolean operations.

## Adding masks to clips

Use `add_mask()` to attach one or more masks. Masks are evaluated during
rendering and multiplied into the clip's alpha channel:

```python
from pymotion import ColorClip, BezierMask, BezierPoint, MaskOp, Vec2

clip = ColorClip("#e94560").set_duration(90)

mask = BezierMask(points=[
    BezierPoint(vertex=Vec2(100.0, 100.0)),
    BezierPoint(vertex=Vec2(300.0, 50.0)),
    BezierPoint(vertex=Vec2(300.0, 250.0)),
    BezierPoint(vertex=Vec2(100.0, 250.0)),
])

clip.add_mask(mask)
```

The clip is now visible only inside the bezier shape.

---

## Mask types

### BezierMask

A closed bezier path rasterized with Cairo. Supports control handles for
smooth curves:

```python
from pymotion import BezierMask, BezierPoint, Vec2

# Rectangle
rect_mask = BezierMask(points=[
    BezierPoint(vertex=Vec2(50.0, 50.0)),
    BezierPoint(vertex=Vec2(350.0, 50.0)),
    BezierPoint(vertex=Vec2(350.0, 250.0)),
    BezierPoint(vertex=Vec2(50.0, 250.0)),
])

# Curved shape with control handles
curved = BezierMask(points=[
    BezierPoint(
        vertex=Vec2(100.0, 200.0),
        out_handle=Vec2(150.0, 50.0),
    ),
    BezierPoint(
        vertex=Vec2(300.0, 200.0),
        in_handle=Vec2(250.0, 50.0),
    ),
])
```

#### Animated masks

Animate mask points over time with `set_points_at()`:

```python
mask = BezierMask(points=[
    BezierPoint(vertex=Vec2(100.0, 100.0)),
    BezierPoint(vertex=Vec2(300.0, 100.0)),
    BezierPoint(vertex=Vec2(300.0, 300.0)),
    BezierPoint(vertex=Vec2(100.0, 300.0)),
])

# At frame 60, expand the mask
mask.set_points_at(60, [
    BezierPoint(vertex=Vec2(50.0, 50.0)),
    BezierPoint(vertex=Vec2(350.0, 50.0)),
    BezierPoint(vertex=Vec2(350.0, 350.0)),
    BezierPoint(vertex=Vec2(50.0, 350.0)),
])
```

Between keyframes, points are linearly interpolated.

### LinearGradientMask

A gradient that fades from hidden to visible along a line:

```python
from pymotion import LinearGradientMask, Vec2

grad = LinearGradientMask(
    start=Vec2(0.0, 0.0),
    end=Vec2(400.0, 0.0),
)
```

### RadialGradientMask

A circular gradient fading outward from a center point:

```python
from pymotion import RadialGradientMask, Vec2

radial = RadialGradientMask(
    center=Vec2(200.0, 150.0),
    radius=180.0,
)
```

### TrackMatte

Use another clip's luminance or alpha as a mask:

```python
from pymotion import TrackMatte, ColorClip, TextClip, MaskOp

# Text-shaped window into the background
matte_source = TextClip("HELLO", font="Arial", size=120.0, color="#FFFFFF")
matte_source.set_duration(90)

matte = TrackMatte(source=matte_source, mode="luma")

clip = ColorClip("#e94560").set_duration(90)
clip.add_mask(matte)
```

Modes: `"alpha"` uses the source's alpha channel, `"luma"` uses BT.601
luminance (0.299R + 0.587G + 0.114B).

### TextMask

Render text directly as a mask shape using Cairo:

```python
from pymotion import TextMask

text_mask = TextMask(
    text="PYMOTION",
    font="sans-serif",
    size=80.0,
)
```

---

## Boolean operations

Combine multiple masks with the `op` parameter of `add_mask()`:

| Operation | Effect |
|-----------|--------|
| `MaskOp.ADD` | Union -- visible where *any* mask is white (default) |
| `MaskOp.INTERSECT` | Intersection -- visible only where *all* masks overlap |
| `MaskOp.SUBTRACT` | Difference -- second mask cuts a hole in the first |

```python
from pymotion import MaskOp, BezierMask, BezierPoint, Vec2

circle_mask = BezierMask(points=[...])  # outer shape
hole_mask = BezierMask(points=[...])    # inner cutout

# Cut a hole
clip.add_mask(circle_mask, op=MaskOp.ADD)
clip.add_mask(hole_mask, op=MaskOp.SUBTRACT)
```

---

## Mask properties

Each mask type supports post-processing properties:

| Property | Default | Description |
|----------|---------|-------------|
| `feather` | `0.0` | Gaussian blur radius for soft edges |
| `expansion` | `0.0` | Grow (positive) or shrink (negative) the mask |
| `invert` | `False` | Flip mask (visible becomes hidden and vice versa) |
| `opacity` | `1.0` | Blend strength of the mask |

```python
mask = BezierMask(
    points=[...],
    feather=5.0,
    expansion=2.0,
    invert=False,
    opacity=0.8,
)
clip.add_mask(mask)
```

## Clearing masks

Remove all masks from a clip:

```python
clip.clear_masks()
```

## Tips

- Masks are applied *after* effects in the render pipeline:
  expressions -> render -> effects -> masks.
- Feathering uses the same Gaussian blur as keying edge softness.
- For animated reveals, combine a `LinearGradientMask` with keyframed
  start/end positions.
- `TrackMatte` renders its source clip every frame, so keep matte
  sources lightweight (text or solid colors).
