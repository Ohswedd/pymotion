"""Educational Explainer — Step-by-step learning video.

Niche: Online educators creating course intro / explainer videos.
Demonstrates: Clean layout design with ShapeClip (rect, circle, line, polygon),
              Typewriter + WordByWord animated text, CountUp for statistics,
              ImageClip (cover mode), ColorClip, GradientClip, multi-track
              composition, LetterByLetter animated CTA.

Duration: ~18 seconds at 30 fps (540 frames).
"""

from pathlib import Path

from pymotion import (
    Composition,
    GradientClip,
    ShapeClip,
    TextClip,
    Track,
)
from pymotion.clip.color import ColorClip
from pymotion.clip.image import ImageClip
from pymotion.text.animated import CountUp, LetterByLetter, Typewriter, WordByWord
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

assets = Path(__file__).parent / "assets"
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

FPS = 30
DURATION = FPS * 18  # 540 frames

# ═══════════════════════════════════════════════════════════════
# COMPOSITION — Clean, professional educational style
# ═══════════════════════════════════════════════════════════════
comp = Composition(
    width=1920,
    height=1080,
    fps=FPS,
    duration=DURATION,
    background="#F5F5F0",
)

# ═══════════════════════════════════════════════════════════════
# LAYER 1: BACKGROUND — Clean light gradient
# ═══════════════════════════════════════════════════════════════
bg = Track(name="background")

bg_light = GradientClip(
    color_start="#FAFAF5",
    color_end="#EEEEE8",
    direction=180.0,
)
bg_light.set_duration(DURATION)
bg.add(bg_light)

# ═══════════════════════════════════════════════════════════════
# LAYER 2: SIDEBAR — Persistent left panel with course nav
# ═══════════════════════════════════════════════════════════════
sidebar = Track(name="sidebar")

sidebar_bg = ShapeClip.rect(x=0, y=0, w=360, h=1080, fill="#2D3436")
sidebar_bg.set_duration(DURATION)
sidebar.add(sidebar_bg)

accent_stripe = ShapeClip.rect(x=356, y=0, w=4, h=1080, fill="#0984E3")
accent_stripe.set_duration(DURATION)
sidebar.add(accent_stripe)

icon_circle = ShapeClip.circle(cx=180, cy=120, r=40, fill="#0984E3")
icon_circle.set_duration(DURATION)
sidebar.add(icon_circle)

icon_inner = ShapeClip.circle(cx=180, cy=120, r=25, fill="#2D3436")
icon_inner.set_duration(DURATION)
sidebar.add(icon_inner)

icon_dot = ShapeClip.circle(cx=180, cy=120, r=8, fill="#0984E3")
icon_dot.set_duration(DURATION)
sidebar.add(icon_dot)

sidebar_title = TextClip(
    "PYTHON",
    font="Arial",
    size=28.0,
    color="#FFFFFF",
    letter_spacing=4.0,
)
sidebar_title.set_duration(DURATION).set_position(110.0, 200.0)
sidebar.add(sidebar_title)

sidebar_subtitle = TextClip(
    "MASTERCLASS",
    font="Arial",
    size=18.0,
    color="#0984E3",
    letter_spacing=6.0,
)
sidebar_subtitle.set_duration(DURATION).set_position(95.0, 240.0)
sidebar.add(sidebar_subtitle)

steps = [
    ("01", "Introduction", True),
    ("02", "Variables", True),
    ("03", "Functions", True),
    ("04", "Classes", False),
    ("05", "Projects", False),
]
for i, (num, label, completed) in enumerate(steps):
    y_pos = 340 + i * 80

    step_color = "#0984E3" if completed else "#555555"
    step_circle = ShapeClip.circle(cx=80, cy=y_pos + 15, r=16, fill=step_color)
    step_circle.set_duration(DURATION)
    sidebar.add(step_circle)

    step_num = TextClip(num, font="Arial", size=14.0, color="#FFFFFF")
    step_num.set_duration(DURATION).set_position(70.0, float(y_pos + 5))
    sidebar.add(step_num)

    label_color = "#FFFFFF" if completed else "#888888"
    step_label = TextClip(label, font="Arial", size=18.0, color=label_color)
    step_label.set_duration(DURATION).set_position(115.0, float(y_pos + 5))
    sidebar.add(step_label)

    if i < len(steps) - 1:
        conn_line = ShapeClip.line(
            x1=80, y1=y_pos + 31, x2=80, y2=y_pos + 64,
            color="#444444", width=1,
        )
        conn_line.set_duration(DURATION)
        sidebar.add(conn_line)

