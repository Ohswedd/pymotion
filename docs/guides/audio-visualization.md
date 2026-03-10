# Audio Visualization

PyMotion provides four audio visualization clips that render audio data
as animated video frames using Cairo.

## Waveform clip

`WaveformClip` renders an animated audio waveform, supporting both bar
and line styles:

```python
from pymotion import WaveformClip, Composition, Track
import numpy as np

comp = Composition(1920, 1080, fps=30, duration=90)

samples = np.random.randn(48000 * 3, 2) * 0.5  # 3 seconds of audio
wave = WaveformClip(
    audio_samples=samples,
    style="bars",
    color="#00FF88",
    background="#111111",
    sample_rate=48000,
)
wave.set_duration(90)

track = Track(name="waveform")
track.add(wave)
comp.add_track(track)
comp.render("waveform.mp4", preset="h264_1080p")
```

Set `style="line"` for a continuous waveform trace instead of bars.

## Spectrum clip

`SpectrumClip` renders an animated FFT frequency spectrum with
logarithmic frequency binning:

```python
from pymotion import SpectrumClip

spectrum = SpectrumClip(
    audio_samples=samples,
    bands=64,
    style="bars",
    color_map=["#FF0000", "#FFFF00", "#00FF00"],
    sample_rate=48000,
)
spectrum.set_duration(90)
```

The `color_map` interpolates across bands from low to high frequency.

## Spectrogram clip

`SpectrogramClip` renders a scrolling time-frequency heatmap:

```python
from pymotion import SpectrogramClip

spectrogram = SpectrogramClip(
    audio_samples=samples,
    style="heatmap",
    sample_rate=48000,
)
spectrogram.set_duration(90)
```

## Audio-reactive effect

`AudioReactiveEffect` modulates any visual effect parameter from audio
amplitude in a configurable frequency band:

```python
from pymotion import AudioReactiveEffect
from pymotion.effects.visual import Glow

reactive = AudioReactiveEffect(
    effect=Glow(strength=0.0),
    audio_samples=samples,
    property_name="strength",
    band=(80.0, 500.0),      # react to bass frequencies
    sensitivity=2.0,
    sample_rate=48000,
)
```

The `band` tuple specifies the frequency range in Hz. The `sensitivity`
multiplier scales how strongly the audio amplitude drives the property.
