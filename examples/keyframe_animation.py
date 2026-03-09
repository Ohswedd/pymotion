"""Keyframe Animation — animate position using KeyframeTrack.

Demonstrates creating keyframe tracks with easing functions to
animate a shape's position across the screen.
"""

from pymotion import (
    ColorClip,
    Composition,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    Vec2,
)

comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Background
background = ColorClip(color="#1a1a2e")
background.set_duration(150)

# Animated circle
circle = ShapeClip.circle(cx=0, cy=0, r=40, fill="#FF6B6B")
circle.set_duration(150)

# Build a position keyframe track: move across the screen with easing
position_track = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=Vec2(200.0, 540.0), easing="ease_in_out"),
        Keyframe(frame=45, value=Vec2(960.0, 300.0), easing="ease_out"),
        Keyframe(frame=90, value=Vec2(1720.0, 540.0), easing="ease_in"),
        Keyframe(frame=135, value=Vec2(960.0, 780.0), easing="ease_in_out"),
        Keyframe(frame=149, value=Vec2(200.0, 540.0)),
    ]
)

# Opacity track: fade in and out
opacity_track = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=0.0, easing="linear"),
        Keyframe(frame=15, value=1.0, easing="linear"),
        Keyframe(frame=130, value=1.0, easing="linear"),
        Keyframe(frame=149, value=0.0),
    ]
)

# Evaluate position at each frame and apply
# (In a real pipeline, you would use the track in a custom render loop
# or attach it to a clip via the animation system.)
for frame in range(150):
    pos = position_track.value_at(frame)
    if isinstance(pos, Vec2):
        circle.set_position(pos.x, pos.y)

comp.add(background)
comp.add(circle)

comp.render("keyframe_animation.mp4", preset="h264_1080p")