# ═══════════════════════════════════════════════════════════════
# LAYER 3: SECTION 1 (0–180) — Course Introduction with code
# ═══════════════════════════════════════════════════════════════
sec1 = Track(name="section1")

sec1_header_bg = ShapeClip.rect(x=360, y=0, w=1560, h=120, fill="#FFFFFF")
sec1_header_bg.set_duration(180).set_opacity(0.95)
sec1.add(sec1_header_bg)

sec1_header_line = ShapeClip.rect(x=360, y=118, w=1560, h=2, fill="#E0E0D8")
sec1_header_line.set_duration(180)
sec1.add(sec1_header_line)

# Module title — Typewriter (19 chars at 2/frame = done ~frame 10, holds rest)
module_title = Typewriter(
    text="Module 3: Functions",
    font_size=36.0,
    color=Color(0.18, 0.2, 0.21, 1.0),
    chars_per_frame=2.0,
    cursor=False,
    position=Vec2(420.0, 35.0),
)
module_title.set_duration(180)
sec1.add(module_title)

objectives_header = TextClip(
    "LEARNING OBJECTIVES",
    font="Arial",
    size=16.0,
    color="#0984E3",
    letter_spacing=4.0,
)
objectives_header.set_duration(160).at(20).set_position(420.0, 170.0)
sec1.add(objectives_header)

# Objectives — WordByWord, each extends to fill section
objectives = [
    "Understand function definitions and parameters",
    "Master return values and type hints",
    "Learn decorators and closures",
    "Build reusable code modules",
]
for i, obj_text in enumerate(objectives):
    y = 220 + i * 55
    obj_start = 30 + i * 20

    checkbox = ShapeClip.rect(
        x=420, y=y, w=22, h=22,
        fill="#FFFFFF",
        stroke="#0984E3",
        stroke_width=2,
    )
    checkbox.set_duration(180 - obj_start).at(obj_start)
    sec1.add(checkbox)

    # Checkmarks appear after a short delay
    check = ShapeClip.line(
        x1=425, y1=y + 11, x2=431, y2=y + 17,
        color="#0984E3", width=2,
    )
    check.set_duration(180 - obj_start - 15).at(obj_start + 15)
    sec1.add(check)

    check2 = ShapeClip.line(
        x1=431, y1=y + 17, x2=440, y2=y + 5,
        color="#0984E3", width=2,
    )
    check2.set_duration(180 - obj_start - 15).at(obj_start + 15)
    sec1.add(check2)

    # WordByWord — extends to fill section (animation finishes, text holds)
    obj_anim = WordByWord(
        text=obj_text,
        font_size=20.0,
        color=Color(0.3, 0.3, 0.3, 1.0),
        frames_per_word=5,
        position=Vec2(460.0, float(y + 2)),
    )
    obj_anim.set_duration(180 - obj_start).at(obj_start)
    sec1.add(obj_anim)

# Code preview panel
code_panel = ShapeClip.rect(x=1100, y=160, w=700, h=500, fill="#2D3436")
code_panel.set_duration(160).at(20)
sec1.add(code_panel)

code_lines = [
    ("def greet(name: str) -> str:", "#66D9EF"),
    ('    """Return a greeting."""', "#75715E"),
    ('    return f"Hello, {name}!"', "#A6E22E"),
    ("", "#FFFFFF"),
    ("result = greet('World')", "#F8F8F2"),
    ("print(result)", "#F8F8F2"),
]
for j, (code, color) in enumerate(code_lines):
    if code:
        code_text = TextClip(code, font="Arial", size=18.0, color=color)
        code_text.set_duration(150 - j * 10).at(30 + j * 10).set_position(
            1130.0, 195.0 + j * 35
        )
        sec1.add(code_text)

for j in range(6):
    line_num = TextClip(str(j + 1), font="Arial", size=14.0, color="#555555")
    line_num.set_duration(150).at(30).set_position(1110.0, 198.0 + j * 35)
    sec1.add(line_num)

# ═══════════════════════════════════════════════════════════════
# LAYER 4: SECTION 2 (180–360) — Concept Diagram
# ═══════════════════════════════════════════════════════════════
sec2 = Track(name="section2")

