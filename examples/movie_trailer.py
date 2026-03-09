"""Movie Trailer — dramatic title sequence with animated text.

Demonstrates Typewriter for the main title, WordByWord for the tagline,
decorative shapes, and multiple scenes with dark cinematic styling.
"""

from pathlib import Path

from pymotion import (
    ColorClip,
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
)
from pymotion.text.animated import Typewriter, WordByWord
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "movie_trailer.mp4"

FPS = 30
DURATION = 360
comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#000000")

bg = GradientClip(
    color_start="#050510",
    color_end="#1A0A2E",
    direction=0.0,
    gradient_type="radial",
)
bg.set_duration(DURATION)

top_line = ShapeClip.line(x1=560, y1=380, x2=1360, y2=380, color="#C0A040", width=2.0)
top_line.set_duration(180).at(30)

bottom_line = ShapeClip.line(x1=560, y1=620, x2=1360, y2=620, color="#C0A040", width=2.0)
bottom_line.set_duration(180).at(30)

title = Typewriter(
    text="ECLIPSE OF SHADOWS",
    font_size=72.0,
    color=Color(1.0, 0.85, 0.4, 1.0),
    chars_per_frame=0.8,
    cursor=True,
    position=Vec2(540.0, 440.0),
)
title.set_duration(150).at(30)

tagline = WordByWord(
    text="The darkness returns. No one is safe.",
    font_size=32.0,
    color=Color(0.75, 0.75, 0.85, 1.0),
    frames_per_word=12,
    position=Vec2(600.0, 560.0),
)
tagline.set_duration(120).at(60)

scene2_bg = ColorClip(color="#080008")
scene2_bg.set_duration(120).at(210)

coming_soon = TextClip(
    text="COMING SOON",
    font="Arial",
    size=64.0,
    color="#FFFFFF",
)
coming_soon.set_duration(90).at(220).set_position(760, 460)

date_text = TextClip(
    text="SUMMER 2026",
    font="Arial",
    size=36.0,
    color="#C0A040",
)
date_text.set_duration(90).at(240).set_position(820, 560)

accent = ShapeClip.rect(x=860, y=640, w=200, h=4, fill="#C0A040")
accent.set_duration(80).at(250)

comp.add(bg)
comp.add(top_line)
comp.add(bottom_line)
comp.add(title)
comp.add(tagline)
comp.add(scene2_bg)
comp.add(coming_soon)
comp.add(date_text)
comp.add(accent)

comp.render(str(output_path), preset="h264_1080p")
