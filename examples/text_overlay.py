"""Text Overlay — multi-text demo with different sizes, colors, and positions.

Demonstrates TextClip with a title, subtitle, and paragraph text
layered over a solid color background.
"""

from pathlib import Path

from pymotion import ColorClip, Composition, TextClip

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 6  # 180 frames = 6 seconds

comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#0f0f23")

bg = ColorClip("#0f0f23")
bg.set_duration(DURATION)

title = TextClip("PyMotion Text Demo", color="#FF6B6B", size=64.0, font="Arial")
title.set_duration(DURATION).set_position(960.0, 200.0)

subtitle = TextClip(
    "Multiple text styles in one composition", color="#4ECDC4", size=36.0, font="Arial"
)
subtitle.set_duration(DURATION).set_position(960.0, 300.0)

line1 = TextClip("Large white heading", color="#FFFFFF", size=48.0, font="Arial")
line1.set_duration(DURATION).set_position(960.0, 460.0)

line2 = TextClip("Medium golden text", color="#FFD93D", size=32.0, font="Arial")
line2.set_duration(DURATION).set_position(960.0, 540.0)

line3 = TextClip("Small muted caption at the bottom", color="#888888", size=24.0, font="Arial")
line3.set_duration(DURATION).set_position(960.0, 620.0)

accent = TextClip("ACCENT", color="#FF4444", size=80.0, font="Arial")
accent.set_duration(DURATION).set_position(960.0, 800.0).set_opacity(0.6)

comp.add(bg, title, subtitle, line1, line2, line3, accent)
comp.render(str(output_dir / "text_overlay.mp4"))
print("Rendered: output/text_overlay.mp4")