sec2_header_bg = ShapeClip.rect(x=360, y=0, w=1560, h=120, fill="#FFFFFF")
sec2_header_bg.set_duration(180).at(180).set_opacity(0.95)
sec2.add(sec2_header_bg)

sec2_header_line = ShapeClip.rect(x=360, y=118, w=1560, h=2, fill="#E0E0D8")
sec2_header_line.set_duration(180).at(180)
sec2.add(sec2_header_line)

sec2_title = TextClip(
    "How Functions Work",
    font="Arial",
    size=36.0,
    color="#2D3436",
)
sec2_title.set_duration(180).at(180).set_position(420.0, 40.0)
sec2.add(sec2_title)

# Diagram elements — all visible for the full section
input_box = ShapeClip.rect(
    x=480, y=300, w=200, h=120,
    fill="#DFE6E9",
    stroke="#0984E3",
    stroke_width=2,
)
input_box.set_duration(180).at(180)
sec2.add(input_box)

input_label = TextClip("Input", font="Arial", size=20.0, color="#2D3436")
input_label.set_duration(180).at(180).set_position(545.0, 330.0)
sec2.add(input_label)

input_example = TextClip('"Alice"', font="Arial", size=16.0, color="#0984E3")
input_example.set_duration(180).at(180).set_position(540.0, 370.0)
sec2.add(input_example)

arrow1 = ShapeClip.line(x1=680, y1=360, x2=800, y2=360, color="#0984E3", width=3)
arrow1.set_duration(180).at(180)
sec2.add(arrow1)

arrow1_head = ShapeClip.polygon(
    points=[(800, 350), (820, 360), (800, 370)],
    fill="#0984E3",
)
arrow1_head.set_duration(180).at(180)
sec2.add(arrow1_head)

func_box = ShapeClip.rect(x=820, y=270, w=280, h=180, fill="#0984E3")
func_box.set_duration(180).at(180)
sec2.add(func_box)

func_label = TextClip("greet()", font="Arial", size=24.0, color="#FFFFFF")
func_label.set_duration(180).at(180).set_position(895.0, 330.0)
sec2.add(func_label)

func_icon = TextClip("f(x)", font="Arial", size=18.0, color="#74B9FF")
func_icon.set_duration(180).at(180).set_position(930.0, 290.0)
sec2.add(func_icon)

arrow2 = ShapeClip.line(x1=1100, y1=360, x2=1220, y2=360, color="#0984E3", width=3)
arrow2.set_duration(180).at(180)
sec2.add(arrow2)

arrow2_head = ShapeClip.polygon(
    points=[(1220, 350), (1240, 360), (1220, 370)],
    fill="#0984E3",
)
arrow2_head.set_duration(180).at(180)
sec2.add(arrow2_head)

output_box = ShapeClip.rect(
    x=1240, y=300, w=200, h=120,
    fill="#DFE6E9",
    stroke="#00B894",
    stroke_width=2,
)
output_box.set_duration(180).at(180)
sec2.add(output_box)

output_label = TextClip("Output", font="Arial", size=20.0, color="#2D3436")
output_label.set_duration(180).at(180).set_position(1295.0, 330.0)
sec2.add(output_label)

output_example = TextClip('"Hello, Alice!"', font="Arial", size=16.0, color="#00B894")
output_example.set_duration(180).at(180).set_position(1265.0, 370.0)
sec2.add(output_example)

# Explanation — Typewriter (62 chars at 1.5/frame = done ~frame 41, holds rest)
explanation = Typewriter(
    text="A function takes inputs, processes them, and returns an output.",
    font_size=22.0,
    color=Color(0.3, 0.3, 0.3, 1.0),
    chars_per_frame=1.5,
    cursor=False,
    position=Vec2(500.0, 530.0),
)
explanation.set_duration(160).at(200)
sec2.add(explanation)

# Concept cards — all visible for the section
concepts = [
    ("Parameters", "Values passed in"),
    ("Return", "Value sent back"),
    ("Scope", "Variable visibility"),
]
for i, (concept, desc) in enumerate(concepts):
    cx = 500 + i * 350

    card = ShapeClip.rect(x=cx, y=620, w=300, h=100, fill="#FFFFFF")
    card.set_duration(150).at(210)
    sec2.add(card)

    card_border = ShapeClip.rect(x=cx, y=620, w=300, h=4, fill="#0984E3")
    card_border.set_duration(150).at(210)
    sec2.add(card_border)

    card_title = TextClip(concept, font="Arial", size=20.0, color="#2D3436")
    card_title.set_duration(150).at(210).set_position(float(cx + 20), 640.0)
    sec2.add(card_title)

    card_desc = TextClip(desc, font="Arial", size=14.0, color="#636E72")
    card_desc.set_duration(150).at(210).set_position(float(cx + 20), 675.0)
    sec2.add(card_desc)

