"""Particle Fire — fire particle effect.

Uses the built-in fire() preset from the particle system, which
configures emitters with warm colors, upward velocity, and drag.
"""

from pymotion import ColorClip, Composition, Vec2
from pymotion.particle.system import Emitter, ParticleSystem, fire

comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Dark background
background = ColorClip(color="#0a0a0a")
background.set_duration(150)

# Use the fire preset — returns a fully configured ParticleSystem
fire_system = fire(width=1920, height=1080)

# You can also build a custom particle system from scratch:
custom_system = ParticleSystem(width=1920, height=1080)
custom_system.add_emitter(
    Emitter(
        position=Vec2(960.0, 900.0),
        rate=30.0,
        lifetime=(20.0, 50.0),
        speed=(2.0, 6.0),
        angle=(250.0, 290.0),  # upward cone
        size=(3.0, 8.0),
        gravity=Vec2(0.0, -0.1),
        drag=0.02,
        turbulence=0.5,
    )
)

comp.add(background)

# In a real render loop, you would call:
#   fire_system.step()                     # advance simulation
#   particle_frame = fire_system.render()  # get BGRA array
# and composite it onto each frame.

comp.render("particle_fire.mp4", preset="h264_1080p")
