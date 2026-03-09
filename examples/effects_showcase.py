"""Effects Showcase — applies visual effects to a gradient scene.

Demonstrates Vignette, FilmGrain, GaussianBlur, and Brightness effects
applied through a custom render loop.
"""

from pathlib import Path

from pymotion import (
    Brightness,
    Composition,
    FilmGrain,
    GradientClip,
    ShapeClip,
    TextClip,
    Vignette,
)
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 6  # 180 frames
WIDTH, HEIGHT = 1920, 1080

comp = Composition(width=WIDTH, height=HEIGHT, fps=FPS, duration=DURATION, background="#000000")

bg = GradientClip("#1a0533", "#0a1628", direction=135.0)
bg.set_duration(DURATION)

circle = ShapeClip.circle(cx=960, cy=540, r=200, fill="#FF6B6B")
circle.set_duration(DURATION)

rect = ShapeClip.rect(x=300, y=400, w=250, h=250, fill="#4ECDC4")
rect.set_duration(DURATION)

label = TextClip("Effects Showcase", color="#FFFFFF", size=48.0, font="Arial")
label.set_duration(DURATION).set_position(960.0, 150.0)

comp.add(bg, rect, circle, label)

effects = [
    Vignette(strength=0.6),
    FilmGrain(strength=0.15),
    Brightness(value=0.05),
]

preset = get_preset("h264_1080p")
encoder = FFmpegEncoder()


def frame_iter():
    for i in range(DURATION):
        frame = comp._render_frame(i)
        ctx = RenderContext(
            frame=i,
            fps=FPS,
            resolution=Resolution(WIDTH, HEIGHT),
            time_range=TimeRange(start=0, end=DURATION),
            local_frame=i,
            progress=i / max(DURATION - 1, 1),
        )
        for effect in effects:
            frame = effect.apply(frame, ctx)
        yield frame


output_path = output_dir / "effects_showcase.mp4"
encoder.encode(
    frame_iter=frame_iter(),
    audio=None,
    output=output_path,
    preset=preset,
    width=WIDTH,
    height=HEIGHT,
    fps=FPS,
)
print("Rendered: output/effects_showcase.mp4")
