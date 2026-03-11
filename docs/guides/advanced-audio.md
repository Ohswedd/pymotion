# Advanced Audio

PyMotion v1.5 extends the audio pipeline with 5.1 surround mixing, bus
routing, audio crossfades, multiband compression, convolution reverb,
and LUFS normalization.

## 5.1 surround channel routing

Configure the mixer for 5.1 surround output with SMPTE/ITU channel
ordering (L, R, C, LFE, Ls, Rs):

```python
from pymotion import AudioMixer

mixer = AudioMixer(sample_rate=48000, channels=6)
```

Route individual tracks to specific channels using a channel weight map:

```python
from pymotion import SurroundChannel

mixer.set_routing("dialogue", {
    SurroundChannel.CENTER: 1.0,
})

mixer.set_routing("ambience", {
    SurroundChannel.LEFT_SURROUND: 0.7,
    SurroundChannel.RIGHT_SURROUND: 0.7,
})
```

## Audio bus routing

Group tracks into named buses for submix processing before the master:

```python
mixer.create_bus("dialogue")
mixer.create_bus("music")
mixer.create_bus("sfx")

mixer.assign_track_to_bus("narrator", "dialogue")
mixer.assign_track_to_bus("bg_music", "music")
mixer.assign_track_to_bus("explosion", "sfx")
```

Control bus volume and pan with static values or keyframes:

```python
mixer.set_bus_volume("music", 0.6)
mixer.set_bus_pan("sfx", -0.3)

# Automate bus volume over time
mixer.set_bus_volume_keyframes("music", [
    (0, 1.0),
    (144000, 0.3),   # duck at 3 seconds
    (240000, 1.0),   # restore at 5 seconds
])
```

## Audio crossfades

Apply crossfades between overlapping audio clips with three curve types:

```python
from pymotion import audio_crossfade
import numpy as np

clip_a = np.random.randn(48000 * 5, 2) * 0.5
clip_b = np.random.randn(48000 * 5, 2) * 0.5

# Equal-power crossfade (smoothest perceived transition)
result = audio_crossfade(clip_a, clip_b, crossfade_samples=24000, curve="equal_power")

# Other curves: "linear", "s_curve"
```

## Multiband compressor

Split audio into four frequency bands and compress each independently:

```python
from pymotion import MultibandCompressor

comp = MultibandCompressor(
    crossover_frequencies=[200.0, 2000.0, 8000.0],
    thresholds=[-20.0, -18.0, -15.0, -12.0],
    ratios=[3.0, 2.5, 2.0, 1.5],
    attack_ms=[5.0, 3.0, 2.0, 1.0],
    release_ms=[50.0, 40.0, 30.0, 20.0],
)

compressed = comp.process(samples, sample_rate=48000)
```

## Convolution reverb

Load an impulse response WAV and apply FFT-based convolution reverb:

```python
from pymotion import ConvolutionReverb

reverb = ConvolutionReverb(
    ir_path="assets/cathedral_ir.wav",
    wet=0.3,
    dry=0.7,
)

wet_audio = reverb.process(samples, sample_rate=48000)
```

## LUFS normalization

Normalize the final mix to a target loudness level using ITU-R BS.1770
K-weighted measurement:

```python
# Normalize for streaming platforms (-14 LUFS)
mixer.normalize(target_lufs=-14)

# Normalize for broadcast (-23 LUFS)
mixer.normalize(target_lufs=-23)

output = mixer.render()
```

## Silence generator

Generate precisely timed silence clips:

```python
from pymotion import Silence

# 2 seconds of silence at 48kHz
gap = Silence(duration_sec=2.0)
```
