"""YouTube Tech Review Intro — Energetic channel intro sequence.

Niche: Tech YouTubers creating branded channel intros.
Demonstrates: Animated text (Typewriter, CountUp), ShapeClip geometry,
              GradientClip (radial, conic), ImageClip, particle effects
              (fire for energy), blend modes (ADD), multi-phase layout, Shadow.

Duration: ~14 seconds at 30 fps (420 frames).
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
from pymotion.particle.system import fire
from pymotion.text.animated import CountUp, Typewriter
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 14  # 420 frames

# ═══════════════════════════════════════════════════════════════
# COMPOSITION
# ═══════════════════════════════════════════════════════════════
comp = Composition(
    width=1920,
    height=1080,
    fps=FPS,
    duration=DURATION,
    background="#000000",
)

# ═══════════════════════════════════════════════════════════════
# PHASE 1 (0–140): DARK BUILD-UP — Channel name + tagline
# ═══════════════════════════════════════════════════════════════
phase1 = Track(name="phase1")

dark_bg = GradientClip(
    color_start="#050510",
    color_end="#0A0A2A",
    gradient_type="radial",
    center_x=0.5,
    center_y=0.5,
    radius=0.8,
)
dark_bg.set_duration(140)
phase1.add(dark_bg)

tech_bg = ImageClip(source=assets / "tech_circuit.jpg", fit_mode="cover")
tech_bg.set_duration(140).set_opacity(0.15)
phase1.add(tech_bg)

# Channel name — static (no Scramble, which causes jitter)
channel_name_1 = TextClip(
    "BYTECRAFT",
    font="Arial",
    size=96.0,
    color="#FFFFFF",
    letter_spacing=12.0,
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.8), offset_x=4, offset_y=4, blur=6),
)
channel_name_1.set_duration(140).set_position(560.0, 380.0)
phase1.add(channel_name_1)

# Tagline — Typewriter (43 chars at 1.5/frame ≈ finishes frame 19, holds rest)
intro_tagline = Typewriter(
    text="Honest Tech. Real Reviews.",
    font_size=32.0,
    color=Color(0.4, 0.8, 1.0, 1.0),
    chars_per_frame=1.5,
    cursor=False,
    position=Vec2(680.0, 520.0),
)
intro_tagline.set_duration(130).at(10)
phase1.add(intro_tagline)

# Accent lines
accent_left = ShapeClip.rect(x=540, y=490, w=120, h=2, fill="#4FC3F7")
accent_left.set_duration(120).at(20)
phase1.add(accent_left)

accent_right = ShapeClip.rect(x=1260, y=490, w=120, h=2, fill="#4FC3F7")
accent_right.set_duration(120).at(20)
phase1.add(accent_right)

# Decorative dots
for i in range(5):
    dot = ShapeClip.circle(cx=700 + i * 100, cy=575, r=3, fill="#4FC3F7")
    dot.set_duration(90).at(50)
    phase1.add(dot)

# ═══════════════════════════════════════════════════════════════
# PHASE 2 (140–280): CHANNEL SHOWCASE — Device bg + sub count
# ═══════════════════════════════════════════════════════════════
phase2 = Track(name="phase2")

reveal_bg = GradientClip(
    color_start="#0F0C29",
    color_end="#302B63",
    gradient_type="radial",
    center_x=0.5,
    center_y=0.4,
    radius=0.7,
)
reveal_bg.set_duration(140).at(140)
phase2.add(reveal_bg)

device_img = ImageClip(source=assets / "tech_device.jpg", fit_mode="contain")
device_img.set_duration(140).at(140).set_opacity(0.35)
phase2.add(device_img)

channel_name_main = TextClip(
    "BYTECRAFT",
    font="Arial",
    size=96.0,
    color="#FFFFFF",
    letter_spacing=8.0,
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.6), offset_x=3, offset_y=3, blur=5),
)
channel_name_main.set_duration(140).at(140).set_position(560.0, 310.0)
phase2.add(channel_name_main)

tagline_static = TextClip(
    "Honest Tech. Real Reviews.",
    font="Arial",
    size=32.0,
    color="#4FC3F7",
)
tagline_static.set_duration(140).at(140).set_position(680.0, 440.0)
phase2.add(tagline_static)

for rect_x in [540, 1260]:
    line = ShapeClip.rect(x=rect_x, y=460, w=120, h=2, fill="#4FC3F7")
    line.set_duration(140).at(140)
    phase2.add(line)

# Subscriber CountUp — full phase duration, counts over entire phase
sub_count = CountUp(
    start_value=0,
    end_value=1247000,
    font_size=22.0,
    color=Color(1.0, 0.4, 0.4, 1.0),
    suffix=" subscribers",
    decimals=0,
    position=Vec2(800.0, 500.0),
)
sub_count.set_duration(140).at(140)
phase2.add(sub_count)

# Stats bar at bottom
stats_bar = ShapeClip.rect(x=0, y=950, w=1920, h=130, fill="#000000")
stats_bar.set_duration(140).at(140).set_opacity(0.7)
phase2.add(stats_bar)

stats_items = [
    ("1.2M Subs", 350),
    ("500+ Videos", 700),
    ("Weekly Reviews", 1050),
    ("4 Years Running", 1400),
]
for text_str, x_pos in stats_items:
    stat = TextClip(text_str, font="Arial", size=18.0, color="#AAAAAA")
    stat.set_duration(140).at(140).set_position(float(x_pos), 1000.0)
    phase2.add(stat)

for x_pos in [600, 950, 1300]:
    sep = ShapeClip.circle(cx=x_pos, cy=1010, r=3, fill="#4FC3F7")
    sep.set_duration(140).at(140)
    phase2.add(sep)

# ═══════════════════════════════════════════════════════════════
# PHASE 3 (280–420): REVIEW TEASER — Product showcase + rating
# ═══════════════════════════════════════════════════════════════
phase3 = Track(name="phase3")

conic_bg = GradientClip(
    color_start="#1A1A2E",
    color_end="#16213E",
    direction=45.0,
    gradient_type="conic",
    center_x=0.5,
    center_y=0.5,
)
conic_bg.set_duration(140).at(280)
phase3.add(conic_bg)

workspace = ImageClip(source=assets / "tech_workspace.jpg", fit_mode="cover")
workspace.set_duration(140).at(280).set_opacity(0.4)
phase3.add(workspace)

# Dark panel
dark_panel = ShapeClip.rect(x=400, y=250, w=1120, h=500, fill="#000000")
dark_panel.set_duration(140).at(280).set_opacity(0.6)
phase3.add(dark_panel)

panel_border = ShapeClip.rect(
    x=400,
    y=250,
    w=1120,
    h=500,
    fill="#00000000",
    stroke="#4FC3F7",
    stroke_width=1,
)
panel_border.set_duration(140).at(280).set_opacity(0.4)
phase3.add(panel_border)

review_header = TextClip(
    "TODAY'S REVIEW",
    font="Arial",
    size=20.0,
    color="#FF6B6B",
    letter_spacing=6.0,
)
review_header.set_duration(140).at(280).set_position(840.0, 280.0)
phase3.add(review_header)

header_line = ShapeClip.rect(x=840, y=310, w=240, h=2, fill="#FF6B6B")
header_line.set_duration(140).at(280).set_opacity(0.6)
phase3.add(header_line)

# Product name — Typewriter (20 chars at 2/frame = done by frame 10, holds rest)
product_type = Typewriter(
    text="MacBook Pro M4 Ultra",
    font_size=56.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    chars_per_frame=2.0,
    cursor=False,
    position=Vec2(530.0, 370.0),
)
product_type.set_duration(140).at(280)
phase3.add(product_type)

# Rating CountUp — counts from 0 to 9.2 over full phase
rating = CountUp(
    start_value=0.0,
    end_value=9.2,
    font_size=64.0,
    color=Color(1.0, 0.84, 0.0, 1.0),
    suffix=" / 10",
    decimals=1,
    position=Vec2(810.0, 480.0),
)
rating.set_duration(140).at(280)
phase3.add(rating)

# Rating dots
for i in range(5):
    fill = "#FFD700" if i < 4 else "#555555"
    star = ShapeClip.circle(cx=830 + i * 50, cy=590, r=12, fill=fill)
    star.set_duration(120).at(300)
    phase3.add(star)

half_star = ShapeClip.circle(cx=1030, cy=590, r=8, fill="#FFD700")
half_star.set_duration(120).at(300)
phase3.add(half_star)

# ═══════════════════════════════════════════════════════════════
# FIRE PARTICLES — Energy during phase 2
# ═══════════════════════════════════════════════════════════════
fx_track = Track(name="effects", blend_mode=BlendMode.ADD, opacity=0.08)

fire_sys = fire(1920, 1080)
fire_clip = fire_sys.to_clip(140)
fire_clip.set_duration(140).at(140)
fx_track.add(fire_clip)

# ═══════════════════════════════════════════════════════════════
# VIGNETTE OVERLAY
# ═══════════════════════════════════════════════════════════════
vignette_track = Track(name="vignette")

vignette_gradient = GradientClip(
    color_start="#00000000",
    color_end="#000000CC",
    gradient_type="radial",
    center_x=0.5,
    center_y=0.5,
    radius=0.6,
)
vignette_gradient.set_duration(DURATION).set_opacity(0.3)
vignette_track.add(vignette_gradient)

# ═══════════════════════════════════════════════════════════════
# ASSEMBLE
# ═══════════════════════════════════════════════════════════════
comp.add_track(phase1)
comp.add_track(phase2)
comp.add_track(phase3)
comp.add_track(fx_track)
comp.add_track(vignette_track)

# ═══════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════
output_path = output_dir / "02_tech_review_intro.mp4"
comp.render(str(output_path), preset="h264_1080p")

comp.export_frame(210, str(output_dir / "02_tech_review_thumbnail.png"))
print(f"Rendered: {output_path}")
