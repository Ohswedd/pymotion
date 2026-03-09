"""Audio + Video -- composition with background music and sound effects.

Demonstrates loading audio files with AudioClip, mixing them via AudioMixer,
and rendering a video with visual layers and mixed audio output.
"""

from pathlib import Path

from pymotion import AudioClip, AudioClipData, AudioMixer, ColorClip, Composition, TextClip

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = 300
SAMPLE_RATE = 48000

comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION)

background = ColorClip(color="#16213e")
background.set_duration(DURATION)

title = TextClip(text="Audio Demo", font="Arial", size=64.0, color="#E2E2E2")
title.set_duration(DURATION).set_position(960, 480)

subtitle = TextClip(
    text="Background music + sound effects", font="Arial", size=32.0, color="#8899AA"
)
subtitle.set_duration(DURATION).set_position(960, 580)

comp.add(background, title, subtitle)

music = AudioClip(source=assets / "background_music.wav", volume=0.6)
music.fade_in(0.5).fade_out(1.0)

sfx_whoosh = AudioClip(source=assets / "whoosh.wav", volume=0.9)
sfx_whoosh.at(60)

sfx_ding = AudioClip(source=assets / "ding.wav", volume=0.8)
sfx_ding.at(120)

mixer = AudioMixer(sample_rate=SAMPLE_RATE, channels=2)

music_samples = music.get_samples()
music_start = int(music.start_frame / FPS * SAMPLE_RATE)
mixer.add(
    AudioClipData(samples=music_samples, start_sample=music_start, sample_rate=SAMPLE_RATE),
    track="music",
)
mixer.set_volume("music", 0.6)

whoosh_samples = sfx_whoosh.get_samples()
whoosh_start = int(sfx_whoosh.start_frame / FPS * SAMPLE_RATE)
mixer.add(
    AudioClipData(samples=whoosh_samples, start_sample=whoosh_start, sample_rate=SAMPLE_RATE),
    track="sfx",
)

ding_samples = sfx_ding.get_samples()
ding_start = int(sfx_ding.start_frame / FPS * SAMPLE_RATE)
mixer.add(
    AudioClipData(samples=ding_samples, start_sample=ding_start, sample_rate=SAMPLE_RATE),
    track="sfx",
)
mixer.set_volume("sfx", 0.9)

mixed_audio = mixer.render()

comp.render(str(output_dir / "audio_video.mp4"), preset="h264_1080p")
