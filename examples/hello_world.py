"""Hello World — simplest PyMotion example.

Creates a 5-second intro video with a gradient background,
centered title text, and a subtitle below it.
"""

from pathlib import Path

from pymotion import Composition, GradientClip, TextClip

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 5  # 150 frames = 5 seconds

comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#000000")

bg = GradientClip("#1a1a2e", "#16213e", direction=90.0)
bg.set_duration(DURATION)

title = TextClip("Hello, PyMotion!", color="#FFFFFF", size=72.0, font="Arial")
title.set_duration(DURATION).set_position(960.0, 480.0)

subtitle = TextClip("Code-first video generation", color="#AABBCC", size=36.0, font="Arial")
subtitle.set_duration(DURATION).set_position(960.0, 580.0)

comp.add(bg, title, subtitle)
comp.render(str(output_dir / "hello_world.mp4"))
print("Rendered: output/hello_world.mp4")
