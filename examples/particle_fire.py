"""Particle Fire — fire particle system over a dark background.

Uses the built-in fire() preset with ParticleSystem to render a fire
effect composited over a dark gradient via a custom render loop.
"""

from pathlib import Path

import numpy as np

from pymotion import Composition, GradientClip
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import get_preset
from pymotion.particle.system import fire

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 5  # 150 frames
WIDTH, HEIGHT = 1920, 1080

comp = Composition(width=WIDTH, height=HEIGHT, fps=FPS, duration=DURATION, background="#000000")

bg = GradientClip("#0a0505", "#1a0a0a", direction=0.0)
bg.set_duration(DURATION)
comp.add(bg)

fire_system = fire(WIDTH, HEIGHT)

preset = get_preset("h264_1080p")
encoder = FFmpegEncoder()


def frame_iter():
    fire_system.reset()
    for i in range(DURATION):
        base = comp._render_frame(i)
        particle_frame = fire_system.simulate_frame()

        base_f = base.astype(np.float32)
        part_f = particle_frame.astype(np.float32)

        base_f[:, :, :3] = np.clip(base_f[:, :, :3] + part_f[:, :, :3], 0, 255)
        base_f[:, :, 3] = np.maximum(base_f[:, :, 3], part_f[:, :, 3])

        yield base_f.astype(np.uint8)


output_path = output_dir / "particle_fire.mp4"
encoder.encode(
    frame_iter=frame_iter(),
    audio=None,
    output=output_path,
    preset=preset,
    width=WIDTH,
    height=HEIGHT,
    fps=FPS,
)
print("Rendered: output/particle_fire.mp4")
