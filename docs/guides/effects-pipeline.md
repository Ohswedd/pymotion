# Effects Pipeline

PyMotion includes a library of visual effects that transform BGRA frames.
Effects are stateless -- they receive a frame and a render context, and
return a new frame with the effect applied.

## How effects work

Every effect inherits from `Effect` and implements a single method:

```python
def apply(self, frame: np.ndarray, ctx: RenderContext) -> np.ndarray:
```

The `frame` is a BGRA uint8 numpy array of shape `(H, W, 4)`. The `ctx`
provides the current frame number, progress, and resolution. Effects must
return an array of the same shape without mutating the input.

## Adding effects to clips

Use `add_effect()` on any clip. Effects are applied in order during rendering:

```python
from pymotion import (
    Composition, ColorClip, TextClip,
    GaussianBlur, Vignette, FilmGrain,
)

comp = Composition(1920, 1080, fps=30, duration=90)

bg = ColorClip("#1a1a2e")
bg.set_duration(90)
bg.add_effect(Vignette(strength=0.6, radius=0.8))
bg.add_effect(FilmGrain(strength=0.2, monochrome=True))

title = TextClip("Cinematic", font_size=72, color="#ffffff")
title.set_position(960, 540)
title.set_duration(90)
title.add_effect(GaussianBlur(radius=1.5))

comp.add(bg, title)
comp.render("effects_demo.mp4")
```

## Visual effects

### Blur and sharpen

```python
from pymotion import GaussianBlur, MotionBlur, Sharpen

GaussianBlur(radius=5.0)
MotionBlur(angle=45.0, distance=10.0)
Sharpen(amount=1.5)
```

### Film and lens effects

```python
from pymotion import Vignette, FilmGrain, ChromaticAberration, Bloom, Glow

Vignette(strength=0.5, radius=0.8, feather=0.3)
FilmGrain(strength=0.3, size=1.0, monochrome=True)
ChromaticAberration(offset=3.0, angle=0.0)
Bloom(radius=10.0, strength=0.5, threshold=200.0, iterations=3)
Glow(radius=10.0, strength=0.5, threshold=200.0)
```

### Light effects

```python
from pymotion import NeonGlow, LightLeak, GodRays, LensFlareLight, Vec2

NeonGlow(color="#00FFFF", radius=8.0, strength=0.7)
LightLeak(color="#FF9933", position=Vec2(0.8, 0.3), intensity=0.5)
GodRays(position=Vec2(0.5, 0.0), intensity=0.5, decay=0.95)
LensFlareLight(position=Vec2(0.3, 0.2), intensity=0.8, color="#FFF2CC")
```

## Color effects

### Brightness, Contrast, Saturation

These use a `value` parameter where `1.0` means no change:

```python
from pymotion import Brightness, Contrast, Saturation

Brightness(value=1.2)      # 20% brighter
Contrast(value=1.3)        # more contrast
Saturation(value=0.5)      # half saturation (desaturated)
```

### HSL and color balance

```python
from pymotion import HueSaturationLuminance, ColorBalance

HueSaturationLuminance(hue=30.0, saturation=1.2, luminance=0.05)
ColorBalance(shadows="#001133", midtones="#000000", highlights="#332200")
```

### Split toning and bleach bypass

```python
from pymotion import SplitToning, BleachBypass

SplitToning(highlights_color="#FFE6CC", shadows_color="#334D80", balance=0.0)
BleachBypass(strength=0.5)
```

### Curves

Control per-channel tone curves with control points:

```python
from pymotion import Curves

Curves(
    rgb_curve=[(0, 0), (64, 50), (192, 210), (255, 255)],
    r_curve=[(0, 0), (255, 240)],
)
```

### LUT grading

Apply a `.cube` LUT file for cinematic color grading:

```python
from pymotion import LUTEffect

lut = LUTEffect(lut_path="assets/luts/cinematic.cube", intensity=0.8)
```

The `intensity` parameter blends between the original and graded image
(0.0 = original, 1.0 = fully graded).

## Distortion effects

```python
from pymotion import WaveWarp, Ripple, Twirl, Fisheye, Vec2

WaveWarp(amplitude=10.0, frequency=0.05, axis="x")
Ripple(center=Vec2(0.5, 0.5), amplitude=10.0, frequency=0.1)
Twirl(center=Vec2(0.5, 0.5), angle=1.0, radius=100.0)
Fisheye(strength=0.5)
```

## Keying effects

Keying effects remove parts of a frame based on color or luminance for
compositing. See the [Keying guide](keying.md) for full details.

```python
from pymotion.effects.keying import ChromaKey, LumaKey, ColorKey, DifferenceKey

# Green screen removal
ChromaKey(color="#00FF00", tolerance=0.3, edge_softness=0.05)

# Remove dark areas
LumaKey(threshold=0.2, softness=0.1)

# Key any color
ColorKey(color="#FF0000", tolerance=0.25)

# Key by difference from a reference frame
DifferenceKey(reference_frame=0, threshold=0.15)
```

## Stacking effects

Effects are applied in order. The output of one effect becomes the input
of the next:

```python
clip.add_effect(Brightness(value=1.1))
clip.add_effect(Contrast(value=1.2))
clip.add_effect(Vignette(strength=0.4))
clip.add_effect(FilmGrain(strength=0.15))
```

## Tips

- Effects are stateless. The same effect instance can safely be shared
  across multiple clips.
- Use `ctx.progress` (0.0 to 1.0) inside custom effects to animate
  parameters over the clip's lifetime.
- The internal frame format is BGRA uint8. Effects that do math should
  convert to float32, operate, then clip back to uint8.
- For LUT grading, the `.cube` format indexes as R-varies-fastest, stored
  internally as `[b, g, r]`.
