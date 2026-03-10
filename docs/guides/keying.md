# Keying Effects

Keying effects remove parts of a frame based on color or luminance,
producing transparent regions for compositing. PyMotion includes four
keying modes plus shared utilities for edge refinement.

## Chroma key

Remove a green or blue screen using YCbCr chroma distance:

```python
from pymotion import Composition, VideoClip, ColorClip, Track
from pymotion.effects.keying import ChromaKey

comp = Composition(1920, 1080, fps=30, duration=150)

bg_track = Track(name="background")
bg = ColorClip("#1a1a2e")
bg.set_duration(150)
bg_track.add(bg)

fg_track = Track(name="foreground")
footage = VideoClip("greenscreen.mp4")
footage.add_effect(ChromaKey(
    color="#00FF00",       # key color
    tolerance=0.3,         # chroma distance threshold
    edge_softness=0.05,   # feather width
    spill_suppression=0.5, # remove green spill from edges
))
fg_track.add(footage)

comp.add_track(bg_track)
comp.add_track(fg_track)
comp.render("keyed.mp4")
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `color` | `"#00FF00"` | Key color (hex string, CSS name, or Color) |
| `tolerance` | `0.3` | Chroma distance threshold (0.0 - 1.0) |
| `edge_softness` | `0.05` | Feather width for soft edges |
| `spill_suppression` | `0.5` | Strength of color spill removal |

## Luma key

Key based on luminance threshold -- useful for removing black or white
backgrounds:

```python
from pymotion.effects.keying import LumaKey

# Remove dark areas
clip.add_effect(LumaKey(threshold=0.2, softness=0.1))

# Remove bright areas
clip.add_effect(LumaKey(threshold=0.8, softness=0.1, invert=True))
```

## Color key

Key any arbitrary color using weighted RGB distance:

```python
from pymotion.effects.keying import ColorKey

clip.add_effect(ColorKey(
    color="#FF0000",
    tolerance=0.25,
    softness=0.1,
))
```

## Difference key

Key based on pixel difference from a reference frame. Useful for
removing a static background when you have a clean plate:

```python
from pymotion.effects.keying import DifferenceKey

clip.add_effect(DifferenceKey(
    reference_frame=0,  # frame index to use as clean plate
    threshold=0.15,
    softness=0.05,
))
```

## Shared utilities

All keying effects use these internal utilities for edge refinement:

- **`_feather_mask`** -- Gaussian blur on the alpha mask for soft edges.
- **`_choke_mask`** -- Erode or dilate the mask to shrink or expand the keyed area.
- **`_despill`** -- Remove color spill (green/blue fringing) from edge pixels.

These are applied automatically based on the effect parameters.

## Tips

- Start with a higher `tolerance` and reduce until the key is clean.
- Use `edge_softness` to avoid hard, jagged edges.
- `spill_suppression` prevents colored fringing on hair and edges.
- For best results, light green screens evenly to minimize luminance variation.
- Stack a `ChromaKey` with `Brightness` or `Contrast` to clean up difficult shots.
