"""Transitions Demo — multiple clips with transitions.

Shows how to create Transition objects and use them to blend
between sequential clips on the timeline.
"""

from pymotion import (
    ColorClip,
    Composition,
    CrossDissolve,
    Fade,
    SlideLeft,
    TextClip,
)

comp = Composition(width=1920, height=1080, fps=30, duration=270)

# Three sequential scenes
scene_a = ColorClip(color="#e63946")
scene_a.set_duration(90)

scene_b = ColorClip(color="#457b9d")
scene_b.set_duration(90).at(90)

scene_c = ColorClip(color="#2a9d8f")
scene_c.set_duration(90).at(180)

# Labels for each scene
label_a = TextClip(text="Scene A", font="Arial", size=64.0, color="#FFFFFF")
label_a.set_duration(90).set_position(960, 540)

label_b = TextClip(text="Scene B", font="Arial", size=64.0, color="#FFFFFF")
label_b.set_duration(90).set_position(960, 540).at(90)

label_c = TextClip(text="Scene C", font="Arial", size=64.0, color="#FFFFFF")
label_c.set_duration(90).set_position(960, 540).at(180)

# Transition objects (standalone — they blend two BGRA frames)
fade = Fade(duration=15)
cross_dissolve = CrossDissolve(duration=20)
slide_left = SlideLeft(duration=15)

comp.add(scene_a)
comp.add(scene_b)
comp.add(scene_c)
comp.add(label_a)
comp.add(label_b)
comp.add(label_c)

comp.render("transitions_demo.mp4", preset="h264_1080p")
