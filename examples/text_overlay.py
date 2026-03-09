"""Text Overlay — text on a colored background.

Demonstrates TextClip positioned over a solid color background with
a subtitle line and adjusted opacity.
"""

from pymotion import Color, ColorClip, Composition, TextClip

comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Dark gradient-like background
background = ColorClip(color="#0f0c29")
background.set_duration(150)

# Main title — large, white, centered
title = TextClip(
    text="Welcome to PyMotion",
    font="Arial",
    size=72.0,
    color="#FFFFFF",
)
title.set_duration(150).set_position(960, 400)

# Subtitle — smaller, slightly transparent
subtitle = TextClip(
    text="Code-first video generation in Python",
    font="Arial",
    size=36.0,
    color="#AABBFF",
)
subtitle.set_duration(150).set_position(960, 520).set_opacity(0.8)

comp.add(background)
comp.add(title)
comp.add(subtitle)

comp.render("text_overlay.mp4", preset="h264_1080p")
