"""Effects Showcase — apply visual effects to clips.

Demonstrates creating effect instances and applying them to BGRA frames.
Effects are stateless transform functions: effect.apply(frame, ctx).
"""

from pymotion import (
    Brightness,
    ChromaticAberration,
    ColorClip,
    Composition,
    Contrast,
    FilmGrain,
    GaussianBlur,
    TextClip,
    Vignette,
)

comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Base background
background = ColorClip(color="#264653")
background.set_duration(150)

# Title
title = TextClip(
    text="Effects Showcase",
    font="Arial",
    size=56.0,
    color="#E9C46A",
)
title.set_duration(150).set_position(960, 200)

# Create various effect instances
vignette = Vignette(strength=0.6, radius=0.75, feather=0.4)
film_grain = FilmGrain(strength=0.25, size=1.0, monochrome=True)
blur = GaussianBlur(radius=3.0)
brightness = Brightness(value=1.2)
contrast = Contrast(value=1.3)
chromatic = ChromaticAberration(offset=2.5, angle=45.0)

# Effects are applied per-frame in a render loop:
#   frame = vignette.apply(frame, ctx)
#   frame = film_grain.apply(frame, ctx)
#
# Each effect takes a BGRA uint8 array and returns a new one.

comp.add(background)
comp.add(title)

comp.render("effects_showcase.mp4", preset="h264_1080p")
