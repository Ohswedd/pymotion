# Transitions

PyMotion ships with 39 built-in transitions for blending between clips.
Transitions are standalone objects that take two BGRA frames and a progress
value, and return a blended frame.

## How transitions work

Every transition inherits from `Transition` and implements `render_frame()`:

```python
def render_frame(
    self,
    clip_a: np.ndarray,   # outgoing clip (BGRA uint8)
    clip_b: np.ndarray,   # incoming clip (BGRA uint8)
    progress: float,      # 0.0 = all A, 1.0 = all B
) -> np.ndarray:
```

The `duration` parameter (in frames) controls how long the transition takes.

## Basic usage

Create transition objects and add sequential clips to a composition.
Overlap the clip timings by the transition duration so frames from both
clips are available during the blend:

```python
from pymotion import (
    Composition, ColorClip, TextClip,
    Fade, CrossDissolve, SlideLeft,
)

comp = Composition(1920, 1080, fps=30, duration=270)

# Three scenes, each 90 frames
scene_a = ColorClip("#e63946")
scene_a.set_duration(90)

scene_b = ColorClip("#457b9d")
scene_b.set_duration(90).at(90)

scene_c = ColorClip("#2a9d8f")
scene_c.set_duration(90).at(180)

# Transition objects
fade = Fade(duration=15)
cross = CrossDissolve(duration=20)
slide = SlideLeft(duration=15)

comp.add(scene_a, scene_b, scene_c)
comp.render("transitions.mp4")
```

## Available transitions

### Basic

| Transition | Description |
|------------|-------------|
| `Fade` | A fades out while B fades in. |
| `CrossDissolve` | Linear blend from A to B. |
| `Cut` | Instant switch at the midpoint. |
| `FadeToBlack` | Dip to black, then reveal B. |
| `FadeToWhite` | Dip to white, then reveal B. |
| `DipToColor` | Dip to a custom color, then reveal B. |

### Directional -- Slide

```python
from pymotion import SlideLeft, SlideRight, SlideUp, SlideDown

SlideLeft(duration=15)
SlideRight(duration=15)
SlideUp(duration=15)
SlideDown(duration=15)
```

Both clips slide together in the specified direction.

### Directional -- Push

```python
from pymotion import PushLeft, PushRight, PushUp, PushDown

PushLeft(duration=15)
```

B pushes A out of frame in the given direction.

### Directional -- Cover and Reveal

```python
from pymotion import CoverLeft, CoverRight, CoverUp, CoverDown
from pymotion import RevealLeft, RevealRight, RevealUp, RevealDown

CoverLeft(duration=15)    # B slides in from the right, covering A
RevealLeft(duration=15)   # A slides away, revealing B beneath
```

### Zoom

```python
from pymotion import ZoomIn, ZoomOut, ZoomBlur, ScaleDissolve

ZoomIn(duration=20)        # A zooms in while fading to B
ZoomOut(duration=20)       # B zooms out from large to normal
ZoomBlur(duration=20)      # A blurs outward while fading to B
ScaleDissolve(duration=20) # A scales down while dissolving to B
```

### Wipe

```python
from pymotion import WipeLeft, WipeRight, WipeDiagonal, CircularWipe

WipeLeft(duration=20)      # B revealed from right to left
WipeRight(duration=20)     # B revealed from left to right
WipeDiagonal(duration=20)  # Diagonal boundary sweeps across
CircularWipe(duration=20)  # Expanding circle from center
```

### Advanced

```python
from pymotion import (
    IrisIn, IrisOut, PixelDissolve, Glitch,
    FilmBurn, PageTurn, Vortex, Shatter, MorphWarp,
)

IrisIn(duration=20)                    # Expanding circle reveals B
IrisOut(duration=20)                   # Shrinking circle reveals B
PixelDissolve(duration=30, seed=42)    # Random pixels switch from A to B
Glitch(duration=20, seed=42)           # Random slice shifts with color separation
FilmBurn(duration=25)                  # Bright overexposure wipe
PageTurn(duration=30)                  # A peels away like a turning page
Vortex(duration=30)                    # Pixels swirl from A to B
Shatter(duration=30, grid_size=6)      # A breaks into falling pieces
MorphWarp(duration=30)                 # Sinusoidal warp morphs A into B
```

## DipToColor example

Fade through a custom color between scenes:

```python
from pymotion import DipToColor

dip = DipToColor(duration=30, color="#1a1a2e")
```

## Tips

- The `duration` parameter is always specified in frames.
- Transitions with a `seed` parameter (like `PixelDissolve`, `Glitch`, and
  `Shatter`) produce deterministic results -- the same seed always gives the
  same pattern.
- All transitions operate on BGRA uint8 numpy arrays and return the same
  format.
- For smooth results, overlap clip timings by the transition duration so
  both clips render during the blend window.
