"""Real Estate Property Tour — Professional property listing video.

Niche: Real estate agents creating listing videos for properties.
Demonstrates: ImageClip (cover mode), TextClip with shadows, ShapeClip geometry,
              GradientClip (linear + radial), Typewriter animated text, particle
              effects (sparkles for luxury feel), blend modes (ADD),
              multi-track z-ordering.

Duration: ~16 seconds at 30 fps (480 frames).
"""

from pathlib import Path

from pymotion import (
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
    Track,
)
from pymotion.clip.base import BlendMode
from pymotion.clip.image import ImageClip
from pymotion.clip.text import Shadow
from pymotion.particle.system import sparkles
from pymotion.text.animated import Typewriter
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 16  # 480 frames = 16 seconds

# ═══════════════════════════════════════════════════════════════
# COMPOSITION SETUP
# ═══════════════════════════════════════════════════════════════
comp = Composition(
    width=1920,
    height=1080,
    fps=FPS,
    duration=DURATION,
    background="#0A0F1C",
)

# ═══════════════════════════════════════════════════════════════
# TRACK 1: BACKGROUND — Elegant dark gradient (full duration)
# ═══════════════════════════════════════════════════════════════
bg_track = Track(name="background")

bg_gradient = GradientClip(
    color_start="#0D1B2A",
    color_end="#1B263B",
    direction=135.0,
    gradient_type="linear",
)
bg_gradient.set_duration(DURATION)
bg_track.add(bg_gradient)

# Subtle radial glow
center_glow = GradientClip(
    color_start="#1B263B",
    color_end="#0D1B2A",
    gradient_type="radial",
    center_x=0.5,
    center_y=0.4,
    radius=0.6,
)
center_glow.set_duration(DURATION).set_opacity(0.3)
bg_track.add(center_glow)

# ═══════════════════════════════════════════════════════════════
# TRACK 2: PROPERTY PHOTOS — Sequential slideshow
# ═══════════════════════════════════════════════════════════════
photos_track = Track(name="photos")

photo_exterior = ImageClip(source=assets / "house_exterior.jpg", fit_mode="cover")
photo_exterior.set_duration(120).at(0)

photo_interior = ImageClip(source=assets / "house_interior.jpg", fit_mode="cover")
photo_interior.set_duration(120).at(120)

photo_kitchen = ImageClip(source=assets / "house_kitchen.jpg", fit_mode="cover")
photo_kitchen.set_duration(120).at(240)

photo_garden = ImageClip(source=assets / "house_garden.jpg", fit_mode="cover")
photo_garden.set_duration(120).at(360)

photos_track.add(photo_exterior, photo_interior, photo_kitchen, photo_garden)

# ═══════════════════════════════════════════════════════════════
# TRACK 3: DARK OVERLAYS — Bottom bar + top vignette
# ═══════════════════════════════════════════════════════════════
overlay_track = Track(name="overlay")

bottom_bar = ShapeClip.rect(x=0, y=800, w=1920, h=280, fill="#000000")
bottom_bar.set_duration(DURATION).set_opacity(0.75)
overlay_track.add(bottom_bar)

top_accent = ShapeClip.rect(x=0, y=798, w=1920, h=3, fill="#D4AF37")
top_accent.set_duration(DURATION)
overlay_track.add(top_accent)

top_vignette = GradientClip(
    color_start="#0D1B2ACC",
    color_end="#00000000",
    direction=180.0,
)
top_vignette.set_duration(DURATION).set_opacity(0.5)
overlay_track.add(top_vignette)

# ═══════════════════════════════════════════════════════════════
# TRACK 4: PERSISTENT TEXT — Title, address, price, features
# ═══════════════════════════════════════════════════════════════
text_track = Track(name="text")

title = TextClip(
    "Elegant Hillside Retreat",
    font="Arial",
    size=52.0,
    color="#FFFFFF",
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.7), offset_x=3, offset_y=3, blur=5),
)
title.set_duration(DURATION).set_position(120.0, 830.0)
text_track.add(title)

address = TextClip(
    "1247 Ocean View Drive, Malibu, CA 90265",
    font="Arial",
    size=24.0,
    color="#D4AF37",
)
address.set_duration(DURATION).set_position(120.0, 900.0)
text_track.add(address)

price = TextClip(
    "$4,250,000",
    font="Arial",
    size=44.0,
    color="#FFFFFF",
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.5), offset_x=2, offset_y=2, blur=3),
)
price.set_duration(DURATION).set_position(1500.0, 840.0)
text_track.add(price)

