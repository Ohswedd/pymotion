# AI Background & Object Manipulation

PyMotion v2.0 provides AI-powered effects for removing backgrounds,
segmenting objects, inpainting, and outpainting. All AI features are
optional — install with `pip install "pymotion-studio[ai]"`.

## Removing backgrounds

`RemoveBackground` uses [rembg](https://github.com/danielgatis/rembg)
to strip the background and produce a clip with alpha transparency:

```python
from pymotion import RemoveBackground

effect = RemoveBackground(model="u2net")
# Apply via the standard effects pipeline:
# result = effect.apply(frame, ctx)
```

The `model` parameter accepts any rembg model name: `"u2net"`,
`"u2netp"`, `"u2net_human_seg"`, `"silueta"`, `"isnet-general-use"`.

Sessions are cached internally — the first frame loads the model,
subsequent frames reuse it.

## Replacing backgrounds

`ReplaceBackground` combines background removal with compositing over
a new background image:

```python
from pymotion import ReplaceBackground
import numpy as np

# A solid blue background (BGRA uint8)
new_bg = np.zeros((1080, 1920, 4), dtype=np.uint8)
new_bg[:, :, 0] = 180  # B
new_bg[:, :, 3] = 255  # A

effect = ReplaceBackground(background=new_bg, model="u2net")
```

The foreground is composited onto `background` using alpha blending
with uint16 fixed-point math for accuracy.

## Object segmentation

`ObjectSegmentation` uses Segment Anything Model (SAM) with a text
prompt to isolate specific objects:

```python
from pymotion import ObjectSegmentation

effect = ObjectSegmentation(prompt="the cat on the sofa")
# Returns a frame with only the segmented object visible (alpha mask)
```

This requires `segment-anything` and `transformers` packages. The
model is loaded on first use and cached for subsequent frames.

## Removing objects

`RemoveObject` inpaints over a masked region to remove unwanted
objects from the scene:

```python
from pymotion import RemoveObject
import numpy as np

# Binary mask — white (255) where the object should be removed
mask = np.zeros((1080, 1920), dtype=np.uint8)
mask[200:400, 300:600] = 255

effect = RemoveObject(mask=mask)
```

The effect uses diffusion-based inpainting to fill the masked region
with plausible content matching the surrounding area.

## Extending frames (outpainting)

`ExtendFrame` uses AI outpainting to extend frame edges beyond their
original boundaries:

```python
from pymotion import ExtendFrame

# Extend 200 pixels to the right
effect = ExtendFrame(direction="right", amount=200)
```

Valid directions: `"left"`, `"right"`, `"top"`, `"bottom"`.

The effect pads the frame, runs diffusion inpainting on the new
region, then resizes back to the original dimensions.
