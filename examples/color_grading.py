"""Color Grading -- custom render loop with Brightness, Contrast, Saturation.

Demonstrates applying color effects frame-by-frame using a custom render
loop. Renders a gradient scene with warm color grading applied to every frame.
"""

from pathlib import Path

from pymotion import Composition, GradientClip, TextClip
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.effects.color import Brightness, Contrast, Saturation
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

comp = Composition(width=1920, height=1080, fps=30, duration=150)

background = GradientClip(
    color_start="#4a6741",
    color_end="#2c3e50",
    direction=135.0,
)
background.set_duration(150)

title = TextClip(text="Color Graded", font="Arial", size=64.0, color="#F0E6D3")
title.set_duration(150).set_position(960, 480)

subtitle = TextClip(
    text="Brightness + Contrast + Saturation", font="Arial", size=32.0, color="#CCBBAA"
)
subtitle.set_duration(150).set_position(960, 580)

comp.add(background, title, subtitle)

brightness = Brightness(value=1.15)
contrast = Contrast(value=1.2)
saturation = Saturation(value=1.3)

output_path = output_dir / "color_grading.mp4"
preset_config = get_preset("h264_1080p")


def graded_frames():
    """Yield color-graded frames from the composition."""
    dummy_ctx = RenderContext(
        frame=0,
        fps=30,
        resolution=Resolution(width=1920, height=1080),
        time_range=TimeRange(start=0, end=150),
        local_frame=0,
        progress=0.0,
    )
    for i in range(150):
        frame = comp._render_frame(i)
        dummy_ctx = RenderContext(
            frame=i,
            fps=30,
            resolution=Resolution(width=1920, height=1080),
            time_range=TimeRange(start=0, end=150),
            local_frame=i,
            progress=i / 149.0,
        )
        frame = brightness.apply(frame, dummy_ctx)
        frame = contrast.apply(frame, dummy_ctx)
        frame = saturation.apply(frame, dummy_ctx)
        yield frame


encoder = FFmpegEncoder()
encoder.encode(
    frame_iter=graded_frames(),
    audio=None,
    output=output_path,
    preset=preset_config,
    width=1920,
    height=1080,
    fps=30,
)
