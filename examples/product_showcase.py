"""Product Showcase -- product image with title, price, features, and CTA.

Displays a product image from assets alongside marketing text: product title,
price, a features list, and a call-to-action button bar.
"""

from pathlib import Path

from pymotion import Composition, GradientClip, ShapeClip, TextClip
from pymotion.clip.image import ImageClip

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

DURATION = 180
comp = Composition(width=1920, height=1080, fps=30, duration=DURATION)

bg = GradientClip(color_start="#1a1a2e", color_end="#16213e", direction=180.0)
bg.set_duration(DURATION)

product_img = ImageClip(source=assets / "product.png")
product_img.set_duration(DURATION).set_position(300, 200)

title = TextClip(text="Premium Wireless Pro", font="Arial", size=64.0, color="#FFFFFF")
title.set_duration(DURATION).set_position(1100, 250)

price = TextClip(text="$149.99", font="Arial", size=56.0, color="#F7C948")
price.set_duration(DURATION).set_position(1100, 350)

divider = ShapeClip.rect(x=1000, y=420, w=300, h=2, fill="#3498DB")
divider.set_duration(DURATION).set_opacity(0.6)

features = [
    "40-hour battery life",
    "Active noise cancellation",
    "Hi-Res Audio certified",
    "Lightweight comfort fit",
]
feature_clips = []
for idx, feat in enumerate(features):
    ft = TextClip(text=feat, font="Arial", size=28.0, color="#CCDDEE")
    ft.set_duration(DURATION).set_position(1020, 460 + idx * 50)
    feature_clips.append(ft)

cta_bar = ShapeClip.rect(x=980, y=700, w=350, h=60, fill="#FF6B35")
cta_bar.set_duration(DURATION)

cta_text = TextClip(text="ORDER NOW", font="Arial", size=36.0, color="#FFFFFF")
cta_text.set_duration(DURATION).set_position(1155, 712)

logo = ImageClip(source=assets / "logo.png")
logo.set_duration(DURATION).set_position(1700, 20).set_opacity(0.7)

comp.add(bg, product_img, title, price, divider)
for fc in feature_clips:
    comp.add(fc)
comp.add(cta_bar, cta_text, logo)

comp.render(str(output_dir / "product_showcase.mp4"), preset="h264_1080p")
