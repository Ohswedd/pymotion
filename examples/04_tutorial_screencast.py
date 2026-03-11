"""Tutorial screencast — 1920x1080, 120 seconds at 30fps (3600 frames).

Demonstrates: BrowserMockup framing, step-by-step indicators, code-like text
panels, animated cursor using expressions and ShapeClip, highlight boxes with
semi-transparent ShapeClip overlays, Typewriter for instructions, ProgressBar
as a step indicator, DesktopMockup, and expression-driven animation.

All visuals are self-contained — no external asset files required.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from pymotion import (
    AdjustmentLayer,
    BrowserMockup,
    ColorClip,
    Composition,
    DesktopMockup,
    GradientClip,
    ProgressBar,
    ShapeClip,
    TextClip,
    Track,
    TransitionTitle,
    Typewriter,
    Vignette,
    wiggle,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_FRAMES = 3600  # 120 seconds

# Tutorial color palette
BG_SLATE = "#0F172A"
BG_EDITOR = "#1E293B"
ACCENT_BLUE = "#3B82F6"
ACCENT_GREEN = "#22C55E"
ACCENT_ORANGE = "#F97316"
ACCENT_PURPLE = "#A855F7"
TEXT_WHITE = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
TEXT_CODE = "#E2E8F0"
HIGHLIGHT_BG = "#3B82F630"
CODE_BG = "#0F172A"

# Step timings (each step is ~24 seconds = 720 frames)
STEPS = [
    (0, 720, "1/5", "Install PyMotion"),
    (720, 1440, "2/5", "Create a Composition"),
    (1440, 2160, "3/5", "Add Clips and Effects"),
    (2160, 2880, "4/5", "Configure Rendering"),
    (2880, 3600, "5/5", "Export Your Video"),
]


def _build_composition() -> Composition:
    """Assemble the tutorial screencast composition."""
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=TOTAL_FRAMES,
        background=BG_SLATE,
    )

    # ── Track 1: Background gradient ──────────────────────────────────
    bg_track = Track(name="backgrounds")

    bg_grad = GradientClip(
        color_start="#0F172A",
        color_end="#1E293B",
        direction=135.0,
    )
    bg_grad.set_duration(TOTAL_FRAMES).at(0)
    bg_track.add(bg_grad)

    comp.add_track(bg_track)

    # ── Track 2: Step progress indicator at bottom ────────────────────
    progress_track = Track(name="progress")

    # Bottom progress bar showing overall tutorial progress
    progress = ProgressBar(
        value=lambda frame: min(1.0, frame / TOTAL_FRAMES),
        bar_width=WIDTH - 160.0,
        bar_height=6.0,
        fill_color=Color.parse(ACCENT_BLUE),
        bg_color=Color(1.0, 1.0, 1.0, 0.1),
        radius=3.0,
    )
    progress.set_duration(TOTAL_FRAMES).at(0).set_position(80.0, HEIGHT - 30.0)
    progress_track.add(progress)

    comp.add_track(progress_track)

    # ── Track 3: Step indicators and headers ──────────────────────────
    step_track = Track(name="step_indicators")

    for start, end, step_num, step_title in STEPS:
        dur = end - start

        # Step badge — top-left corner
        badge_bg = ShapeClip.rect(
            x=40,
            y=100,
            w=120,
            h=44,
            fill=ACCENT_BLUE,
        )
        badge_bg.set_duration(dur).at(start)
        step_track.add(badge_bg)

        badge_text = TextClip(
            text=step_num,
            font_size=22.0,
            color=TEXT_WHITE,
        )
        badge_text.set_duration(dur).at(start).set_position(60.0, 108.0)
        step_track.add(badge_text)

        # Step title next to badge
        title = TextClip(
            text=step_title,
            font_size=28.0,
            color=TEXT_WHITE,
        )
        title.set_duration(dur).at(start).set_position(180.0, 108.0)
        step_track.add(title)

        # Section intro transition
        intro = TransitionTitle(
            text=f"Step {step_num}: {step_title}",
            style="slide_up",
            title_duration=60,
            animate_in=15,
            animate_out=15,
            font_size=44.0,
        )
        intro.set_duration(60).at(start + 10)
        step_track.add(intro)

    comp.add_track(step_track)

    # ── Track 4: Browser mockup (Step 1 — installation docs) ─────────
    mockup_track = Track(name="mockups")

    # Step 1: Browser showing documentation
    doc_content = ColorClip(color="#1A1A2E")
    doc_content.set_duration(600).at(100)

    browser = BrowserMockup(
        content_clip=doc_content,
        mockup_theme="dark",
        url_text="https://pymotion.dev/docs/getting-started",
        animate_in_frames=20,
        animate_out_frames=20,
    )
    browser.set_duration(600).at(100)
    mockup_track.add(browser)

    # Step 4: Desktop mockup showing render settings
    render_content = ColorClip(color="#0F172A")
    render_content.set_duration(600).at(2260)

    desktop = DesktopMockup(
        content_clip=render_content,
        os_theme="macos",
        window_title="PyMotion Renderer",
        animate_in_frames=20,
        animate_out_frames=20,
    )
    desktop.set_duration(600).at(2260)
    mockup_track.add(desktop)

    comp.add_track(mockup_track)

    # ── Track 5: Code panels ──────────────────────────────────────────
    code_track = Track(name="code_panels")

    # Code block backgrounds — dark panels
    code_blocks = [
        # Step 1: pip install
        (
            200,
            400,
            300.0,
            200.0,
            1200.0,
            300.0,
            [
                ("$ pip install pymotion", Vec2(330.0, 250.0), 28.0, ACCENT_GREEN),
                ("Collecting pymotion...", Vec2(330.0, 300.0), 20.0, TEXT_MUTED),
                ("Successfully installed pymotion-3.0.0", Vec2(330.0, 340.0), 20.0, ACCENT_GREEN),
            ],
        ),
        # Step 2: Create composition
        (
            820,
            500,
            300.0,
            200.0,
            1300.0,
            420.0,
            [
                (
                    "from pymotion import Composition, Track",
                    Vec2(330.0, 240.0),
                    22.0,
                    ACCENT_PURPLE,
                ),
                ("", Vec2(330.0, 270.0), 22.0, TEXT_CODE),
                ("comp = Composition(", Vec2(330.0, 300.0), 22.0, TEXT_CODE),
                ("    width=1920, height=1080,", Vec2(330.0, 330.0), 22.0, ACCENT_ORANGE),
                ("    fps=30, duration=900,", Vec2(330.0, 360.0), 22.0, ACCENT_ORANGE),
                ("    background='#0A0A1A'", Vec2(330.0, 390.0), 22.0, ACCENT_ORANGE),
                (")", Vec2(330.0, 420.0), 22.0, TEXT_CODE),
            ],
        ),
        # Step 3: Add clips
        (
            1540,
            500,
            300.0,
            200.0,
            1300.0,
            480.0,
            [
                (
                    "from pymotion import TextClip, ColorClip",
                    Vec2(330.0, 240.0),
                    22.0,
                    ACCENT_PURPLE,
                ),
                ("", Vec2(330.0, 270.0), 22.0, TEXT_CODE),
                ("title = TextClip(", Vec2(330.0, 300.0), 22.0, TEXT_CODE),
                ("    text='Hello World',", Vec2(330.0, 330.0), 22.0, ACCENT_ORANGE),
                ("    font_size=64,", Vec2(330.0, 360.0), 22.0, ACCENT_ORANGE),
                ("    color='#FFFFFF'", Vec2(330.0, 390.0), 22.0, ACCENT_ORANGE),
                (")", Vec2(330.0, 420.0), 22.0, TEXT_CODE),
                ("title.set_duration(90).at(0)", Vec2(330.0, 460.0), 22.0, ACCENT_BLUE),
            ],
        ),
        # Step 5: Export
        (
            2980,
            400,
            300.0,
            200.0,
            1300.0,
            300.0,
            [
                ("comp.render(", Vec2(330.0, 250.0), 24.0, TEXT_CODE),
                ("    'output/video.mp4',", Vec2(330.0, 290.0), 24.0, ACCENT_ORANGE),
                ("    preset='h264_1080p'", Vec2(330.0, 330.0), 24.0, ACCENT_ORANGE),
                (")", Vec2(330.0, 370.0), 24.0, TEXT_CODE),
            ],
        ),
    ]

    for block_start, block_dur, panel_x, panel_y, panel_w, panel_h, lines in code_blocks:
        # Dark code background panel
        panel = ShapeClip.rect(
            x=int(panel_x),
            y=int(panel_y),
            w=int(panel_w),
            h=int(panel_h),
            fill=CODE_BG,
            stroke="#334155",
            stroke_width=2.0,
        )
        panel.set_duration(block_dur).at(block_start)
        code_track.add(panel)

        # Code text lines — revealed with Typewriter
        for line_idx, (line_text, pos, size, color) in enumerate(lines):
            if not line_text:
                continue
            code_line = Typewriter(
                text=line_text,
                font_size=size,
                color=Color.parse(color),
                chars_per_frame=1.2,
                cursor=line_idx == len(lines) - 1,
                position=pos,
            )
            line_start = block_start + 30 + line_idx * 20
            code_line.set_duration(block_dur - 30 - line_idx * 20).at(line_start)
            code_track.add(code_line)

    comp.add_track(code_track)

    # ── Track 6: Highlight boxes ──────────────────────────────────────
    highlight_track = Track(name="highlights")

    highlights = [
        (280, 150, 310, 235, 700, 50),
        (920, 150, 310, 315, 500, 100),
        (1640, 150, 310, 285, 500, 160),
        (3080, 150, 310, 235, 500, 140),
    ]
    for h_start, h_dur, hx, hy, hw, hh in highlights:
        highlight = ShapeClip.rect(
            x=hx,
            y=hy,
            w=hw,
            h=hh,
            fill="#3B82F618",
            stroke=ACCENT_BLUE,
            stroke_width=2.0,
        )
        highlight.set_duration(h_dur).at(h_start).set_opacity(0.7)
        highlight_track.add(highlight)

    comp.add_track(highlight_track)

    # ── Track 7: Animated cursor pointer ──────────────────────────────
    cursor_track = Track(name="cursor")

    # Cursor positions per step — moves between key areas
    cursor_waypoints = [
        (100, 350, 500.0, 400.0),
        (350, 200, 800.0, 350.0),
        (820, 300, 600.0, 380.0),
        (1200, 200, 450.0, 500.0),
        (1540, 300, 600.0, 400.0),
        (1900, 200, 550.0, 470.0),
        (2260, 300, 960.0, 540.0),
        (2600, 200, 700.0, 400.0),
        (2980, 300, 600.0, 350.0),
        (3300, 300, 500.0, 280.0),
    ]

    for wp_start, wp_dur, target_x, target_y in cursor_waypoints:
        # Cursor dot
        cursor_dot = ShapeClip.circle(
            cx=0,
            cy=0,
            r=8,
            fill=TEXT_WHITE,
        )
        cursor_dot.set_duration(wp_dur).at(wp_start).set_opacity(0.9)
        cursor_dot.set_position(target_x, target_y)

        # Subtle wiggle for natural movement
        cursor_dot.set_expression("position.x", wiggle(freq=2.0, amp=15.0))
        cursor_dot.set_expression("position.y", wiggle(freq=1.5, amp=10.0))
        cursor_track.add(cursor_dot)

        # Cursor ring — pulse effect
        cursor_ring = ShapeClip.circle(
            cx=0, cy=0, r=16, fill="#3B82F600", stroke=ACCENT_BLUE, stroke_width=2.0
        )
        cursor_ring.set_duration(wp_dur).at(wp_start).set_opacity(0.5)
        cursor_ring.set_position(target_x, target_y)
        cursor_ring.set_expression("position.x", wiggle(freq=2.0, amp=15.0))
        cursor_ring.set_expression("position.y", wiggle(freq=1.5, amp=10.0))
        cursor_track.add(cursor_ring)

    comp.add_track(cursor_track)

    # ── Track 8: Instruction text ─────────────────────────────────────
    instruction_track = Track(name="instructions")

    instructions = [
        ("First, install PyMotion using pip.", 130, 200),
        ("The package includes all dependencies.", 370, 180),
        ("Create a Composition with your target resolution.", 860, 240),
        ("Set fps and duration in frames for precise control.", 1140, 200),
        ("TextClip, ColorClip, and ShapeClip are your building blocks.", 1580, 240),
        ("Chain set_duration() and at() for timeline positioning.", 1860, 200),
        ("Choose an output preset for your target platform.", 2300, 240),
        ("Hardware encoders are auto-detected for faster renders.", 2600, 200),
        ("Call comp.render() to produce your final video file.", 3020, 240),
        ("Your video is ready to share!", 3340, 260),
    ]
    pos = Vec2(300.0, 660.0)
    for inst_text, start, dur in instructions:
        inst = Typewriter(
            text=inst_text,
            font_size=26.0,
            color=Color.parse(TEXT_MUTED),
            chars_per_frame=0.7,
            cursor=False,
            position=pos,
        )
        inst.set_duration(dur).at(start)
        instruction_track.add(inst)

    comp.add_track(instruction_track)

    # ── Track 9: Step completion checkmarks ───────────────────────────
    check_track = Track(name="checkmarks")

    for i, (_start, end, _step_num, _step_title) in enumerate(STEPS):
        if i == len(STEPS) - 1:
            break
        # Green checkmark circle at end of each step
        check_bg = ShapeClip.circle(
            cx=85,
            cy=160,
            r=16,
            fill=ACCENT_GREEN,
        )
        check_bg.set_duration(TOTAL_FRAMES - end).at(end)
        check_track.add(check_bg)

        check_text = TextClip(
            text="OK",
            font_size=14.0,
            color=TEXT_WHITE,
        )
        check_text.set_duration(TOTAL_FRAMES - end).at(end).set_position(73.0, 153.0)
        check_track.add(check_text)

    comp.add_track(check_track)

    # ── Track 10: Global effects ──────────────────────────────────────
    fx_track = Track(name="effects")

    vignette = AdjustmentLayer()
    vignette.add_effect(Vignette(strength=0.3, radius=0.85, feather=0.3))
    vignette.set_duration(TOTAL_FRAMES).at(0)
    fx_track.add(vignette)

    comp.add_track(fx_track)

    return comp


def main() -> None:
    """Build and render the tutorial screencast video."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "04_tutorial_screencast.mp4"

    logger.info("building_composition", width=WIDTH, height=HEIGHT, fps=FPS)
    comp = _build_composition()

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
