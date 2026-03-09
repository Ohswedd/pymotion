"""Patch Notes — software update video with animated bullet points.

Demonstrates WordByWord for revealing patch notes one word at a time,
version badge shape, and a dark tech-themed gradient background.
"""

from pathlib import Path

from pymotion import (
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
)
from pymotion.text.animated import WordByWord
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "patch_notes.mp4"

FPS = 30
DURATION = 390
comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#0A0A14")

bg = GradientClip(
    color_start="#0A0A14",
    color_end="#141428",
    direction=0.0,
    gradient_type="linear",
)
bg.set_duration(DURATION)

badge_bg = ShapeClip.rect(x=760, y=60, w=400, h=60, fill="#1E90FF")
badge_bg.set_duration(DURATION)

version_text = TextClip(text="v2.4.0", font="Arial", size=36.0, color="#FFFFFF")
version_text.set_duration(DURATION).set_position(900, 68)

title = TextClip(text="PATCH NOTES", font="Arial", size=56.0, color="#E0E0FF")
title.set_duration(DURATION).set_position(780, 160)

divider = ShapeClip.line(x1=400, y1=240, x2=1520, y2=240, color="#1E90FF", width=2.0)
divider.set_duration(DURATION)

notes = [
    "New rendering engine with 3x performance boost",
    "Added dark mode support for all panels",
    "Fixed memory leak in asset pipeline",
    "Improved export quality for 4K output",
    "Bug fix: timeline scrubbing lag resolved",
]
y_positions = [300, 400, 500, 600, 700]
start_frames = [30, 90, 150, 210, 270]

note_clips = []
for _i, (note, y_pos, start) in enumerate(zip(notes, y_positions, start_frames, strict=True)):
    bullet = TextClip(text=">", font="Arial", size=28.0, color="#1E90FF")
    bullet.set_duration(DURATION - start).at(start).set_position(420, y_pos)
    note_clips.append(bullet)

    words = WordByWord(
        text=note,
        font_size=26.0,
        color=Color(0.85, 0.85, 0.95, 1.0),
        frames_per_word=8,
        position=Vec2(460.0, float(y_pos)),
    )
    words.set_duration(DURATION - start).at(start)
    note_clips.append(words)

comp.add(bg)
comp.add(badge_bg)
comp.add(version_text)
comp.add(title)
comp.add(divider)
for clip in note_clips:
    comp.add(clip)

comp.render(str(output_path), preset="h264_1080p")
