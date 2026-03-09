"""Gradient Shapes — gradient backgrounds with geometric shapes.

Demonstrates GradientClip (linear and radial) combined with ShapeClip
factory methods for rectangles, circles, and polygons.
"""

from pathlib import Path

from pymotion import Composition, GradientClip, ShapeClip

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 5  # 150 frames

comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#000000")

bg = GradientClip("#0a0a2a", "#1a0a3a", direction=45.0)
bg.set_duration(DURATION)

radial_bg = GradientClip(
    "#222255", "#000011", gradient_type="radial", center_x=0.5, center_y=0.5, radius=0.7
)
radial_bg.set_duration(DURATION).set_opacity(0.5)

rect1 = ShapeClip.rect(
    x=200, y=300, w=300, h=200, fill="#FF6B6B", stroke="#FFFFFF", stroke_width=3.0
)
rect1.set_duration(DURATION)

rect2 = ShapeClip.rect(x=250, y=350, w=200, h=120, fill="#4ECDC4")
rect2.set_duration(DURATION).set_opacity(0.7)

circle1 = ShapeClip.circle(
    cx=960, cy=540, r=120, fill="#FFD93D", stroke="#FFFFFF", stroke_width=2.0
)
circle1.set_duration(DURATION)

circle2 = ShapeClip.circle(cx=1050, cy=480, r=80, fill="#6BCB77")
circle2.set_duration(DURATION).set_opacity(0.8)

triangle = ShapeClip.polygon(
    points=[(1500.0, 300.0), (1700.0, 700.0), (1300.0, 700.0)],
    fill="#C084FC",
)
triangle.set_duration(DURATION)

diamond = ShapeClip.polygon(
    points=[(960.0, 850.0), (1060.0, 950.0), (960.0, 1050.0), (860.0, 950.0)],
    fill="#F472B6",
)
diamond.set_duration(DURATION).set_opacity(0.9)

comp.add(bg, radial_bg, rect1, rect2, circle1, circle2, triangle, diamond)
comp.render(str(output_dir / "gradient_shapes.mp4"))
print("Rendered: output/gradient_shapes.mp4")
