# Compositing

PyMotion supports nested compositions, adjustment layers, and clip
parenting for complex multi-layer projects.

## Nested compositions (pre-comps)

Wrap a `Composition` in a `CompositionClip` to treat it as a single clip
inside a parent composition. This lets you group layers, apply effects to
the group, and reuse motion graphics across projects.

```python
from pymotion import Composition, ColorClip, TextClip, Track

# Build the inner composition
inner = Composition(960, 540, fps=30, duration=90)
inner_track = Track(name="inner")
bg = ColorClip("#e94560").set_duration(90)
label = TextClip("SALE", font="Arial", size=48.0, color="#FFFFFF")
label.set_duration(90).set_position(400.0, 250.0)
inner_track.add(bg)
inner_track.add(label)
inner.add_track(inner_track)

# Nest it as a clip in the outer composition
outer = Composition(1920, 1080, fps=30, duration=90)
nested = inner.to_clip()
nested.set_duration(90).set_position(960.0, 540.0)

main_track = Track(name="main")
main_track.add(nested)
outer.add_track(main_track)
outer.render("nested.mp4")
```

### Resolution and frame rate

A `CompositionClip` can have a different resolution and fps from its
parent. Frames are automatically scaled and remapped:

```python
# Inner comp at 720p, parent at 1080p -- auto-scaled
inner = Composition(1280, 720, fps=24, duration=72)
# ...
nested = inner.to_clip()
nested.set_duration(90)  # 90 frames at parent's 30 fps
```

Nesting is supported up to 10 levels deep. A shared LRU cache avoids
redundant frame renders when the same nested composition appears on
multiple tracks.

---

## Adjustment layers

An `AdjustmentLayer` applies its effects to every layer below it in the
same composition, like a global color grade or blur that affects all
underlying clips.

```python
from pymotion import (
    Composition, AdjustmentLayer, ColorClip, TextClip, Track,
    Vignette, Brightness,
)

comp = Composition(1920, 1080, fps=30, duration=90)

bg_track = Track(name="bg")
bg = ColorClip("#1a1a2e").set_duration(90)
bg_track.add(bg)

text_track = Track(name="text")
title = TextClip("Hello", font="Arial", size=72.0, color="#FFFFFF")
title.set_duration(90).set_position(800.0, 500.0)
text_track.add(title)

# Adjustment layer on top
fx_track = Track(name="adjust")
adj = AdjustmentLayer()
adj.set_duration(90)
adj.add_effect(Vignette(strength=0.5))
adj.add_effect(Brightness(value=1.1))
fx_track.add(adj)

comp.add_track(bg_track)
comp.add_track(text_track)
comp.add_track(fx_track)
comp.render("adjusted.mp4")
```

The vignette and brightness are applied to the flattened result of all
tracks below the adjustment layer. The adjustment layer itself renders
as fully transparent -- it only contributes effects.

### Opacity

Set `adj.set_opacity(0.5)` to blend the adjusted result at 50% with the
un-adjusted original, creating a subtle effect.

---

## Parenting (clip hierarchy)

Any clip can be set as the parent of another. The child inherits the
parent's position, scale, and rotation transforms:

```python
from pymotion import NullObject, ColorClip

group = NullObject()
group.set_position(960.0, 540.0)
group.set_rotation(15.0)

box = ColorClip("#e94560").set_duration(90)
box.parent = group
box.set_position(100.0, 0.0)  # offset from parent
```

When `group` rotates, `box` orbits around the parent's center.

### NullObject

A `NullObject` is an invisible clip that carries transforms without
rendering anything. Use it as a group anchor:

```python
pivot = NullObject()
pivot.set_position(960.0, 540.0)
pivot.set_duration(90)

for i in range(5):
    dot = ColorClip("#FFFFFF").set_duration(90)
    dot.parent = pivot
    dot.set_position(float(i * 80), 0.0)
```

Moving or rotating `pivot` moves all five dots together.

### Transform inheritance rules

| Property | Rule |
|----------|------|
| Position | Child position is scaled by parent scale, then rotated by parent rotation, then added to parent position |
| Scale | Multiplied (parent 2.0 x child 0.5 = effective 1.0) |
| Rotation | Summed (parent 15 + child 30 = effective 45 degrees) |
| Opacity | Independent (not inherited) |

## Tips

- Pre-compositions are ideal for grouping a title card (background +
  text + decoration) into one reusable clip.
- Adjustment layers affect all tracks added *before* them. Put them
  on the highest track to affect everything.
- Parenting is resolved per-frame, so animated parent transforms
  propagate automatically to children.
- Circular parenting (A parents B, B parents A) raises a `ValueError`.
