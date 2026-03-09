"""Audio + Video — composition with AudioClip and AudioMixer.

Shows how to load audio, set volume and pan, and configure
the AudioMixer for a composition with background music.
"""

from pathlib import Path

from pymotion import AudioClip, AudioMixer, ColorClip, Composition, TextClip

comp = Composition(width=1920, height=1080, fps=30, duration=300)

# Visual layers
background = ColorClip(color="#16213e")
background.set_duration(300)

title = TextClip(
    text="Audio Demo",
    font="Arial",
    size=64.0,
    color="#E2E2E2",
)
title.set_duration(300).set_position(960, 540)

comp.add(background)
comp.add(title)

# Audio setup — load a music track and a sound effect
music = AudioClip(
    source=Path("assets/background_music.wav"),
    volume=0.7,
    pan=0.0,
    start_frame=0,
)

sfx = AudioClip(
    source=Path("assets/whoosh.wav"),
    volume=1.0,
    pan=-0.3,
    start_frame=60,  # play at 2 seconds in
)

# Mix audio tracks together
mixer = AudioMixer()

comp.render("audio_video.mp4", preset="h264_1080p")
