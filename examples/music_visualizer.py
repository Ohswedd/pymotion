"""Music Visualizer — colorful gradient background with animated elements.

Demonstrates GradientClip, ShapeClip, and TextClip to create
a music visualizer look with ring shapes and track info.
"""

from pathlib import Path

from pymotion import (
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "music_visualizer.mp4"

FPS = 30
DURATION = 150
comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#000000")

bg = GradientClip(
    color_start="#0A0020",
    color_end="#200040",
    direction=90.0,
    gradient_type="linear",
)
bg.set_duration(DURATION)

center_glow = GradientClip(
    color_start="#2A1050",
    color_end="#0A0020",
    gradient_type="radial",
    radius=0.6,
)
center_glow.set_duration(DURATION).set_opacity(0.5)

pulse_circle = ShapeClip.circle(cx=960, cy=540, r=120, fill="#7B68EE")
pulse_circle.set_duration(DURATION).set_opacity(0.4)

ring = ShapeClip.circle(cx=960, cy=540, r=180, fill="#00000000", stroke="#9B88FF", stroke_width=3.0)
ring.set_duration(DURATION).set_opacity(0.3)

now_playing = TextClip(text="NOW PLAYING", font="Arial", size=22.0, color="#8888CC")
now_playing.set_duration(DURATION).set_position(860, 180).set_opacity(0.7)

track_title = TextClip(text="Synthwave Dreams", font="Arial", size=48.0, color="#FFFFFF")
track_title.set_duration(DURATION).set_position(780, 220)

artist = TextClip(text="Neon Pulse", font="Arial", size=28.0, color="#AA99DD")
artist.set_duration(DURATION).set_position(860, 280).set_opacity(0.8)

progress_bg = ShapeClip.rect(x=560, y=860, w=800, h=4, fill="#1A1A3E")
progress_bg.set_duration(DURATION)

progress_fill = ShapeClip.rect(x=560, y=860, w=400, h=4, fill="#7B68EE")
progress_fill.set_duration(DURATION)

comp.add(bg, center_glow, pulse_circle, ring)
comp.add(now_playing, track_title, artist)
comp.add(progress_bg, progress_fill)

comp.render(str(output_path), preset="h264_1080p")
print(f"Rendered: {output_path.relative_to(Path(__file__).parent)}")
