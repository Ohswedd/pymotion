"""Color Grading — color pipeline with LUT and grade.

Demonstrates the color pipeline: loading a .cube LUT, applying
lift/gamma/gain grading, and ACES tone mapping.
"""

from pymotion import ColorClip, Composition, TextClip
from pymotion.render.color_pipeline import (
    ColorGrade,
)

comp = Composition(width=1920, height=1080, fps=30, duration=150)

# Base scene
background = ColorClip(color="#4a6741")
background.set_duration(150)

title = TextClip(
    text="Color Graded",
    font="Arial",
    size=64.0,
    color="#F0E6D3",
)
title.set_duration(150).set_position(960, 540)

comp.add(background)
comp.add(title)

# --- Color pipeline configuration ---

# Load a .cube LUT file (e.g., a cinematic look)
# lut = load_cube_lut("luts/cinematic_warm.cube")

# Define a color grade: warm shadows, cool highlights
grade = ColorGrade(
    lift=(0.02, -0.01, -0.03),  # warm shadows (add red, reduce blue)
    gamma=(1.0, 1.0, 0.95),  # slightly reduce blue in midtones
    gain=(1.05, 1.0, 0.9),  # warm highlights
    saturation=1.15,  # slightly boost saturation
)

# In a custom render loop, apply the full pipeline to each frame:
#
#   frame = comp._render_frame(i)
#
#   # Option A: apply individual steps
#   frame = apply_color_grade(frame, grade)
#   frame = tone_map_aces(frame)
#
#   # Option B: apply the full pipeline in one call
#   frame = apply_color_pipeline(frame, grade=grade, tone_map="aces")
#
#   # With a LUT:
#   # frame = apply_color_pipeline(frame, lut=lut, grade=grade, tone_map="aces")

comp.render("color_grading.mp4", preset="h264_1080p")
