"""Fitness/Gym Social Media Ad — High-energy promotional video.

Niche: Personal trainers and gyms creating Instagram Reels / TikTok ads.
Demonstrates: Bold typography, CountUp/CountDown animated numbers, ShapeClip
              polygons, ImageClip (cover mode), LetterByLetter animated text,
              particle effects (confetti), GradientClip, ColorClip,
              blend modes (ADD), Shadow.

Duration: ~12 seconds at 30 fps (360 frames).
Resolution: 1080x1920 (vertical/portrait for social media).
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
from pymotion.clip.color import ColorClip
from pymotion.clip.image import ImageClip
from pymotion.clip.text import Shadow
from pymotion.particle.system import confetti
from pymotion.text.animated import CountDown, CountUp, LetterByLetter
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 12  # 360 frames

# ═══════════════════════════════════════════════════════════════
# VERTICAL COMPOSITION (1080x1920 for Instagram/TikTok)
# ═══════════════════════════════════════════════════════════════
comp = Composition(
    width=1080,
    height=1920,
    fps=FPS,
    duration=DURATION,
    background="#000000",
)

# ═══════════════════════════════════════════════════════════════
# SECTION 1 (0–120): HERO — Bold intro with countdown
# ═══════════════════════════════════════════════════════════════
sec1 = Track(name="section1")

sec1_bg = GradientClip(
    color_start="#FF4500",
    color_end="#8B0000",
    direction=180.0,
)
sec1_bg.set_duration(120)
sec1.add(sec1_bg)

gym_img = ImageClip(source=assets / "fitness_gym.jpg", fit_mode="cover")
gym_img.set_duration(120).set_opacity(0.35)
sec1.add(gym_img)

dark_overlay = ColorClip("#000000")
dark_overlay.set_duration(120).set_opacity(0.3)
sec1.add(dark_overlay)

# "GET READY" — static bold text
get_ready = TextClip(
    "GET READY",
    font="Arial",
    size=80.0,
    color="#FFFFFF",
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.8), offset_x=4, offset_y=4, blur=6),
)
get_ready.set_duration(120).set_position(230.0, 600.0)
sec1.add(get_ready)

# Countdown 3→0 over 90 frames (3 seconds)
countdown = CountDown(
    start_value=3,
    end_value=0,
    font_size=200.0,
    color=Color(1.0, 0.27, 0.0, 1.0),
    decimals=0,
    position=Vec2(440.0, 800.0),
)
countdown.set_duration(90).at(10)
sec1.add(countdown)

# "YOUR TRANSFORMATION" — LetterByLetter (19 chars × 2 frames = done at 38,
#  extends to fill section so it holds the final text)
starts_text = LetterByLetter(
    text="YOUR TRANSFORMATION",
    font_size=32.0,
    color=Color(1.0, 0.84, 0.0, 1.0),
    frames_per_letter=2,
    position=Vec2(200.0, 1150.0),
)
starts_text.set_duration(110).at(10)
sec1.add(starts_text)

# Decorative diagonal stripes
stripe = ShapeClip.polygon(
    points=[(0, 1600), (1080, 1450), (1080, 1500), (0, 1650)],
    fill="#FF4500",
)
stripe.set_duration(120).set_opacity(0.7)
sec1.add(stripe)

stripe2 = ShapeClip.polygon(
    points=[(0, 1680), (1080, 1530), (1080, 1550), (0, 1700)],
    fill="#FFD700",
)
stripe2.set_duration(120).set_opacity(0.4)
sec1.add(stripe2)

# ═══════════════════════════════════════════════════════════════
# SECTION 2 (120–250): STATS — CountUp numbers over full section
# ═══════════════════════════════════════════════════════════════
sec2 = Track(name="section2")

sec2_bg = GradientClip(
    color_start="#0052D4",
    color_end="#4364F7",
    direction=225.0,
)
sec2_bg.set_duration(130).at(120)
sec2.add(sec2_bg)

running_img = ImageClip(source=assets / "fitness_running.jpg", fit_mode="cover")
running_img.set_duration(130).at(120).set_opacity(0.25)
sec2.add(running_img)

sec2_header = TextClip(
    "PROVEN RESULTS",
    font="Arial",
    size=48.0,
    color="#FFFFFF",
    letter_spacing=6.0,
)
sec2_header.set_duration(130).at(120).set_position(240.0, 280.0)
sec2.add(sec2_header)

sec2_line = ShapeClip.rect(x=240, y=350, w=600, h=4, fill="#FFD700")
sec2_line.set_duration(130).at(120)
sec2.add(sec2_line)

# Stat 1: Members — CountUp over full section duration
members_count = CountUp(
    start_value=0,
    end_value=5000,
    font_size=72.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    suffix="+",
    decimals=0,
    position=Vec2(100.0, 500.0),
)
members_count.set_duration(130).at(120)
sec2.add(members_count)

members_label = TextClip("Active Members", font="Arial", size=24.0, color="#AADDFF")
members_label.set_duration(130).at(120).set_position(100.0, 600.0)
sec2.add(members_label)

# Stat 2: Classes — CountUp
classes_count = CountUp(
    start_value=0,
    end_value=120,
    font_size=72.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    suffix="",
    decimals=0,
    position=Vec2(100.0, 750.0),
)
classes_count.set_duration(130).at(120)
sec2.add(classes_count)

classes_label = TextClip("Classes Per Week", font="Arial", size=24.0, color="#AADDFF")
classes_label.set_duration(130).at(120).set_position(100.0, 850.0)
sec2.add(classes_label)

# Stat 3: Satisfaction — CountUp
satisfaction = CountUp(
    start_value=0,
    end_value=98,
    font_size=72.0,
    color=Color(1.0, 0.84, 0.0, 1.0),
    suffix="%",
    decimals=0,
    position=Vec2(100.0, 1000.0),
)
satisfaction.set_duration(130).at(120)
sec2.add(satisfaction)

satisfaction_label = TextClip("Member Satisfaction", font="Arial", size=24.0, color="#AADDFF")
satisfaction_label.set_duration(130).at(120).set_position(100.0, 1100.0)
sec2.add(satisfaction_label)

# Separator lines
for y_sep in [700, 950]:
    sep_line = ShapeClip.rect(x=100, y=y_sep, w=880, h=1, fill="#FFFFFF")
    sep_line.set_duration(130).at(120).set_opacity(0.15)
    sec2.add(sep_line)

# ═══════════════════════════════════════════════════════════════
# SECTION 3 (250–360): CTA — Call to action
# ═══════════════════════════════════════════════════════════════
sec3 = Track(name="section3")

sec3_bg = GradientClip(
    color_start="#1B1B2F",
    color_end="#162447",
    direction=0.0,
)
sec3_bg.set_duration(110).at(250)
sec3.add(sec3_bg)

weights_img = ImageClip(source=assets / "fitness_weights.jpg", fit_mode="cover")
weights_img.set_duration(110).at(250).set_opacity(0.2)
sec3.add(weights_img)

join_text = TextClip(
    "JOIN NOW",
    font="Arial",
    size=96.0,
    color="#FFFFFF",
    shadow=Shadow(color=Color(0.0, 0.0, 0.0, 0.8), offset_x=4, offset_y=4, blur=6),
)
join_text.set_duration(110).at(250).set_position(260.0, 550.0)
sec3.add(join_text)

offer = TextClip(
    "FIRST MONTH FREE",
    font="Arial",
    size=44.0,
    color="#00FF88",
    letter_spacing=4.0,
)
offer.set_duration(110).at(250).set_position(220.0, 700.0)
sec3.add(offer)

offer_line = ShapeClip.rect(x=220, y=760, w=640, h=2, fill="#00FF88")
offer_line.set_duration(110).at(250).set_opacity(0.5)
sec3.add(offer_line)

btn_bg = ShapeClip.rect(
    x=250,
    y=860,
    w=580,
    h=80,
    fill="#FF4500",
    stroke="#FFFFFF",
    stroke_width=3,
)
btn_bg.set_duration(110).at(250)
sec3.add(btn_bg)

btn_text = TextClip("www.elitefit.com/join", font="Arial", size=28.0, color="#FFFFFF")
btn_text.set_duration(110).at(250).set_position(340.0, 878.0)
sec3.add(btn_text)

handle = TextClip("@elitefit_official", font="Arial", size=22.0, color="#AAAAAA")
handle.set_duration(110).at(250).set_position(380.0, 1020.0)
sec3.add(handle)

bottom_info = ShapeClip.rect(x=0, y=1750, w=1080, h=170, fill="#000000")
bottom_info.set_duration(110).at(250).set_opacity(0.8)
sec3.add(bottom_info)

info_text = TextClip(
    "HIIT  |  Yoga  |  Boxing  |  CrossFit  |  Spin",
    font="Arial",
    size=20.0,
    color="#AADDFF",
)
info_text.set_duration(110).at(250).set_position(200.0, 1810.0)
sec3.add(info_text)

# ═══════════════════════════════════════════════════════════════
# CONFETTI — Over the CTA section
# ═══════════════════════════════════════════════════════════════
confetti_track = Track(name="confetti", blend_mode=BlendMode.ADD, opacity=0.15)

confetti_sys = confetti(1080, 1920)
confetti_clip = confetti_sys.to_clip(110)
confetti_clip.set_duration(110).at(250)
confetti_track.add(confetti_clip)

# ═══════════════════════════════════════════════════════════════
# ASSEMBLE
# ═══════════════════════════════════════════════════════════════
comp.add_track(sec1)
comp.add_track(sec2)
comp.add_track(sec3)
comp.add_track(confetti_track)

# ═══════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════
output_path = output_dir / "03_fitness_social_ad.mp4"
comp.render(str(output_path), preset="h264_1080p")

comp.export_frame(200, str(output_dir / "03_fitness_thumbnail.png"))
print(f"Rendered: {output_path}")
