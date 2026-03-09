"""Social Media Ad — short promotional video with text, effects, and transitions.

Creates a 6-second social media advertisement at 1080x1080 (square format)
with animated text overlays, color effects, and a call-to-action.
"""

from pymotion import (
    ColorClip,
    Composition,
    GradientClip,
    Keyframe,
    KeyframeTrack,
    ShapeClip,
    TextClip,
    Track,
)

# Square format for Instagram/TikTok — 6 seconds at 30 fps
comp = Composition(width=1080, height=1080, fps=30, duration=180)

# --- Scene 1: Bold intro (frames 0-59) ---

bg_intro = GradientClip(
    color_start="#FF6B35",
    color_end="#F7C948",
    direction=135.0,
)
bg_intro.set_duration(60)

headline = TextClip(
    text="SUMMER SALE",
    font="Arial",
    size=96.0,
    color="#FFFFFF",
)
headline.set_duration(60).set_position(540, 440)

tagline = TextClip(
    text="Up to 70% off",
    font="Arial",
    size=48.0,
    color="#1A1A2E",
)
tagline.set_duration(60).set_position(540, 560)

# --- Scene 2: Product feature (frames 60-119) ---

bg_product = GradientClip(
    color_start="#1A1A2E",
    color_end="#16213E",
    direction=90.0,
)
bg_product.set_duration(60).at(60)

# Decorative circle behind product area
accent_circle = ShapeClip.circle(cx=540, cy=480, r=200, fill="#FF6B35")
accent_circle.set_duration(60).at(60).set_opacity(0.3)

product_text = TextClip(
    text="Premium Collection",
    font="Arial",
    size=64.0,
    color="#F7C948",
)
product_text.set_duration(60).at(60).set_position(540, 750)

# --- Scene 3: Call to action (frames 120-179) ---

bg_cta = ColorClip(color="#FF6B35")
bg_cta.set_duration(60).at(120)

cta_text = TextClip(
    text="SHOP NOW",
    font="Arial",
    size=80.0,
    color="#FFFFFF",
)
cta_text.set_duration(60).at(120).set_position(540, 480)

# Animated underline bar
cta_bar = ShapeClip.rect(x=340, y=540, w=400, h=6, fill="#1A1A2E")
cta_bar.set_duration(60).at(120)

website = TextClip(
    text="www.example.com",
    font="Arial",
    size=32.0,
    color="#FFFFFF",
)
website.set_duration(60).at(120).set_position(540, 620).set_opacity(0.8)

# --- Animate the CTA text with a pulse-like scale via opacity ---

cta_opacity_track = KeyframeTrack(
    keyframes=[
        Keyframe(frame=120, value=0.0, easing="ease_out"),
        Keyframe(frame=135, value=1.0, easing="ease_in_out"),
        Keyframe(frame=155, value=1.0, easing="ease_in_out"),
        Keyframe(frame=179, value=0.8),
    ]
)

# --- Add all clips ---

track = Track()
track.add(
    bg_intro,
    headline,
    tagline,
    bg_product,
    accent_circle,
    product_text,
    bg_cta,
    cta_text,
    cta_bar,
    website,
)
comp.add(
    bg_intro,
    headline,
    tagline,
    bg_product,
    accent_circle,
    product_text,
    bg_cta,
    cta_text,
    cta_bar,
    website,
)

# --- Effects applied in a custom render loop ---
#
# vignette = Vignette(strength=0.4)
# glow = NeonGlow(strength=0.3)
# brightness = Brightness(value=1.05)
#
# for i in range(180):
#     frame = comp._render_frame(i)
#     frame = vignette.apply(frame, ctx)
#     if 120 <= i < 180:
#         frame = glow.apply(frame, ctx)
#     frame = brightness.apply(frame, ctx)

comp.render("social_media_ad.mp4", preset="h264_1080p")
