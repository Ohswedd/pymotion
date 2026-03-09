# Audio Mixing

PyMotion provides a multi-track audio mixing system with per-track volume
and pan automation. This guide covers loading audio, mixing tracks,
applying effects, and syncing audio to video.

## Loading audio files

The `AudioClip` class loads audio from any format FFmpeg supports (WAV, MP3,
FLAC, AAC, OGG, etc.):

```python
from pymotion import AudioClip

# Load a music file
music = AudioClip("assets/background_music.mp3")

# Load with custom sample rate
sfx = AudioClip("assets/click.wav", sample_rate=44100)
```

Audio is decoded to float64 stereo samples via FFmpeg. The default sample
rate is 48000 Hz.

## Trimming and fading

AudioClip provides a fluent API for trim, fade, and loop operations:

```python
from pymotion import AudioClip

music = AudioClip("assets/song.mp3")

# Trim to a 10-second segment starting at 5 seconds
music.trim(start_sec=5.0, end_sec=15.0)

# Add a 2-second fade in and 3-second fade out
music.fade_in(duration_sec=2.0)
music.fade_out(duration_sec=3.0)
```

All methods return `self` for chaining:

```python
music = (
    AudioClip("assets/song.mp3")
    .trim(5.0, 15.0)
    .fade_in(2.0)
    .fade_out(3.0)
)
```

## Positioning audio in the timeline

Use `at()` to set the start frame, or `at_seconds()` for time-based
positioning:

```python
from pymotion import AudioClip

intro = AudioClip("assets/intro.wav").at(0)
narration = AudioClip("assets/voice.wav").at(90)       # starts at frame 90
outro = AudioClip("assets/outro.wav").at_seconds(10.0, fps=30)  # frame 300
```

## Volume and pan

Set volume and stereo pan on each clip:

```python
from pymotion import AudioClip

music = AudioClip("assets/bg.mp3", volume=0.6)
sfx = AudioClip("assets/explosion.wav", volume=1.0, pan=-0.5)  # panned left
```

Pan values range from -1.0 (full left) through 0.0 (center) to 1.0
(full right). PyMotion uses equal-power (constant-power) panning.

## Looping

Loop an audio clip a fixed number of times, or infinitely:

```python
from pymotion import AudioClip

# Loop 3 times
ambience = AudioClip("assets/rain.wav").loop(3)

# Loop to fill the composition duration
drone = AudioClip("assets/drone.wav").loop(-1)
```

## The AudioMixer

`AudioMixer` combines multiple audio clips across named tracks with
per-track volume control:

```python
from pymotion import AudioMixer, AudioClipData
import numpy as np

mixer = AudioMixer(sample_rate=48000, channels=2)

# Create audio data (normally from AudioClip.get_samples())
music_samples = np.random.randn(48000 * 10, 2).astype(np.float64) * 0.3
sfx_samples = np.random.randn(48000 * 2, 2).astype(np.float64) * 0.8

# Add to named tracks
mixer.add(
    AudioClipData(samples=music_samples, start_sample=0),
    track="music",
)
mixer.add(
    AudioClipData(samples=sfx_samples, start_sample=48000 * 3),
    track="sfx",
)

# Set track volumes
mixer.set_volume("music", 0.7)
mixer.set_volume("sfx", 1.0)

# Render the final mix
output = mixer.render()  # interleaved int32 array
```

## Volume automation

Automate volume over time with keyframes. Each keyframe is a
`(sample_index, volume)` tuple:

```python
from pymotion import AudioMixer, AudioClipData
import numpy as np

mixer = AudioMixer(sample_rate=48000, channels=2)

samples = np.random.randn(48000 * 10, 2).astype(np.float64) * 0.5
mixer.add(AudioClipData(samples=samples, start_sample=0), track="music")

# Duck the music at sample 144000 (3 seconds in)
mixer.set_volume_keyframes("music", [
    (0, 1.0),           # full volume at start
    (144000, 1.0),       # still full at 3 seconds
    (148800, 0.3),       # duck to 30% over 0.1 seconds
    (336000, 0.3),       # hold ducked
    (340800, 1.0),       # bring back up
])

output = mixer.render()
```

Volume values are linearly interpolated between keyframes.

## Pan automation

Automate stereo pan position over time:

```python
mixer.set_pan("sfx", -0.5)  # static pan: slightly left

# Or automate it
mixer.set_pan_keyframes("sfx", [
    (0, -1.0),        # starts fully left
    (240000, 1.0),     # pans to fully right over 5 seconds
])
```

## Audio effects

PyMotion includes audio processing effects for mastering:

```python
from pymotion import Compressor, Limiter, EQ, EQBand

# Compressor -- reduces dynamic range
comp = Compressor(threshold=-20.0, ratio=4.0, attack_ms=5.0, release_ms=50.0)

# Limiter -- hard ceiling to prevent clipping
limiter = Limiter(ceiling=-1.0)

# EQ -- parametric equalizer
eq = EQ(bands=[
    EQBand(frequency=100.0, gain_db=-3.0, q=1.0),
    EQBand(frequency=3000.0, gain_db=2.0, q=0.7),
    EQBand(frequency=10000.0, gain_db=-6.0, q=1.5),
])
```

## Audio analysis

PyMotion provides tools for analyzing audio and syncing animation to music:

```python
from pymotion import BeatDetector, OnsetDetector, WaveformExtractor

# Detect beats in an audio file
detector = BeatDetector()
# beats = detector.detect("assets/song.mp3")

# Detect onsets (transients)
onset = OnsetDetector()
# onsets = onset.detect("assets/drums.wav")

# Extract waveform data for visualization
extractor = WaveformExtractor()
# waveform = extractor.extract("assets/song.mp3")
```

### Waveform to keyframes

Convert waveform amplitude data directly into animation keyframes:

```python
from pymotion import waveform_to_keyframes

# Convert waveform data to keyframes for driving animation
# keyframes = waveform_to_keyframes(waveform_data, fps=30)
```

## Putting it all together

A complete example mixing background music with sound effects:

```python
from pymotion import Composition, ColorClip, TextClip, AudioClip, AudioMixer, AudioClipData

# Build the visual composition
comp = Composition(1920, 1080, fps=30, duration=300)
bg = ColorClip("#0a0a23")
bg.set_duration(300)
title = TextClip("Audio Demo", font_size=72, color="#ffffff")
title.set_position(960, 540)
title.set_duration(300)
comp.add(bg, title)

# Set up audio
music = AudioClip("assets/bg_music.mp3").trim(0.0, 10.0).fade_in(1.0).fade_out(2.0)
click = AudioClip("assets/click.wav").at(30)

# The composition render() handles video encoding.
# Audio mixing is done separately via AudioMixer.
comp.render("audio_demo.mp4")
```
