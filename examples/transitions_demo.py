"""Transitions Demo — shows transitions between colored scenes.

Creates 4 colored scenes and transitions between them using Fade,
CrossDissolve, SlideLeft, and ZoomIn. Uses a custom render loop.
"""

from pathlib import Path

from pymotion import (
    Composition,
    CrossDissolve,
    Fade,
    SlideLeft,
    TextClip,
)
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
SCENE_DUR = 60  # 2 seconds per scene
TRANS_DUR = 20  # transition overlap in frames
WIDTH, HEIGHT = 1920, 1080
NUM_SCENES = 4

colors = ["#E63946", "#457B9D", "#2A9D8F", "#E9C46A"]
labels = ["Scene A: Fade", "Scene B: CrossDissolve", "Scene C: SlideLeft", "Scene D: ZoomIn"]

scenes: list[Composition] = []
for idx in range(NUM_SCENES):
    sc = Composition(WIDTH, HEIGHT, FPS, SCENE_DUR, background=colors[idx])
    lbl = TextClip(labels[idx], color="#FFFFFF", size=56.0, font="Arial")
    lbl.set_duration(SCENE_DUR).set_position(960.0, 540.0)
    sc.add(lbl)
    scenes.append(sc)

transitions = [
    Fade(duration=TRANS_DUR),
    CrossDissolve(duration=TRANS_DUR),
    SlideLeft(duration=TRANS_DUR),
]

total_frames = SCENE_DUR * NUM_SCENES - TRANS_DUR * (NUM_SCENES - 1)

preset = get_preset("h264_1080p")
encoder = FFmpegEncoder()


def frame_iter():
    for i in range(total_frames):
        offset = 0
        for s in range(NUM_SCENES):
            scene_start = offset
            scene_end = scene_start + SCENE_DUR
            if i < scene_end:
                local = i - scene_start
                if s < NUM_SCENES - 1:
                    trans_begin = SCENE_DUR - TRANS_DUR
                    if local >= trans_begin:
                        t_local = local - trans_begin
                        progress = t_local / max(TRANS_DUR - 1, 1)
                        frame_a = scenes[s]._render_frame(local)
                        frame_b = scenes[s + 1]._render_frame(t_local)
                        yield transitions[s].render_frame(frame_a, frame_b, progress)
                        break
                yield scenes[s]._render_frame(local)
                break
            offset += SCENE_DUR - TRANS_DUR


output_path = output_dir / "transitions_demo.mp4"
encoder.encode(
    frame_iter=frame_iter(),
    audio=None,
    output=output_path,
    preset=preset,
    width=WIDTH,
    height=HEIGHT,
    fps=FPS,
)
print("Rendered: output/transitions_demo.mp4")
