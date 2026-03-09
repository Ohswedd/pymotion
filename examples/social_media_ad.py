"""Social Media Ad -- square 1080x1080 promo with 3 scenes.

Creates a 6-second social media advertisement at 1080x1080 (square format)
with three scenes: gradient intro, product feature, and call-to-action.
"""

from pathlib import Path

from pymotion import (
    ColorClip,
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
)
from pymotion.clip.image import ImageClip

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

DURATION = 180
comp = Composition(width=1080, height=1080, fps=30, duration=DURATION)

bg_intro = GradientClip(color_start="#FF6B35", color_end="#F7C948", direction=135.0)
bg_intro.set_duration(60)

headline = TextClip(text="SUMMER SALE", font="Arial", size=96.0, color="#FFFFFF")
headline.set_duration(60).set_position(540, 400)

tagline_intro = TextClip(text="Up to 70% off", font="Arial", size=48.0, color="#1A1A2E")
tagline_intro.set_duration(60).set_position(540, 530)

bg_product = GradientClip(color_start="#1A1A2E", color_end="#16213E", direction=90.0)
bg_product.set_duration(60).at(60)

accent_circle = ShapeClip.circle(cx=540, cy=440, r=200, fill="#FF6B35")
accent_circle.set_duration(60).at(60).set_opacity(0.3)

product_img = ImageClip(source=assets / "product.png")
product_img.set_duration(60).at(60).set_position(340, 240)

product_label = TextClip(text="Premium Collection", font="Arial", size=52.0, color="#F7C948")
product_label.set_duration(60).at(60).set_position(540, 750)

price_tag = TextClip(text="Starting at $29.99", font="Arial", size=36.0, color="#FFFFFF")
price_tag.set_duration(60).at(60).set_position(540, 830).set_opacity(0.8)

bg_cta = ColorClip(color="#FF6B35")
bg_cta.set_duration(60).at(120)

cta_text = TextClip(text="SHOP NOW", font="Arial", size=80.0, color="#FFFFFF")
cta_text.set_duration(60).at(120).set_position(540, 440)

cta_bar = ShapeClip.rect(x=340, y=520, w=400, h=6, fill="#1A1A2E")
cta_bar.set_duration(60).at(120)

website = TextClip(text="www.example.com", font="Arial", size=32.0, color="#FFFFFF")
website.set_duration(60).at(120).set_position(540, 600).set_opacity(0.8)

logo = ImageClip(source=assets / "logo.png")
logo.set_duration(60).at(120).set_position(440, 750)

comp.add(
    bg_intro,
    headline,
    tagline_intro,
    bg_product,
    accent_circle,
    product_img,
    product_label,
    price_tag,
    bg_cta,
    cta_text,
    cta_bar,
    website,
    logo,
)

comp.render(str(output_dir / "social_media_ad.mp4"), preset="h264_1080p")