features = ["5 Bedrooms", "4.5 Bathrooms", "3,800 sq ft", "Ocean View"]
for i, feature_text in enumerate(features):
    dot = ShapeClip.circle(cx=140 + i * 300, cy=970, r=4, fill="#D4AF37")
    dot.set_duration(DURATION)
    text_track.add(dot)

    feat = TextClip(feature_text, font="Arial", size=20.0, color="#CCCCCC")
    feat.set_duration(DURATION).set_position(155.0 + i * 300, 960.0)
    text_track.add(feat)

# ═══════════════════════════════════════════════════════════════
# TRACK 5: ANIMATED TEXT — Typewriter tagline (extends full duration,
#           holds final text after animation completes)
# ═══════════════════════════════════════════════════════════════
anim_track = Track(name="animated")

# Typewriter: 43 chars at 1 char/frame = finishes at ~frame 73.
# Duration extends to DURATION so it holds the final text with no renderer jump.
agent_tagline = Typewriter(
    text="Luxury Living — Brooks & Associates Realty",
    font_size=18.0,
    color=Color(0.83, 0.69, 0.22, 1.0),
    chars_per_frame=1.0,
    cursor=False,
    position=Vec2(120.0, 1030.0),
)
agent_tagline.set_duration(DURATION - 30).at(30)
anim_track.add(agent_tagline)

# Section labels for each photo
section_labels = [
    ("EXTERIOR", 10, 110),
    ("INTERIOR", 130, 230),
    ("KITCHEN", 250, 350),
    ("GARDEN", 370, 470),
]
for label, start, end in section_labels:
    lbl = TextClip(
        label,
        font="Arial",
        size=14.0,
        color="#D4AF37",
        letter_spacing=6.0,
    )
    lbl.set_duration(end - start).at(start).set_position(1700.0, 130.0)
    anim_track.add(lbl)

# ═══════════════════════════════════════════════════════════════
# TRACK 6: FOR SALE BADGE + CORNER ACCENTS
# ═══════════════════════════════════════════════════════════════
badge_track = Track(name="badge")

badge_bg = ShapeClip.rect(x=1600, y=50, w=260, h=50, fill="#D4AF37")
badge_bg.set_duration(DURATION)
badge_track.add(badge_bg)

badge_text = TextClip("FOR SALE", font="Arial", size=24.0, color="#0D1B2A")
badge_text.set_duration(DURATION).set_position(1670.0, 60.0)
badge_track.add(badge_text)

corners = [
    ShapeClip.rect(x=40, y=40, w=80, h=2, fill="#D4AF37"),
    ShapeClip.rect(x=40, y=40, w=2, h=80, fill="#D4AF37"),
    ShapeClip.rect(x=1800, y=40, w=80, h=2, fill="#D4AF37"),
    ShapeClip.rect(x=1878, y=40, w=2, h=80, fill="#D4AF37"),
    ShapeClip.rect(x=40, y=780, w=80, h=2, fill="#D4AF37"),
    ShapeClip.rect(x=40, y=700, w=2, h=82, fill="#D4AF37"),
    ShapeClip.rect(x=1800, y=780, w=80, h=2, fill="#D4AF37"),
    ShapeClip.rect(x=1878, y=700, w=2, h=82, fill="#D4AF37"),
]
for corner in corners:
    corner.set_duration(DURATION).set_opacity(0.4)
    badge_track.add(corner)

# ═══════════════════════════════════════════════════════════════
# TRACK 7: SPARKLE PARTICLES — Subtle luxury ambiance
# ═══════════════════════════════════════════════════════════════
particles_track = Track(name="particles", blend_mode=BlendMode.ADD, opacity=0.12)

sparkle_sys = sparkles(1920, 1080)
sparkle_clip = sparkle_sys.to_clip(DURATION)
sparkle_clip.set_duration(DURATION)
particles_track.add(sparkle_clip)

# ═══════════════════════════════════════════════════════════════
# ASSEMBLE
# ═══════════════════════════════════════════════════════════════
comp.add_track(bg_track)
comp.add_track(photos_track)
comp.add_track(overlay_track)
comp.add_track(text_track)
comp.add_track(anim_track)
comp.add_track(badge_track)
comp.add_track(particles_track)

# ═══════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════
output_path = output_dir / "01_real_estate_tour.mp4"
comp.render(str(output_path), preset="h264_1080p")

comp.export_frame(60, str(output_dir / "01_real_estate_thumbnail.png"))
print(f"Rendered: {output_path}")
