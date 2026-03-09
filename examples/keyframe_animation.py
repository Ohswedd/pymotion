"""Keyframe Animation — demonstrates KeyframeTrack and animate().

Shows a circle moving across the screen with easing, plus opacity
fading. Uses a custom render loop to evaluate keyframes each frame.
"""

from pathlib import Path

import numpy as np

from pymotion import (
    Composition,
    GradientClip,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    animate,
)
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 5  # 150 frames
WIDTH, HEIGHT = 1920, 1080

x_track = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=200.0, easing="ease_in_out_cubic"),
        Keyframe(frame=75, value=960.0, easing="ease_in_out_cubic"),
        Keyframe(frame=150, value=1700.0),
    ]
)

y_track = animate(start=300.0, end=780.0, duration=150, easing="ease_in_out_sine")

opacity_track = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=0.0, easing="ease_out_quad"),
        Keyframe(frame=30, value=1.0, easing="linear"),
        Keyframe(frame=120, value=1.0, easing="ease_in_quad"),
        Keyframe(frame=150, value=0.0),
    ]
)

comp = Composition(width=WIDTH, height=HEIGHT, fps=FPS, duration=DURATION, background="#0a0a2a")

bg = GradientClip("#0a0a2a", "#1a1a4a", direction=90.0)
bg.set_duration(DURATION)
comp.add(bg)

preset = get_preset("h264_1080p")
encoder = FFmpegEncoder()


def frame_iter():
    for i in range(DURATION):
        cx = float(x_track.value_at(i))
        cy = float(y_track.value_at(i))
        alpha = float(opacity_track.value_at(i))

        circle = ShapeClip.circle(cx=cx, cy=cy, r=60, fill="#FF6B6B")
        circle.set_duration(DURATION)

        shadow = ShapeClip.circle(cx=cx + 5, cy=cy + 5, r=60, fill="#000000")
        shadow.set_duration(DURATION)

        comp_frame = comp._render_frame(i)

        ctx = RenderContext(
            frame=i,
            fps=FPS,
            resolution=Resolution(WIDTH, HEIGHT),
            time_range=TimeRange(start=0, end=DURATION),
            local_frame=i,
            progress=i / max(DURATION - 1, 1),
        )
        shadow_frame = shadow.render_frame(ctx)
        circle_frame = circle.render_frame(ctx)

        mask_s = shadow_frame[:, :, 3:4].astype(np.float32) / 255.0 * 0.3
        result = comp_frame.astype(np.float32)
        sf = shadow_frame[:, :, :3].astype(np.float32)
        result[:, :, :3] = result[:, :, :3] * (1 - mask_s) + sf * mask_s

        mask_c = circle_frame[:, :, 3:4].astype(np.float32) / 255.0 * alpha
        cf = circle_frame[:, :, :3].astype(np.float32)
        result[:, :, :3] = result[:, :, :3] * (1 - mask_c) + cf * mask_c

        yield np.clip(result, 0, 255).astype(np.uint8)


output_path = output_dir / "keyframe_animation.mp4"
encoder.encode(
    frame_iter=frame_iter(),
    audio=None,
    output=output_path,
    preset=preset,
    width=WIDTH,
    height=HEIGHT,
    fps=FPS,
)
print("Rendered: output/keyframe_animation.mp4")
