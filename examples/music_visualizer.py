"""Music Visualizer — beat-synced visual effects driven by audio analysis.

Demonstrates BeatDetector and WaveformExtractor to synchronize visual
effects with audio. Bars react to the waveform amplitude, and color
pulses fire on detected beats.
"""

import numpy as np

from pymotion import (
    BeatDetector,
    ColorClip,
    Composition,
    GradientClip,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    TextClip,
    WaveformExtractor,
    waveform_to_keyframes,
)
from pymotion.audio.mixer import AudioMixer

# --- Audio setup ---
# Load your audio file (placeholder path)
AUDIO_PATH = "audio/track.wav"  # Replace with actual audio file
SAMPLE_RATE = 44100
FPS = 30
DURATION_SECONDS = 10
TOTAL_FRAMES = FPS * DURATION_SECONDS  # 300 frames

comp = Composition(width=1920, height=1080, fps=FPS, duration=TOTAL_FRAMES)

# In a real script, load audio with scipy or soundfile:
#   import soundfile as sf
#   audio, sr = sf.read(AUDIO_PATH)
#
# For this example, we create a synthetic audio signal
audio = np.sin(
    2.0 * np.pi * 120.0 * np.linspace(0, DURATION_SECONDS, SAMPLE_RATE * DURATION_SECONDS)
)

# --- Beat detection ---

beat_detector = BeatDetector()
beat_frames = beat_detector.detect(audio, sample_rate=SAMPLE_RATE, fps=FPS)

# --- Waveform extraction ---

waveform_extractor = WaveformExtractor()
amplitude_envelope = waveform_extractor.extract(audio, n_points=TOTAL_FRAMES)

# Convert waveform amplitude to keyframes for driving visual properties
amp_keyframes = waveform_to_keyframes(amplitude_envelope, fps=FPS)

# --- Background: gradient that shifts on beats ---

background = GradientClip(
    color_start="#0a0020",
    color_end="#1a0040",
    direction=90.0,
)
background.set_duration(TOTAL_FRAMES)

# --- Visualizer bars ---
# Create a row of bars whose height is driven by the amplitude envelope

NUM_BARS = 32
BAR_WIDTH = 40
BAR_GAP = 20
BAR_START_X = (1920 - NUM_BARS * (BAR_WIDTH + BAR_GAP)) // 2

bars = []
for b in range(NUM_BARS):
    x = BAR_START_X + b * (BAR_WIDTH + BAR_GAP)
    bar = ShapeClip.rect(x=x, y=800, w=BAR_WIDTH, h=10, fill="#7B68EE")
    bar.set_duration(TOTAL_FRAMES)
    bars.append(bar)

# --- Beat flash overlay ---

flash_overlay = ColorClip(color="#FFFFFF")
flash_overlay.set_duration(TOTAL_FRAMES).set_opacity(0.0)

# Build an opacity keyframe track that pulses on each detected beat
flash_keyframes = []
for beat_frame in beat_frames:
    if beat_frame < TOTAL_FRAMES - 5:
        flash_keyframes.append(Keyframe(frame=beat_frame, value=0.3, easing="linear"))
        flash_keyframes.append(Keyframe(frame=beat_frame + 4, value=0.0, easing="ease_out"))

if flash_keyframes:
    flash_track = KeyframeTrack(keyframes=flash_keyframes)

# --- Central circle that pulses with amplitude ---

pulse_circle = ShapeClip.circle(cx=960, cy=540, r=80, fill="#7B68EE")
pulse_circle.set_duration(TOTAL_FRAMES).set_opacity(0.6)

# --- Song title ---

song_title = TextClip(
    text="NOW PLAYING",
    font="Arial",
    size=28.0,
    color="#AABBEE",
)
song_title.set_duration(TOTAL_FRAMES).set_position(960, 180).set_opacity(0.7)

track_name = TextClip(
    text="Synthwave Dreams",
    font="Arial",
    size=48.0,
    color="#FFFFFF",
)
track_name.set_duration(TOTAL_FRAMES).set_position(960, 230)

# --- Assemble composition ---

comp.add(background)
for bar in bars:
    comp.add(bar)
comp.add(flash_overlay)
comp.add(pulse_circle)
comp.add(song_title)
comp.add(track_name)

# --- Audio mixer ---

mixer = AudioMixer(sample_rate=SAMPLE_RATE, channels=2)
# mixer.add(AudioClipData(samples=audio, sample_rate=SAMPLE_RATE, start_frame=0))

# --- Render loop with beat-reactive effects ---
#
# In a custom render loop, update visuals per frame:
#
#   neon = NeonGlow(strength=0.4)
#   vignette = Vignette(strength=0.5)
#   brightness = Brightness(value=1.0)
#
#   for i in range(TOTAL_FRAMES):
#       amp = float(amplitude_envelope[i])
#
#       # Scale bar heights based on amplitude (with per-bar frequency offset)
#       for b_idx, bar in enumerate(bars):
#           offset = abs(b_idx - NUM_BARS // 2) / NUM_BARS
#           bar_height = int(10 + amp * 300 * (1.0 - offset * 0.5))
#           bar.set_position(
#               BAR_START_X + b_idx * (BAR_WIDTH + BAR_GAP),
#               800 - bar_height,
#           )
#
#       # Pulse the center circle radius via opacity
#       pulse_circle.set_opacity(0.3 + amp * 0.7)
#
#       # Flash on beats
#       if flash_keyframes:
#           flash_overlay.set_opacity(flash_track.value_at(i))
#
#       # Boost brightness on beats
#       is_beat = i in beat_frames
#       brightness = Brightness(value=1.2 if is_beat else 1.0)
#
#       frame = comp._render_frame(i)
#       frame = neon.apply(frame, ctx)
#       frame = vignette.apply(frame, ctx)
#       frame = brightness.apply(frame, ctx)

comp.render("music_visualizer.mp4", preset="h264_1080p")
