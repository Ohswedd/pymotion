# Text-to-Speech

`TTSClip` generates audio clips from text using one of three TTS
engine backends.

## System TTS (pyttsx3)

The default engine uses `pyttsx3` — zero network dependencies, works
offline:

```python
from pymotion import TTSClip

tts = TTSClip(
    text="Welcome to PyMotion.",
    engine="system",
    speed=1.0,
    voice="default",
)
samples = tts.generate()  # float64 stereo array (n_samples, 2)
```

Install the optional dependency: `pip install pyttsx3`

## OpenAI TTS

Use the OpenAI TTS API for high-quality voices. Requires an
`OPENAI_API_KEY` environment variable:

```python
tts = TTSClip(
    text="Welcome to PyMotion.",
    engine="openai",
    voice="alloy",   # alloy, echo, fable, onyx, nova, shimmer
    speed=1.0,
)
samples = tts.generate()
```

Install: `pip install openai`

## ElevenLabs TTS

Use ElevenLabs for premium voice synthesis. Requires an
`ELEVEN_API_KEY` environment variable:

```python
tts = TTSClip(
    text="Welcome to PyMotion.",
    engine="elevenlabs",
    voice="Rachel",
    speed=1.0,
)
samples = tts.generate()
```

Install: `pip install elevenlabs`

## Using with AudioMixer

The generated samples work directly with `AudioMixer`:

```python
from pymotion import TTSClip, AudioMixer, AudioClipData

tts = TTSClip(text="Quarterly revenue grew by 25%.", engine="system")
samples = tts.generate()

mixer = AudioMixer(sample_rate=48000, channels=2)
mixer.add(AudioClipData(samples=samples, start_sample=0), track="narration")
output = mixer.render()
```

## Caching

`TTSClip` caches the generated samples internally. Calling
`get_samples()` multiple times returns the same array without
re-synthesizing:

```python
tts = TTSClip(text="Hello", engine="system")
s1 = tts.get_samples()
s2 = tts.get_samples()
assert s1 is s2  # same cached object
```
