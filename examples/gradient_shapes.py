"""Gradient & Shapes — GradientClip and ShapeClip usage.

Demonstrates gradient backgrounds (linear, radial) and geometric
shapes created with ShapeClip factory methods.
"""

from pymotion import Composition, GradientClip, ShapeClip

comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Linear gradient background (top to bottom, purple to dark blue)
gradient_bg = GradientClip(
    color_start="#6c5ce7",
    color_end="#0c0032",
    gradient_type="linear",
    direction=0.0,  # top to bottom
)
gradient_bg.set_duration(150)

# Radial gradient overlay for a spotlight effect
radial = GradientClip(
    color_start="#ffffff",
    color_end="#00000000",
    gradient_type="radial",
    center_x=0.5,
    center_y=0.5,
    radius=0.6,
)
radial.set_duration(150).set_opacity(0.3)

# Shapes using factory methods
rect = ShapeClip.rect(x=100, y=200, w=300, h=200, fill="#ff6348")
rect.set_duration(150)

circle = ShapeClip.circle(cx=960, cy=540, r=80, fill="#2ed573")
circle.set_duration(150)

ellipse = ShapeClip.ellipse(cx=1500, cy=400, rx=120, ry=60, fill="#ffa502")
ellipse.set_duration(150)

triangle = ShapeClip.polygon(
    points=[(960, 800), (860, 950), (1060, 950)],
    fill="#1e90ff",
)
triangle.set_duration(150)

line = ShapeClip.line(x1=200, y1=100, x2=1720, y2=100, color="#ffffff", width=2.0)
line.set_duration(150)

comp.add(gradient_bg)
comp.add(radial)
comp.add(rect)
comp.add(circle)
comp.add(ellipse)
comp.add(triangle)
comp.add(line)

comp.render("gradient_shapes.mp4", preset="h264_1080p")