# ═══════════════════════════════════════════════════════════════
# LAYER 5: SECTION 3 (360–540) — Summary + Stats + CTA
# ═══════════════════════════════════════════════════════════════
sec3 = Track(name="section3")

sec3_bg = ColorClip("#F5F5F0")
sec3_bg.set_duration(180).at(360)
sec3.add(sec3_bg)

books_bg = ImageClip(source=assets / "edu_books.jpg", fit_mode="cover")
books_bg.set_duration(180).at(360).set_opacity(0.08)
sec3.add(books_bg)

stats_header = TextClip(
    "COURSE IMPACT",
    font="Arial",
    size=28.0,
    color="#2D3436",
    letter_spacing=4.0,
)
stats_header.set_duration(180).at(360).set_position(850.0, 180.0)
sec3.add(stats_header)

stats_line = ShapeClip.rect(x=850, y=225, w=220, h=3, fill="#0984E3")
stats_line.set_duration(180).at(360)
sec3.add(stats_line)

# Stats — CountUp over full section duration (counts smoothly, no handoff)
stat_data = [
    (50000, "Students Enrolled", "+", 0),
    (4.9, "Average Rating", "", 1),
    (95, "Completion Rate", "%", 0),
]
for i, (value, label, suffix, decimals) in enumerate(stat_data):
    x_pos = 500 + i * 350

    count = CountUp(
        start_value=0,
        end_value=value,
        font_size=52.0,
        color=Color(0.04, 0.52, 0.89, 1.0),
        suffix=suffix,
        decimals=decimals,
        position=Vec2(float(x_pos), 290.0),
    )
    count.set_duration(180).at(360)
    sec3.add(count)

    stat_label = TextClip(label, font="Arial", size=18.0, color="#636E72")
    stat_label.set_duration(180).at(360).set_position(float(x_pos), 370.0)
    sec3.add(stat_label)

# CTA bar
cta_bar = ShapeClip.rect(x=360, y=470, w=1560, h=200, fill="#0984E3")
cta_bar.set_duration(160).at(380)
sec3.add(cta_bar)

# CTA text — LetterByLetter (20 chars at 2/frame = done ~frame 10, holds rest)
cta_text = LetterByLetter(
    text="Start Learning Today",
    font_size=44.0,
    color=Color(1.0, 1.0, 1.0, 1.0),
    frames_per_letter=2,
    position=Vec2(700.0, 515.0),
)
cta_text.set_duration(160).at(380)
sec3.add(cta_text)

cta_url = TextClip(
    "www.pythonmasterclass.io",
    font="Arial",
    size=22.0,
    color="#74B9FF",
)
cta_url.set_duration(150).at(390).set_position(780.0, 590.0)
sec3.add(cta_url)

info_bar = ShapeClip.rect(x=360, y=850, w=1560, h=80, fill="#2D3436")
info_bar.set_duration(150).at(390)
sec3.add(info_bar)

info_text = TextClip(
    "12 Modules  |  48 Lessons  |  Certificate Included  |  Lifetime Access",
    font="Arial",
    size=16.0,
    color="#B2BEC3",
)
info_text.set_duration(150).at(390).set_position(580.0, 880.0)
sec3.add(info_text)

# ═══════════════════════════════════════════════════════════════
# ASSEMBLE
# ═══════════════════════════════════════════════════════════════
comp.add_track(bg)
comp.add_track(sidebar)
comp.add_track(sec1)
comp.add_track(sec2)
comp.add_track(sec3)

# ═══════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════
output_path = output_dir / "05_educational_explainer.mp4"
comp.render(str(output_path), preset="h264_1080p")

comp.export_frame(100, str(output_dir / "05_edu_thumbnail_code.png"))
comp.export_frame(280, str(output_dir / "05_edu_thumbnail_diagram.png"))
comp.export_frame(460, str(output_dir / "05_edu_thumbnail_stats.png"))
print(f"Rendered: {output_path}")
