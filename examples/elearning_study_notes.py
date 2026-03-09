"""E-Learning Study Notes — clean educational video with topic overview.

Demonstrates TextClip for structured content, ShapeClip for layout
elements, and sequential clip timing for progressive reveal.
"""

from pathlib import Path

from pymotion import (
    Composition,
    ShapeClip,
    TextClip,
)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "elearning_study_notes.mp4"

FPS = 30
DURATION = 180
comp = Composition(width=1920, height=1080, fps=FPS, duration=DURATION, background="#F5F5FA")

sidebar = ShapeClip.rect(x=0, y=0, w=80, h=1080, fill="#3366CC")
sidebar.set_duration(DURATION)

header_bg = ShapeClip.rect(x=80, y=0, w=1840, h=120, fill="#FFFFFF")
header_bg.set_duration(DURATION)

title = TextClip(text="Chapter 3: Data Structures", font="Arial", size=42.0, color="#222244")
title.set_duration(DURATION).set_position(140, 40)

subtitle = TextClip(text="Computer Science 101", font="Arial", size=22.0, color="#6666AA")
subtitle.set_duration(DURATION).set_position(140, 88)

topics = [
    ("Arrays", "Contiguous memory, O(1) access, fixed size"),
    ("Linked Lists", "Dynamic size, O(n) access, pointer-based"),
    ("Hash Tables", "Key-value pairs, O(1) average lookup"),
]

topic_clips = []
for i, (topic_name, description) in enumerate(topics):
    y_base = 160 + i * 140
    start_frame = 15 + i * 30

    card = ShapeClip.rect(x=140, y=y_base, w=1600, h=110, fill="#FFFFFF")
    card.set_duration(DURATION - start_frame).at(start_frame)
    topic_clips.append(card)

    name = TextClip(text=topic_name, font="Arial", size=30.0, color="#222244")
    name.set_duration(DURATION - start_frame).at(start_frame).set_position(180, y_base + 18)
    topic_clips.append(name)

    desc = TextClip(text=description, font="Arial", size=20.0, color="#666688")
    desc.set_duration(DURATION - start_frame).at(start_frame).set_position(180, y_base + 60)
    topic_clips.append(desc)

page_num = TextClip(text="3 / 12", font="Arial", size=18.0, color="#888899")
page_num.set_duration(DURATION).set_position(1700, 1040)

comp.add(sidebar, header_bg, title, subtitle)
for clip in topic_clips:
    comp.add(clip)
comp.add(page_num)

comp.render(str(output_path), preset="h264_1080p")
print(f"Rendered: {output_path.relative_to(Path(__file__).parent)}")
