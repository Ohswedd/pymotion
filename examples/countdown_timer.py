"""Countdown Timer — animated countdown from 10 to 0 with gradient background.

Demonstrates CountDown animated text with Color objects and Vec2 positioning,
a progress bar, percentage counter, and a 'GO!' text reveal at the end.
"""

from pathlib import Path

from pymotion import (
    Composition,
    CountDown,
    CountUp,
    GradientClip,
    ShapeClip,
    TextClip,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "countdown_timer.mp4"

comp = Composition(width=1920, height=1080, fps=30, duration=330, background="#000000")

background = GradientClip(
    color_start="#0B0B3B",
    color_end="#3B0B5B",
    direction=45.0,
    gradient_type="linear",
)
background.set_duration(330)

countdown = CountDown(
    start_value=10.0,
    end_value=0.0,
    font_size=200.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    decimals=0,
    position=Vec2(860.0, 400.0),
)
countdown.set_duration(300)

label = TextClip(
    text="LAUNCHING IN",
    font="Arial",
    size=36.0,
    color="#AABBFF",
)
label.set_duration(300).set_position(860, 300).set_opacity(0.8)

bar_bg = ShapeClip.rect(x=460, y=700, w=1000, h=12, fill="#1A1A4E")
bar_bg.set_duration(300)

bar_fill = ShapeClip.rect(x=460, y=700, w=1000, h=12, fill="#7B68EE")
bar_fill.set_duration(300)

percent_counter = CountUp(
    start_value=0.0,
    end_value=100.0,
    font_size=28.0,
    color=Color(0.67, 0.73, 1.0, 1.0),
    suffix="%",
    decimals=0,
    position=Vec2(930.0, 740.0),
)
percent_counter.set_duration(300)

go_text = TextClip(
    text="GO!",
    font="Arial",
    size=140.0,
    color="#00FF88",
)
go_text.set_duration(30).at(300).set_position(860, 440)

go_bg = GradientClip(
    color_start="#0B0B3B",
    color_end="#3B0B5B",
    direction=45.0,
    gradient_type="linear",
)
go_bg.set_duration(30).at(300)

comp.add(background)
comp.add(countdown)
comp.add(label)
comp.add(bar_bg)
comp.add(bar_fill)
comp.add(percent_counter)
comp.add(go_bg)
comp.add(go_text)

comp.render(str(output_path), preset="h264_1080p")
