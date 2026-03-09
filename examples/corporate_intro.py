"""Corporate Intro -- logo, company name, and animated tagline.

Creates a 7-second corporate brand intro featuring the company logo,
an animated company name, and a Typewriter-animated tagline entrance.
"""

from pathlib import Path

from pymotion import (
    Composition,
    GradientClip,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    TextClip,
)
from pymotion.clip.image import ImageClip
from pymotion.text.animated import Typewriter
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

DURATION = 210
comp = Composition(width=1920, height=1080, fps=30, duration=DURATION)

background = GradientClip(color_start="#0C1222", color_end="#1B2838", direction=180.0)
background.set_duration(DURATION)

logo = ImageClip(source=assets / "logo.png")
logo.set_duration(120).at(20).set_position(860, 200)

logo_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=20, value=0.0, easing="ease_out_cubic"),
        Keyframe(frame=50, value=1.0),
    ]
)

line_left = ShapeClip.rect(x=760, y=480, w=400, h=2, fill="#3498DB")
line_left.set_duration(DURATION)

line_right = ShapeClip.rect(x=760, y=600, w=400, h=2, fill="#3498DB")
line_right.set_duration(DURATION)

company_name = TextClip(
    text="ACME CORPORATION",
    font="Arial",
    size=56.0,
    color="#FFFFFF",
)
company_name.set_duration(150).at(60).set_position(960, 510)

name_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=60, value=0.0, easing="ease_out_cubic"),
        Keyframe(frame=85, value=1.0, easing="linear"),
        Keyframe(frame=180, value=1.0, easing="ease_in_quad"),
        Keyframe(frame=209, value=0.0),
    ]
)

separator = ShapeClip.rect(x=860, y=560, w=200, h=1, fill="#3498DB")
separator.set_duration(130).at(70).set_opacity(0.8)

tagline = Typewriter(
    text="Innovation Through Excellence",
    font_size=28.0,
    color=Color(0.53, 0.6, 0.67, 1.0),
    chars_per_frame=0.8,
    cursor=True,
    position=Vec2(750.0, 620.0),
)
tagline.set_duration(120).at(90)

corner_tl = ShapeClip.rect(x=80, y=80, w=60, h=2, fill="#3498DB")
corner_tl.set_duration(180).at(30).set_opacity(0.4)

corner_tl_v = ShapeClip.rect(x=80, y=80, w=2, h=60, fill="#3498DB")
corner_tl_v.set_duration(180).at(30).set_opacity(0.4)

corner_br = ShapeClip.rect(x=1780, y=998, w=60, h=2, fill="#3498DB")
corner_br.set_duration(180).at(30).set_opacity(0.4)

corner_br_v = ShapeClip.rect(x=1838, y=940, w=2, h=60, fill="#3498DB")
corner_br_v.set_duration(180).at(30).set_opacity(0.4)

comp.add(background, line_left, line_right, logo, company_name, separator, tagline)
comp.add(corner_tl, corner_tl_v, corner_br, corner_br_v)

comp.render(str(output_dir / "corporate_intro.mp4"), preset="h264_1080p")
