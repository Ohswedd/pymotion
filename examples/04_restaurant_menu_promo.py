"""Restaurant Menu Promo — Elegant food showcase video.

Niche: Restaurant owners creating menu promo videos for social media / TV displays.
Demonstrates: Warm color palettes, ImageClip with fit modes, TextClip with shadows
              and letter spacing, GradientClip (linear + radial), ShapeClip (rect,
              circle, line, ellipse, polygon), Typewriter + WordByWord animated text,
              particle effects (stars for ambiance), blend modes (SCREEN).

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
from pymotion.particle.system import stars
from pymotion.text.animated import Typewriter, WordByWord
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 16  # 480 frames

# ═══════════════════════════════════════════════════════════════
# COMPOSITION — Warm, elegant feel
# ═══════════════════════════════════════════════════════════════
comp = Composition(
    width=1920,
    height=1080,
    fps=FPS,
    duration=DURATION,
    background="#1A0E0A",
)

# ═══════════════════════════════════════════════════════════════
# LAYER 1: BASE — Warm gradient + borders (full duration)
# ═══════════════════════════════════════════════════════════════
base = Track(name="base")

warm_bg = GradientClip(
    color_start="#1A0E0A",
    color_end="#2C1810",
    direction=180.0,
)
warm_bg.set_duration(DURATION)
base.add(warm_bg)

center_glow = GradientClip(
    color_start="#3D1F0E",
    color_end="#1A0E0A",
    gradient_type="radial",
    center_x=0.5,
    center_y=0.5,
    radius=0.5,
)
center_glow.set_duration(DURATION).set_opacity(0.4)
base.add(center_glow)

top_border = ShapeClip.rect(x=0, y=0, w=1920, h=4, fill="#C8963E")
top_border.set_duration(DURATION)
base.add(top_border)

bottom_gold = ShapeClip.rect(x=0, y=1076, w=1920, h=4, fill="#C8963E")
bottom_gold.set_duration(DURATION)
base.add(bottom_gold)

# ═══════════════════════════════════════════════════════════════
# LAYER 2: OPENING (0–150) — Restaurant name + tagline
# ═══════════════════════════════════════════════════════════════
opening = Track(name="opening")

ambiance = ImageClip(source=assets / "food_ambiance.jpg", fit_mode="cover")
ambiance.set_duration(150).set_opacity(0.2)
opening.add(ambiance)

rest_name = TextClip(
    "LA MAISON DORÉE",
    font="Arial",
    size=64.0,
    color="#C8963E",
    letter_spacing=12.0,
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.6), offset_x=2, offset_y=2, blur=4),
)
rest_name.set_duration(150).set_position(480.0, 380.0)
opening.add(rest_name)

line_left = ShapeClip.line(x1=480, y1=460, x2=720, y2=460, color="#C8963E", width=1)
line_left.set_duration(150)
opening.add(line_left)

line_right = ShapeClip.line(x1=1200, y1=460, x2=1440, y2=460, color="#C8963E", width=1)
line_right.set_duration(150)
opening.add(line_right)

diamond = ShapeClip.polygon(
    points=[(960, 450), (970, 460), (960, 470), (950, 460)],
    fill="#C8963E",
)
diamond.set_duration(150)
opening.add(diamond)

# Typewriter tagline — 30 chars at 1/frame ≈ done by frame 45, holds rest
tagline = Typewriter(
    text="Fine French Cuisine Since 1987",
    font_size=24.0,
    color=Color(0.8, 0.7, 0.55, 1.0),
    chars_per_frame=1.0,
    cursor=False,
    position=Vec2(720.0, 510.0),
)
tagline.set_duration(135).at(15)
opening.add(tagline)

# ═══════════════════════════════════════════════════════════════
# LAYER 3: DISH 1 (150–300) — Filet Mignon
# ═══════════════════════════════════════════════════════════════
dish1_track = Track(name="dish1")

menu_header = TextClip(
    "CHEF'S SELECTION",
    font="Arial",
    size=28.0,
    color="#C8963E",
    letter_spacing=8.0,
)
menu_header.set_duration(150).at(150).set_position(780.0, 50.0)
dish1_track.add(menu_header)

header_line = ShapeClip.rect(x=780, y=90, w=360, h=1, fill="#C8963E")
header_line.set_duration(150).at(150).set_opacity(0.6)
dish1_track.add(header_line)

dish1_img = ImageClip(source=assets / "food_plate.jpg", fit_mode="contain")
dish1_img.set_duration(150).at(150).set_position(-300, 0)
dish1_track.add(dish1_img)

panel1_bg = ShapeClip.rect(x=1050, y=180, w=750, h=450, fill="#1A0E0A")
panel1_bg.set_duration(150).at(150).set_opacity(0.85)
dish1_track.add(panel1_bg)

panel1_border = ShapeClip.rect(
    x=1050,
    y=180,
    w=750,
    h=450,
    fill="#00000000",
    stroke="#C8963E",
    stroke_width=1,
)
panel1_border.set_duration(150).at(150).set_opacity(0.5)
dish1_track.add(panel1_border)

dish1_name = TextClip(
    "Filet Mignon au Poivre",
    font="Arial",
    size=36.0,
    color="#FFFFFF",
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.5), offset_x=1, offset_y=1, blur=2),
)
dish1_name.set_duration(150).at(150).set_position(1100.0, 230.0)
dish1_track.add(dish1_name)

dish1_line = ShapeClip.rect(x=1100, y=280, w=200, h=1, fill="#C8963E")
dish1_line.set_duration(150).at(150).set_opacity(0.4)
dish1_track.add(dish1_line)

# WordByWord description — 8 words at 6 frames/word = done at 48, holds rest
dish1_desc = WordByWord(
    text="Prime beef tenderloin with crushed peppercorn crust",
    font_size=20.0,
    color=Color(0.7, 0.65, 0.55, 1.0),
    frames_per_word=6,
    position=Vec2(1100.0, 310.0),
)
dish1_desc.set_duration(140).at(160)
dish1_track.add(dish1_desc)

dish1_wine = TextClip(
    "Pairs with: Château Margaux 2015",
    font="Arial",
    size=16.0,
    color="#998866",
)
dish1_wine.set_duration(120).at(180).set_position(1100.0, 370.0)
dish1_track.add(dish1_wine)

dish1_price = TextClip("$68", font="Arial", size=48.0, color="#C8963E")
dish1_price.set_duration(150).at(150).set_position(1100.0, 430.0)
dish1_track.add(dish1_price)

# ═══════════════════════════════════════════════════════════════
# LAYER 4: DISH 2 (300–450) — Lobster Thermidor
# ═══════════════════════════════════════════════════════════════
dish2_track = Track(name="dish2")

dish2_img = ImageClip(source=assets / "food_table.jpg", fit_mode="contain")
dish2_img.set_duration(150).at(300).set_position(300, 0)
dish2_track.add(dish2_img)

panel2_bg = ShapeClip.rect(x=100, y=180, w=750, h=450, fill="#1A0E0A")
panel2_bg.set_duration(150).at(300).set_opacity(0.85)
dish2_track.add(panel2_bg)

panel2_border = ShapeClip.rect(
    x=100,
    y=180,
    w=750,
    h=450,
    fill="#00000000",
    stroke="#C8963E",
    stroke_width=1,
)
panel2_border.set_duration(150).at(300).set_opacity(0.5)
dish2_track.add(panel2_border)

dish2_name = TextClip(
    "Lobster Thermidor",
    font="Arial",
    size=36.0,
    color="#FFFFFF",
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.5), offset_x=1, offset_y=1, blur=2),
)
dish2_name.set_duration(150).at(300).set_position(150.0, 230.0)
dish2_track.add(dish2_name)

dish2_line = ShapeClip.rect(x=150, y=280, w=200, h=1, fill="#C8963E")
dish2_line.set_duration(150).at(300).set_opacity(0.4)
dish2_track.add(dish2_line)

# WordByWord description
dish2_desc = WordByWord(
    text="Whole Maine lobster with Gruyere cream and cognac reduction",
    font_size=20.0,
    color=Color(0.7, 0.65, 0.55, 1.0),
    frames_per_word=6,
    position=Vec2(150.0, 310.0),
)
dish2_desc.set_duration(140).at(310)
dish2_track.add(dish2_desc)

dish2_wine = TextClip(
    "Pairs with: Puligny-Montrachet 2018",
    font="Arial",
    size=16.0,
    color="#998866",
)
dish2_wine.set_duration(120).at(330).set_position(150.0, 370.0)
dish2_track.add(dish2_wine)

dish2_price = TextClip("$85", font="Arial", size=48.0, color="#C8963E")
dish2_price.set_duration(150).at(300).set_position(150.0, 430.0)
dish2_track.add(dish2_price)

dessert_small = ImageClip(source=assets / "food_dessert.jpg", fit_mode="contain")
dessert_small.set_duration(150).at(300).set_position(0, 200).set_opacity(0.1)
dish2_track.add(dessert_small)

# ═══════════════════════════════════════════════════════════════
# LAYER 5: CLOSING (420–480) — Reservation CTA
# ═══════════════════════════════════════════════════════════════
closing = Track(name="closing")

dessert_full = ImageClip(source=assets / "food_dessert.jpg", fit_mode="cover")
dessert_full.set_duration(60).at(420).set_opacity(0.25)
closing.add(dessert_full)

reserve_text = TextClip(
    "RESERVE YOUR TABLE",
    font="Arial",
    size=52.0,
    color="#FFFFFF",
    letter_spacing=6.0,
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.8), offset_x=3, offset_y=3, blur=5),
)
reserve_text.set_duration(60).at(420).set_position(520.0, 380.0)
closing.add(reserve_text)

phone = TextClip("(310) 555-DINE", font="Arial", size=32.0, color="#C8963E")
phone.set_duration(60).at(420).set_position(770.0, 480.0)
closing.add(phone)

website_text = TextClip(
    "www.lamaisondoree.com",
    font="Arial",
    size=22.0,
    color="#998866",
)
website_text.set_duration(60).at(420).set_position(780.0, 540.0)
closing.add(website_text)

bottom_bar = ShapeClip.rect(x=0, y=950, w=1920, h=130, fill="#0D0705")
bottom_bar.set_duration(60).at(420).set_opacity(0.9)
closing.add(bottom_bar)

hours_text = TextClip(
    "Open Tue-Sun  |  5:30 PM - 11:00 PM  |  Dress Code: Smart Elegant",
    font="Arial",
    size=18.0,
    color="#998866",
)
hours_text.set_duration(60).at(420).set_position(550.0, 1000.0)
closing.add(hours_text)

# ═══════════════════════════════════════════════════════════════
# LAYER 6: AMBIENT STARS — Subtle twinkling
# ═══════════════════════════════════════════════════════════════
star_track = Track(name="stars", blend_mode=BlendMode.SCREEN, opacity=0.1)

stars_sys = stars(1920, 1080)
stars_clip = stars_sys.to_clip(DURATION)
stars_clip.set_duration(DURATION)
star_track.add(stars_clip)

# ═══════════════════════════════════════════════════════════════
# ASSEMBLE
# ═══════════════════════════════════════════════════════════════
comp.add_track(base)
comp.add_track(opening)
comp.add_track(dish1_track)
comp.add_track(dish2_track)
comp.add_track(closing)
comp.add_track(star_track)

# ═══════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════
output_path = output_dir / "04_restaurant_menu_promo.mp4"
comp.render(str(output_path), preset="h264_1080p")

comp.export_frame(75, str(output_dir / "04_restaurant_thumbnail.png"))
print(f"Rendered: {output_path}")
