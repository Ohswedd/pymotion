# Path Animation

Animate clips along SVG paths, create draw-on stroke effects, and
morph between shapes.

## Following a path

Use `follow_path()` to move a clip's center along an SVG path over a
set number of frames:

```python
from pymotion import ColorClip

clip = ColorClip("#e94560").set_duration(120)

# Move along an L-shaped path
clip.follow_path("M 100 100 L 500 100 L 500 400", duration=120)
```

The clip will travel from (100, 100) to (500, 100) to (500, 400) over
120 frames, with position expressions set automatically.

### Curve paths

SVG cubic bezier curves (`C` command) create smooth motion:

```python
clip.follow_path(
    "M 100 300 C 200 100 400 100 500 300",
    duration=90,
)
```

### Rotation alignment

By default, the clip rotates to face the direction of travel. Disable
this with `align=False`:

```python
clip.follow_path("M 0 0 L 500 300", duration=60, align=False)
```

### Supported SVG commands

| Command | Description |
|---------|-------------|
| `M` / `m` | Move to (absolute / relative) |
| `L` / `l` | Line to |
| `C` / `c` | Cubic bezier |
| `Z` / `z` | Close path |

The standalone function is also available:

```python
from pymotion import follow_path

follow_path(clip, "M 0 0 L 100 100", duration=60)
```

---

## Stroke animation (draw-on effect)

`StrokeClip` renders a stroked SVG path with animatable trim parameters
for draw-on and draw-off effects:

```python
from pymotion import StrokeClip, Composition, Track, animate, Keyframe

stroke = StrokeClip(
    path="M 100 200 C 300 50 500 350 700 200",
    stroke_color="#D4AF37",
    stroke_width=3.0,
    trim_start=0.0,
    trim_end=0.0,
)
stroke.set_duration(90)

# Animate trim_end from 0 to 1 for a draw-on effect
stroke.trim_end = animate([
    Keyframe(0, 0.0),
    Keyframe(89, 1.0),
])
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `path` | `""` | SVG path data string |
| `trim_start` | `0.0` | Start of visible portion (0.0-1.0) |
| `trim_end` | `1.0` | End of visible portion (0.0-1.0) |
| `stroke_color` | `"#FFFFFF"` | Stroke color |
| `stroke_width` | `2.0` | Stroke width in pixels |

Set `trim_start` > 0 for a partial stroke. Animate both `trim_start`
and `trim_end` together for a traveling segment effect.

---

## Path morphing

Interpolate between two SVG paths with `morph_paths()`:

```python
from pymotion import morph_paths

path_a = "M 100 100 L 300 100 L 300 300 L 100 300"  # square
path_b = "M 200 50 L 350 200 L 200 350 L 50 200"    # diamond

# Halfway between square and diamond
result = morph_paths(path_a, path_b, progress=0.5)
```

Both paths must have the same number of segments and command structure.

### ShapeClip.morph

Apply morphing directly to a `ShapeClip`:

```python
from pymotion import ShapeClip

shape = ShapeClip.rect(100, 100, 200, 200)
shape.set_duration(90)

shape.morph(
    "M 100 100 L 300 100 L 300 300 L 100 300",
    "M 200 50 L 350 200 L 200 350 L 50 200",
    progress=0.5,
)
```

This changes the shape type to `"path"` and stores the interpolated SVG
data.

---

## Tips

- Path coordinates are in pixel space relative to the composition.
- For closed shapes, end with `Z` to automatically close back to the
  start point.
- `follow_path` sets expressions on `position.x`, `position.y`, and
  optionally `rotation` -- these override any existing keyframes on
  those properties.
- Bezier curve length is approximated by subdivision (20 steps per
  segment), which is accurate for typical motion paths.
- For complex paths, export SVG path data from a vector editor like
  Figma or Inkscape and paste the `d` attribute directly.
