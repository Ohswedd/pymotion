"""Hello World — minimal PyMotion composition.

Creates a 5-second video with a solid dark-blue background at 1080p/30fps.
"""

from pymotion import ColorClip, Composition

# Create a 1080p composition at 30 fps, lasting 150 frames (5 seconds)
comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Add a solid color background
background = ColorClip(color="#1a1a2e")
background.set_duration(150)

comp.add(background)

# Render to file (requires FFmpeg)
comp.render("hello_world.mp4", preset="h264_1080p")
