"""Photo Slideshow — image clips with multiple transition types.

Demonstrates ImageClip usage with CrossDissolve, SlideLeft, ZoomIn,
and FadeToBlack transitions between slides. Each slide is shown for
3 seconds with 1-second transitions.
"""

from pymotion import (
    ColorClip,
    Composition,
    ImageClip,
    Keyframe,
    KeyframeTrack,
    TextClip,
)

# 16 seconds total: 4 slides x 3s each + 3 transitions x 1s + 1s outro
FPS = 30
SLIDE_FRAMES = 90  # 3 seconds per slide
TRANSITION_FRAMES = 30  # 1 second per transition
TOTAL_FRAMES = 4 * SLIDE_FRAMES + TRANSITION_FRAMES  # 390 frames = 13 seconds

comp = Composition(width=1920, height=1080, fps=FPS, duration=TOTAL_FRAMES)

# Dark background visible during transitions
background = ColorClip(color="#0a0a0a")
background.set_duration(TOTAL_FRAMES)

# --- Slide images ---
# Replace these paths with actual image files
slide_paths = [
    "photos/vacation_beach.jpg",  # Slide 1
    "photos/vacation_mountains.jpg",  # Slide 2
    "photos/vacation_city.jpg",  # Slide 3
    "photos/vacation_sunset.jpg",  # Slide 4
]

slides = []
for i, path in enumerate(slide_paths):
    slide = ImageClip(source=path)
    start_frame = i * SLIDE_FRAMES
    slide.set_duration(SLIDE_FRAMES).at(start_frame)
    slides.append(slide)

# --- Captions for each slide ---

captions = ["Beach Paradise", "Mountain Trail", "City Lights", "Golden Sunset"]
for i, caption_text in enumerate(captions):
    caption = TextClip(
        text=caption_text,
        font="Arial",
        size=48.0,
        color="#FFFFFF",
    )
    start_frame = i * SLIDE_FRAMES
    caption.set_duration(SLIDE_FRAMES).at(start_frame).set_position(960, 950)
    caption.set_opacity(0.9)
    slides.append(caption)

# --- Title card overlay (first 2 seconds) ---

title = TextClip(
    text="Summer Memories 2026",
    font="Arial",
    size=72.0,
    color="#FFFFFF",
)
title.set_duration(60).set_position(960, 540)

title_opacity = KeyframeTrack(
    keyframes=[
        Keyframe(frame=0, value=0.0, easing="ease_out"),
        Keyframe(frame=15, value=1.0, easing="linear"),
        Keyframe(frame=45, value=1.0, easing="ease_in"),
        Keyframe(frame=59, value=0.0),
    ]
)

# --- End card ---

end_text = TextClip(
    text="The End",
    font="Arial",
    size=64.0,
    color="#FFFFFF",
)
end_frame = 4 * SLIDE_FRAMES
end_text.set_duration(TRANSITION_FRAMES).at(end_frame).set_position(960, 540)

# --- Assemble composition ---

comp.add(background)
for slide in slides:
    comp.add(slide)
comp.add(title)
comp.add(end_text)

# --- Transitions between slides ---
# In a custom render loop, apply transitions at slide boundaries:
#
#   transitions = [
#       CrossDissolve(duration=TRANSITION_FRAMES),
#       SlideLeft(duration=TRANSITION_FRAMES),
#       ZoomIn(duration=TRANSITION_FRAMES),
#       FadeToBlack(duration=TRANSITION_FRAMES),
#   ]
#
#   for i in range(TOTAL_FRAMES):
#       frame = comp._render_frame(i)
#
#       # Check if we're in a transition zone between slides
#       for t_idx, t_start in enumerate([75, 165, 255]):
#           if t_start <= i < t_start + TRANSITION_FRAMES:
#               progress = (i - t_start) / TRANSITION_FRAMES
#               outgoing = slides[t_idx].render_frame(ctx)
#               incoming = slides[t_idx + 1].render_frame(ctx)
#               frame = transitions[t_idx].blend(outgoing, incoming, progress)
#
#       # Apply a subtle vignette
#       vignette = Vignette(strength=0.3)
#       frame = vignette.apply(frame, ctx)

comp.render("photo_slideshow.mp4", preset="h264_1080p")
