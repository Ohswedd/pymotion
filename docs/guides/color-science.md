# Color Science

PyMotion v1.5 includes a professional color pipeline with ACES 1.3
support, HDR output presets, secondary color grading, video scopes,
and interchange format export.

## ACES color pipeline

Convert frames between sRGB and ACES AP0 color space for
scene-referred workflows:

```python
from pymotion import srgb_to_aces, aces_to_srgb
import numpy as np

# Convert a BGRA uint8 frame to ACES AP0 (float64, scene-linear)
frame = np.zeros((1080, 1920, 4), dtype=np.uint8)
aces = srgb_to_aces(frame)  # shape: (1080, 1920, 3)

# Apply grading in scene-linear space...
aces *= 1.2  # boost exposure

# Convert back to sRGB BGRA uint8 (includes ACES filmic tone mapping)
graded = aces_to_srgb(aces)  # shape: (1080, 1920, 4)
```

## HDR output presets

Two HDR output configurations are provided as dictionaries for FFmpeg
encoder flags:

```python
from pymotion import HDR10_PRESET, HLG_PRESET

print(HDR10_PRESET)
# {'transfer': 'pq', 'primaries': 'bt2020', 'bit_depth': '10', 'color_space': 'bt2020nc'}

print(HLG_PRESET)
# {'transfer': 'hlg', 'primaries': 'bt2020', 'bit_depth': '10', 'color_space': 'bt2020nc'}
```

## Color matching

`ColorMatch` transfers the color grade from a reference frame to the
current clip using the Reinhard method:

```python
from pymotion import ColorMatch
import numpy as np

reference = np.zeros((1080, 1920, 4), dtype=np.uint8)
reference[:, :, 2] = 200  # warm red-tinted reference

effect = ColorMatch(reference_frame=reference)
# Apply via the standard effects pipeline:
# clip.add_effect(effect)
```

## HSL secondary grading

`HSLSecondary` isolates pixels in a specific hue/saturation/luminance
range and applies targeted adjustments:

```python
from pymotion import HSLSecondary

# Shift sky blue hues toward teal, boost saturation
sky_grade = HSLSecondary(
    hue_range=(180.0, 240.0),      # blue sky range
    saturation_range=(0.3, 1.0),
    luminance_range=(0.4, 1.0),
    hue_shift=-20.0,               # shift toward teal
    saturation_scale=1.3,          # boost saturation
    luminance_scale=1.0,           # keep luminance
)
```

The hue range wraps around 360/0 — setting `hue_range=(350.0, 10.0)`
selects reds that straddle the boundary.

## Video scopes

Four scope clips visualize color data for quality control:

### Waveform monitor

```python
from pymotion import WaveformScopeClip

scope = WaveformScopeClip(source_frame=frame)
scope.set_duration(1)
```

### Vectorscope

```python
from pymotion import VectorscopeClip

scope = VectorscopeClip(source_frame=frame)
scope.set_duration(1)
```

### Histogram

```python
from pymotion import HistogramClip

scope = HistogramClip(source_frame=frame, channels="rgb")
scope.set_duration(1)
```

Set `channels="luma"` for a luminance-only histogram, or `"r"`, `"g"`,
`"b"` for individual channels.

### RGB parade

```python
from pymotion import ParadeScopeClip

scope = ParadeScopeClip(source_frame=frame)
scope.set_duration(1)
```

## EDL export

Export a composition as a CMX 3600 EDL file for interchange with NLE
software:

```python
from pymotion import Composition

comp = Composition(1920, 1080, fps=30, duration=300)
# ... add tracks and clips ...
comp.export_edl("project.edl")
```

Only `VideoClip` instances produce source entries; other clip types are
skipped.

## OTIO export

Export as OpenTimelineIO for richer interchange (requires the
`opentimelineio` package):

```python
comp.export_otio("project.otio")
```

Install: `pip install opentimelineio`
