"""Corporate Intro — professional intro with shapes, text, and smooth animations.

Creates a 7-second corporate brand intro with animated geometric shapes,
company name reveal, and tagline with eased keyframe animations.
"""

from pymotion import (
    Composition,
    GradientClip,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    TextClip,
    Vec2,
)

# 7 seconds at 30 fps
comp = Composition(width=1920, height=1080, fps=30, duration=210)

# Professional dark gradient background
background = GradientClip(
    color_start="#0C1222",
    color_end="#1B2838",
    direction=180.0,
)
background.set_duration(210)

# --- Animated accent lines ---

# Horizontal line sweeps in from left
line_top = ShapeClip.rect(x=0, y=480, w=400, h=2, fill="#3498DB")
line_top.set_duration(210)

line_top_pos = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=Vec2(-400.0, 480.0), easing="ease_out"),
        Keyframe(frame=40, value=Vec2(760.0, 480.0), easing="ease_in_out"),
        Keyframe(frame=60, value=Vec2(760.0, 480.0)),
    ]
)

# Matching line from right
line_bottom = ShapeClip.rect(x=1920, y=600, w=400, h=2, fill="#3498DB")
line_bottom.set_duration(210)

line_bottom_pos = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=Vec2(2320.0, 600.0), easing="ease_out"),
        Keyframe(frame=40, value=Vec2(760.0, 600.0), easing="ease_in_out"),
        Keyframe(frame=60, value=Vec2(760.0, 600.0)),
    ]
)

# --- Logo placeholder: geometric shape ---

# Diamond shape using a rotated square
logo_diamond = ShapeClip.rect(x=920, y=500, w=80, h=80, fill="#3498DB")
logo_diamond.set_duration(210)

logo_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=20, value=0.0, easing="ease_out"),
        Keyframe(frame=50, value=1.0),
    ]
)

# Inner accent circle
logo_circle = ShapeClip.circle(cx=960, cy=540, r=25, fill="#0C1222")
logo_circle.set_duration(210)

# --- Company name ---

company_name = TextClip(
    text="ACME CORPORATION",
    font="Arial",
    size=56.0,
    color="#FFFFFF",
)
company_name.set_duration(150).at(60).set_position(960, 540)

name_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=60, value=0.0, easing="ease_out"),
        Keyframe(frame=80, value=1.0, easing="linear"),
        Keyframe(frame=180, value=1.0, easing="ease_in"),
        Keyframe(frame=209, value=0.0),
    ]
)

# Thin separator line below company name
separator = ShapeClip.rect(x=860, y=580, w=200, h=1, fill="#3498DB")
separator.set_duration(130).at(70)

sep_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=70, value=0.0, easing="ease_out"),
        Keyframe(frame=90, value=0.8),
    ]
)

# --- Tagline ---

tagline = TextClip(
    text="Innovation Through Excellence",
    font="Arial",
    size=28.0,
    color="#8899AA",
)
tagline.set_duration(120).at(80).set_position(960, 620)

tagline_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=80, value=0.0, easing="ease_out"),
        Keyframe(frame=100, value=0.7, easing="linear"),
        Keyframe(frame=170, value=0.7, easing="ease_in"),
        Keyframe(frame=199, value=0.0),
    ]
)

# --- Subtle corner accents ---

corner_tl = ShapeClip.rect(x=80, y=80, w=60, h=2, fill="#3498DB")
corner_tl.set_duration(180).at(30).set_opacity(0.4)

corner_tl_v = ShapeClip.rect(x=80, y=80, w=2, h=60, fill="#3498DB")
corner_tl_v.set_duration(180).at(30).set_opacity(0.4)

corner_br = ShapeClip.rect(x=1780, y=998, w=60, h=2, fill="#3498DB")
corner_br.set_duration(180).at(30).set_opacity(0.4)

corner_br_v = ShapeClip.rect(x=1838, y=940, w=2, h=60, fill="#3498DB")
corner_br_v.set_duration(180).at(30).set_opacity(0.4)

# --- Assemble ---

comp.add(background)
comp.add(line_top)
comp.add(line_bottom)
comp.add(logo_diamond)
comp.add(logo_circle)
comp.add(company_name)
comp.add(separator)
comp.add(tagline)
comp.add(corner_tl, corner_tl_v)
comp.add(corner_br, corner_br_v)

# In a custom render loop, evaluate keyframe tracks and apply effects:
#
#   vignette = Vignette(strength=0.5)
#
#   for i in range(210):
#       # Update positions from keyframe tracks
#       pos = line_top_pos.value_at(i)
#       if isinstance(pos, Vec2):
#           line_top.set_position(pos.x, pos.y)
#
#       pos = line_bottom_pos.value_at(i)
#       if isinstance(pos, Vec2):
#           line_bottom.set_position(pos.x, pos.y)
#
#       # Update opacities
#       logo_diamond.set_opacity(logo_opacity.value_at(i))
#       logo_circle.set_opacity(logo_opacity.value_at(i))
#       company_name.set_opacity(name_opacity.value_at(i))
#       separator.set_opacity(sep_opacity.value_at(i))
#       tagline.set_opacity(tagline_opacity.value_at(i))
#
#       frame = comp._render_frame(i)
#       frame = vignette.apply(frame, ctx)

comp.render("corporate_intro.mp4", preset="h264_1080p")
