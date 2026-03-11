# AI Voice & Audio

PyMotion v2.0 provides AI-powered audio generation: voice conversion,
background music generation, and sound effect synthesis. All require
optional dependencies — install with `pip install "pymotion-studio[ai]"`.

## Voice conversion

`VoiceConversion` transforms the voice style of a clip to match a
target voice sample:

```python
from pymotion import VoiceConversion

converter = VoiceConversion(
    clip=my_clip,
    target_voice_sample="reference_voice.wav",
    strength=0.8,  # 0.0–1.0
)
converted_audio = converter.convert()
# Returns: numpy array of converted audio samples (float64)
```

The `strength` parameter controls how much of the target voice
characteristics are applied. A value of `1.0` fully transforms the
voice; lower values blend between original and target.

Requires a voice conversion backend (e.g., `so-vits-svc` or similar).

## Music generation

`MusicGeneration` creates AI background music from a text prompt
using Meta's MusicGen model:

```python
from pymotion import MusicGeneration

generator = MusicGeneration(
    prompt="upbeat corporate background music, acoustic guitar",
    duration=10.0,
    tempo=120,
    sample_rate=48000,
)
audio = generator.generate()
# Returns: numpy array of audio samples (float64, stereo)
```

The generated audio is a standard numpy array that can be used
directly with `AudioMixer`:

```python
from pymotion import AudioClipData, AudioMixer

mixer = AudioMixer(sample_rate=48000, channels=2)
mixer.add(AudioClipData(samples=audio, start_sample=0), track="music")
```

The model used internally is `"facebook/musicgen-small"`. The `tempo`
parameter provides an approximate BPM hint (20–300).

## Sound effect generation

`SoundFXGeneration` synthesizes sound effects from text descriptions:

```python
from pymotion import SoundFXGeneration

sfx = SoundFXGeneration(
    description="thunder rumbling in the distance",
    duration=3.0,
    sample_rate=48000,
)
audio = sfx.generate()
# Returns: numpy array of audio samples (float64, stereo)
```

The same MusicGen model handles both music and sound effects — the
`description` parameter guides the model toward effects rather than
musical content. The `sample_rate` defaults to 48000 Hz.

### Combining with compositions

Generated audio integrates seamlessly with the audio pipeline:

```python
from pymotion import Composition, AudioMixer, AudioClipData

comp = Composition(1920, 1080, fps=30, duration=300)
# ... add video tracks ...

mixer = AudioMixer(sample_rate=48000, channels=2)

# AI-generated background music
music = MusicGeneration(prompt="ambient electronic", duration=10.0).generate()
mixer.add(AudioClipData(samples=music, start_sample=0), track="bg_music")

# AI-generated sound effect at 3 seconds
sfx = SoundFXGeneration(description="whoosh transition", duration=1.0).generate()
mixer.add(AudioClipData(samples=sfx, start_sample=48000 * 3), track="sfx")

mixer.set_bus_volume("bg_music", 0.4)
```
