"""Data journalism showcase — 1920x1080, 180 seconds at 30fps (5400 frames).

Demonstrates: BarChartClip, LineChartClip, PieChartClip with animated data,
NumberCounter for key statistics, ProgressBar for metrics, Typewriter
narration text, TransitionTitle section headers, grid layout for dashboard
views, professional LowerThird overlays, and clean/minimal design theme.

All visuals are self-contained — no external asset files required.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from pymotion import (
    AdjustmentLayer,
    BarChartClip,
    Composition,
    GradientClip,
    LineChartClip,
    LowerThird,
    NumberCounter,
    PieChartClip,
    ProgressBar,
    ShapeClip,
    TextClip,
    Track,
    TransitionTitle,
    Typewriter,
    Vignette,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_FRAMES = 5400  # 180 seconds

# Clean design palette
BG_WHITE = "#F8FAFC"
BG_LIGHT = "#F1F5F9"
ACCENT_BLUE = "#2563EB"
ACCENT_INDIGO = "#4F46E5"
ACCENT_TEAL = "#0D9488"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"
CARD_BG = "#FFFFFF"
BORDER_LIGHT = "#E2E8F0"


def _build_composition() -> Composition:
    """Assemble the data journalism composition."""
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=TOTAL_FRAMES,
        background=BG_WHITE,
    )

    # ── Section timing (30fps) ────────────────────────────────────────
    # Intro: 0-450 (15s)
    # Section 1 — Bar chart: 450-1350 (30s)
    # Section 2 — Line chart: 1350-2250 (30s)
    # Section 3 — Pie chart: 2250-3150 (30s)
    # Section 4 — Dashboard grid: 3150-4500 (45s)
    # Conclusion: 4500-5400 (30s)

    # ── Track 1: Subtle background panels ─────────────────────────────
    bg_track = Track(name="backgrounds")

    # Light gradient backdrop for intro
    intro_bg = GradientClip(
        color_start="#EFF6FF",
        color_end="#F8FAFC",
        direction=180.0,
    )
    intro_bg.set_duration(450).at(0)
    bg_track.add(intro_bg)

    # Alternating section backgrounds
    for c_start, c_end, start, dur in [
        (BG_WHITE, BG_LIGHT, 450, 900),
        (BG_LIGHT, BG_WHITE, 1350, 900),
        (BG_WHITE, BG_LIGHT, 2250, 900),
        ("#EFF6FF", BG_WHITE, 3150, 1350),
        (BG_LIGHT, "#EFF6FF", 4500, 900),
    ]:
        bg = GradientClip(color_start=c_start, color_end=c_end, direction=90.0)
        bg.set_duration(dur).at(start)
        bg_track.add(bg)

    comp.add_track(bg_track)

    # ── Track 2: Section dividers and structure ───────────────────────
    struct_track = Track(name="structure")

    # Top header bar
    header_bar = ShapeClip.rect(
        x=0,
        y=0,
        w=WIDTH,
        h=80,
        fill=ACCENT_BLUE,
    )
    header_bar.set_duration(TOTAL_FRAMES).at(0)
    struct_track.add(header_bar)

    # Header title
    header_title = TextClip(
        text="DATA INSIGHTS 2026",
        font_size=28.0,
        color="#FFFFFF",
    )
    header_title.set_duration(TOTAL_FRAMES).at(0).set_position(60.0, 25.0)
    struct_track.add(header_title)

    # Bottom rule line
    bottom_rule = ShapeClip.rect(
        x=60,
        y=HEIGHT - 40,
        w=WIDTH - 120,
        h=2,
        fill=BORDER_LIGHT,
    )
    bottom_rule.set_duration(TOTAL_FRAMES).at(0).set_opacity(0.6)
    struct_track.add(bottom_rule)

    comp.add_track(struct_track)

    # ── Track 3: Section titles ───────────────────────────────────────
    title_track = Track(name="titles")

    # Intro title
    intro_title = TransitionTitle(
        text="The State of Open Source in 2026",
        style="fade",
        title_duration=120,
        animate_in=30,
        animate_out=30,
        font_size=56.0,
    )
    intro_title.set_duration(120).at(60)
    title_track.add(intro_title)

    # Section titles
    for title_text, style, start in [
        ("Adoption by Language", "slide_up", 480),
        ("Growth Over Time", "fade", 1380),
        ("Market Share", "slide_up", 2280),
        ("Executive Dashboard", "zoom", 3180),
        ("Key Takeaways", "fade", 4530),
    ]:
        t = TransitionTitle(text=title_text, style=style, title_duration=90, font_size=48.0)
        t.set_duration(90).at(start)
        title_track.add(t)

    comp.add_track(title_track)

    # ── Track 4: Narration text (Typewriter) ──────────────────────────
    narration_track = Track(name="narration")

    narrations = [
        ("Open source adoption has accelerated across all major languages.", 200, 200),
        ("Python continues to lead, followed by JavaScript and Rust.", 600, 240),
        ("Year-over-year growth shows a consistent upward trend since 2020.", 1500, 240),
        ("Cloud-native and AI projects dominate the contribution landscape.", 2400, 240),
        ("The dashboard consolidates all key metrics for stakeholders.", 3300, 240),
        ("Open source will define the next decade of software development.", 4650, 240),
    ]
    pos = Vec2(100.0, 950.0)
    for text, start, dur in narrations:
        narr = Typewriter(
            text=text,
            font_size=24.0,
            color=Color.parse(TEXT_MUTED),
            chars_per_frame=0.6,
            cursor=False,
            position=pos,
        )
        narr.set_duration(dur).at(start)
        narration_track.add(narr)

    comp.add_track(narration_track)

    # ── Track 5: Charts ───────────────────────────────────────────────
    chart_track = Track(name="charts")

    # Bar chart — Language adoption (frames 600-1300)
    bar_data = {
        "Python": 42.0,
        "JS": 35.0,
        "Rust": 28.0,
        "Go": 22.0,
        "Java": 18.0,
        "TS": 31.0,
    }
    bar_chart = BarChartClip(
        data=bar_data,
        animate_duration=60,
        theme="corporate",
        title="Open Source Contributions by Language (thousands)",
        show_values=True,
        bar_gap=0.35,
    )
    bar_chart.set_duration(700).at(600).set_position(160.0, 120.0)
    chart_track.add(bar_chart)

    # Line chart — Growth over time (frames 1500-2200)
    line_data = [8.0, 12.0, 15.0, 22.0, 30.0, 38.0, 42.0, 55.0]
    line_chart = LineChartClip(
        data=line_data,
        labels=["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"],
        animate_duration=90,
        theme="corporate",
        title="Annual Contributions (millions)",
        show_dots=True,
        show_fill=True,
        line_width=3.0,
    )
    line_chart.set_duration(700).at(1500).set_position(160.0, 120.0)
    chart_track.add(line_chart)

    # Pie chart — Market share (frames 2400-3100)
    pie_data = {
        "Cloud Native": 32.0,
        "AI/ML": 28.0,
        "DevTools": 18.0,
        "Web": 14.0,
        "Other": 8.0,
    }
    pie_chart = PieChartClip(
        data=pie_data,
        animate_duration=60,
        theme="corporate",
        title="Contribution Categories",
        show_labels=True,
        inner_radius=0.3,
    )
    pie_chart.set_duration(700).at(2400).set_position(160.0, 120.0)
    chart_track.add(pie_chart)

    # ── Dashboard section (frames 3300-4450) ──────────────────────────
    # Mini bar chart
    mini_bar = BarChartClip(
        data={"Q1": 12.0, "Q2": 18.0, "Q3": 25.0, "Q4": 32.0},
        animate_duration=45,
        theme="minimal",
        title="Quarterly Growth",
        show_values=True,
    )
    mini_bar.set_duration(900).at(3300).set_position(60.0, 120.0)
    chart_track.add(mini_bar)

    # Mini pie chart
    mini_pie = PieChartClip(
        data={"Active": 72.0, "Inactive": 28.0},
        animate_duration=45,
        theme="minimal",
        title="Repository Status",
        inner_radius=0.4,
    )
    mini_pie.set_duration(900).at(3300).set_position(980.0, 120.0)
    chart_track.add(mini_pie)

    comp.add_track(chart_track)

    # ── Track 6: Number counters ──────────────────────────────────────
    counter_track = Track(name="counters")

    # Key stats for dashboard
    counters = [
        (0.0, 2.4, "$", "M raised", Vec2(120.0, 650.0), 3450, 180),
        (0.0, 185.0, "", "K contributors", Vec2(520.0, 650.0), 3510, 180),
        (0.0, 12.0, "", "M downloads", Vec2(920.0, 650.0), 3570, 180),
        (0.0, 99.8, "", "% uptime", Vec2(1320.0, 650.0), 3630, 180),
    ]
    for start_v, end_v, prefix, suffix, pos, start, dur in counters:
        nc = NumberCounter(
            start_value=start_v,
            end_value=end_v,
            count_duration=120,
            format_fn=lambda v: f"{v:.1f}" if v != int(v) else str(int(v)),
            size=48.0,
            color=Color.parse(ACCENT_BLUE),
        )
        nc.set_duration(dur).at(start).set_position(pos.x, pos.y)
        counter_track.add(nc)

        # Label below counter
        label = TextClip(
            text=f"{prefix}{suffix}",
            font_size=18.0,
            color=TEXT_MUTED,
        )
        label.set_duration(dur).at(start).set_position(pos.x, pos.y + 70)
        counter_track.add(label)

    comp.add_track(counter_track)

    # ── Track 7: Progress bars ────────────────────────────────────────
    progress_track = Track(name="progress_bars")

    metrics = [
        ("Code Quality", 0.94, ACCENT_BLUE, Vec2(120.0, 820.0), 3700),
        ("Test Coverage", 0.89, ACCENT_TEAL, Vec2(120.0, 870.0), 3760),
        ("Documentation", 0.78, ACCENT_INDIGO, Vec2(120.0, 920.0), 3820),
    ]
    for metric_name, target, color, pos, start in metrics:
        # Label
        metric_label = TextClip(
            text=f"{metric_name}: {int(target * 100)}%",
            font_size=20.0,
            color=TEXT_DARK,
        )
        metric_label.set_duration(500).at(start).set_position(pos.x, pos.y - 25)
        progress_track.add(metric_label)

        # Animated progress bar
        animate_dur = 90
        bar = ProgressBar(
            value=lambda f, t=target, d=animate_dur: min(t, t * (f / d)) if f < d else t,
            bar_width=700.0,
            bar_height=16.0,
            fill_color=Color.parse(color),
            bg_color=Color.parse(BORDER_LIGHT),
            radius=8.0,
        )
        bar.set_duration(500).at(start).set_position(pos.x, pos.y)
        progress_track.add(bar)

    comp.add_track(progress_track)

    # ── Track 8: Lower thirds ─────────────────────────────────────────
    lt_track = Track(name="lower_thirds")

    lower_thirds = [
        ("Data Source", "Open Source Index 2026", "clean", 300),
        ("Methodology", "Aggregated from 50K+ repos", "clean", 900),
        ("Analyst", "PyMotion Data Team", "corporate", 1800),
        ("Summary", "Q4 2026 Report", "corporate", 4200),
    ]
    for name, title, style, start in lower_thirds:
        lt = LowerThird(name=name, title=title, style=style)
        lt.set_duration(180).at(start)
        lt_track.add(lt)

    comp.add_track(lt_track)

    # ── Track 9: Conclusion text ──────────────────────────────────────
    conclusion_track = Track(name="conclusion")

    conclusion_points = [
        ("Open source adoption grew 40% year-over-year", 400.0, 4700),
        ("Python and AI/ML lead all contribution categories", 480.0, 4820),
        ("Enterprise participation at an all-time high", 560.0, 4940),
    ]
    for point_text, y_pos, start in conclusion_points:
        pos = Vec2(200.0, y_pos)
        point = Typewriter(
            text=point_text,
            font_size=32.0,
            color=Color.parse(TEXT_DARK),
            chars_per_frame=0.8,
            cursor=False,
            position=pos,
        )
        point.set_duration(300).at(start)
        conclusion_track.add(point)

    comp.add_track(conclusion_track)

    # ── Track 10: Subtle vignette ─────────────────────────────────────
    fx_track = Track(name="effects")

    vignette = AdjustmentLayer()
    vignette.add_effect(Vignette(strength=0.2, radius=0.9, feather=0.3))
    vignette.set_duration(TOTAL_FRAMES).at(0)
    fx_track.add(vignette)

    comp.add_track(fx_track)

    return comp


def main() -> None:
    """Build and render the data story video."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "03_data_story.mp4"

    logger.info("building_composition", width=WIDTH, height=HEIGHT, fps=FPS)
    comp = _build_composition()

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
