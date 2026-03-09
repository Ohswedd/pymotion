"""Countdown Timer — animated countdown with gradient background and particles.

Demonstrates CountDown/CountUp animated text clips combined with a gradient
background and the sparkles() particle preset.
"""

from pymotion import (
    Composition,
    CountDown,
    CountUp,
    GradientClip,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    TextClip,
    Vec2,
)
from pymotion.particle.system import sparkles

# 10-second countdown at 30 fps
comp = Composition(width=1920, height=1080, fps=30, duration=300)

# Deep blue-to-purple gradient background
background = GradientClip(
    color_start="#0B0B3B",
    color_end="#3B0B5B",
    direction=45.0,
    gradient_type="linear",
)
background.set_duration(300)

# Main countdown number: 10 -> 0 over 300 frames
countdown = CountDown(
    start_value=10.0,
    end_value=0.0,
    font_size=200.0,
    color="#FFFFFF",
    decimals=0,
    position=Vec2(960.0, 480.0),
)
countdown.set_duration(300)

# Label above the number
label = TextClip(
    text="LAUNCHING IN",
    font="Arial",
    size=36.0,
    color="#AABBFF",
)
label.set_duration(300).set_position(960, 300).set_opacity(0.8)

# Progress bar background
bar_bg = ShapeClip.rect(x=460, y=650, w=1000, h=12, fill="#1A1A4E")
bar_bg.set_duration(300)

# Animated progress bar — in a real render loop you would update width per frame
bar_fill = ShapeClip.rect(x=460, y=650, w=1000, h=12, fill="#7B68EE")
bar_fill.set_duration(300)

# "GO!" text that fades in at the end
go_text = TextClip(
    text="GO!",
    font="Arial",
    size=120.0,
    color="#00FF88",
)
go_text.set_duration(30).at(270).set_position(960, 480)

go_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=270, value=0.0, easing="ease_out"),
        Keyframe(frame=285, value=1.0, easing="ease_in_out"),
        Keyframe(frame=299, value=1.0),
    ]
)

# Sparkles particle system for celebratory finish
spark_system = sparkles(width=1920, height=1080)

# Secondary count-up for a "percentage complete" display
percent_counter = CountUp(
    start_value=0.0,
    end_value=100.0,
    font_size=28.0,
    color="#AABBFF",
    suffix="%",
    decimals=0,
    position=Vec2(960.0, 700.0),
)
percent_counter.set_duration(300)

comp.add(background)
comp.add(countdown)
comp.add(label)
comp.add(bar_bg)
comp.add(bar_fill)
comp.add(percent_counter)
comp.add(go_text)

# In a custom render loop, step and composite particles for the last second:
#
#   for i in range(300):
#       frame = comp._render_frame(i)
#       if i >= 270:
#           spark_system.step()
#           particle_frame = spark_system.render()
#           # composite particle_frame onto frame

comp.render("countdown_timer.mp4", preset="h264_1080p")
