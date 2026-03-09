"""Trip Souvenir — travel photo slideshow with location captions.

Demonstrates ImageClip for photo display with warm color overlays,
location text captions, and smooth transitions between four photos.
"""

from pathlib import Path

from pymotion import (
    Composition,
    GradientClip,
    ImageClip,
    ShapeClip,
    TextClip,
)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
assets = Path(__file__).parent / "assets"
output_path = output_dir / "trip_souvenir.mp4"

FPS = 30
SLIDE_FRAMES = 120
NUM_SLIDES = 4
DURATION = SLIDE_FRAMES * NUM_SLIDES

comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#1A0A00")

photos = [
    (assets / "photo_beach.png", "Malibu Beach", "California, USA"),
    (assets / "photo_mountains.png", "Swiss Alps", "Zermatt, Switzerland"),
    (assets / "photo_city.png", "Tokyo Nights", "Shibuya, Japan"),
    (assets / "photo_sunset.png", "Golden Hour", "Santorini, Greece"),
]

warm_overlay = GradientClip(
    color_start="#331A00",
    color_end="#000000",
    direction=0.0,
    gradient_type="linear",
)
warm_overlay.set_duration(DURATION).set_opacity(0.25)

for i, (photo_path, title_text, location_text) in enumerate(photos):
    start = i * SLIDE_FRAMES

    photo = ImageClip(source=photo_path)
    photo.set_duration(SLIDE_FRAMES).at(start)

    caption_bg = ShapeClip.rect(x=0, y=820, w=1920, h=260, fill="#000000")
    caption_bg.set_duration(SLIDE_FRAMES).at(start).set_opacity(0.6)

    title = TextClip(text=title_text, font="Arial", size=48.0, color="#FFFFFF")
    title.set_duration(SLIDE_FRAMES).at(start).set_position(120, 860)

    location = TextClip(text=location_text, font="Arial", size=28.0, color="#FFCC88")
    location.set_duration(SLIDE_FRAMES).at(start).set_position(120, 920)

    slide_num = TextClip(
        text=f"{i + 1} / {NUM_SLIDES}",
        font="Arial",
        size=20.0,
        color="#AAAAAA",
    )
    slide_num.set_duration(SLIDE_FRAMES).at(start).set_position(1760, 1040)

    comp.add(photo)
    comp.add(caption_bg)
    comp.add(title)
    comp.add(location)
    comp.add(slide_num)

comp.add(warm_overlay)

comp.render(str(output_path), preset="h264_1080p")
