"""Photo Slideshow -- four photos with captions and fade transitions.

Loads 4 photos from assets, displays each for 3 seconds with a text caption,
and applies crossfade transitions between slides using a custom render loop.
"""

from pathlib import Path

import numpy as np

from pymotion import ImageClip, TextClip
from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset
from pymotion.transition.library import Fade

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
SLIDE_FRAMES = 90
FADE_FRAMES = 15
TOTAL = 4 * SLIDE_FRAMES

W, H = 1920, 1080
res = Resolution(width=W, height=H)

photos = ["photo_beach.png", "photo_mountains.png", "photo_city.png", "photo_sunset.png"]
captions = ["Beach Paradise", "Mountain Trail", "City Lights", "Golden Sunset"]

slides = []
for path in photos:
    clip = ImageClip(source=assets / path)
    clip.set_duration(TOTAL)
    slides.append(clip)

caption_clips = []
for text in captions:
    clip = TextClip(text=text, font="Arial", size=48.0, color="#FFFFFF")
    clip.set_duration(TOTAL).set_position(960, 950)
    caption_clips.append(clip)

fade = Fade(duration=FADE_FRAMES)


def make_ctx(frame_idx):
    """Build a RenderContext for the given frame."""
    return RenderContext(
        frame=frame_idx,
        fps=FPS,
        resolution=res,
        time_range=TimeRange(start=0, end=TOTAL),
        local_frame=frame_idx,
        progress=frame_idx / max(TOTAL - 1, 1),
    )


def slideshow_frames():
    """Yield frames with crossfade transitions between slides."""
    for i in range(TOTAL):
        ctx = make_ctx(i)
        slide_idx = min(i // SLIDE_FRAMES, 3)
        local = i - slide_idx * SLIDE_FRAMES

        frame_a = slides[slide_idx].render_frame(ctx)
        caption_a = caption_clips[slide_idx].render_frame(ctx)

        if local >= (SLIDE_FRAMES - FADE_FRAMES) and slide_idx < 3:
            progress = (local - (SLIDE_FRAMES - FADE_FRAMES)) / FADE_FRAMES
            frame_b = slides[slide_idx + 1].render_frame(ctx)
            caption_b = caption_clips[slide_idx + 1].render_frame(ctx)
            frame_a = fade.render_frame(frame_a, frame_b, progress)
            caption_a = fade.render_frame(caption_a, caption_b, progress)

        combined = frame_a.copy().astype(np.float32)
        alpha = caption_a[:, :, 3:4].astype(np.float32) / 255.0
        combined[:, :, :3] = (
            combined[:, :, :3] * (1 - alpha) + caption_a[:, :, :3].astype(np.float32) * alpha
        )
        combined[:, :, 3] = np.maximum(frame_a[:, :, 3], caption_a[:, :, 3])
        yield np.clip(combined, 0, 255).astype(np.uint8)


encoder = FFmpegEncoder()
encoder.encode(
    frame_iter=slideshow_frames(),
    audio=None,
    output=output_dir / "photo_slideshow.mp4",
    preset=get_preset("h264_1080p"),
    width=W,
    height=H,
    fps=FPS,
)
