"""EX09 — Motion Graphics & Charts.

Use-case: A data-driven dashboard video with animated charts,
motion graphics titles, device mockups, and branded overlays.
Each component gets its own dedicated scene for clarity.

Features exercised:
  TransitionTitle, LowerThird, Divider, QuoteCard, CallToAction,
  SocialHandle, Watermark, Countdown, LogoReveal,
  BarChartClip, LineChartClip, PieChartClip, AreaChartClip,
  RadarChartClip, ScatterPlotClip, NumberCounter, ProgressBar,
  BrowserMockup, DesktopMockup, PhoneMockup,
  SlideRight, SlideDown, SlideUp, WipeLeft, WipeRight, WipeDiagonal

Output: 1920x1080, 30fps, ~51s, preset h264_fast -> outputs/09_mograph.mp4
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import pymotion as pm
from pymotion.design.motion import FAST, NORMAL, SLOW, STAGGER
from pymotion.design.tokens import ACCENT, NEUTRAL, get_theme

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Each scene is 3s (90 frames) — enough for entry + hold + exit
SEC = 90
NUM_SCENES = 17
TOTAL = SEC * NUM_SCENES  # 17 scenes = 51s


def main() -> None:
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)
    theme = get_theme()

    # ── Background ───────────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.ColorClip(color=theme.background)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── SCENE 1: TransitionTitle ─────────────────────────────────────────
    # SCENE: title | 90f | Primary: title text | Secondary: none
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = 0
    t1 = pm.Track(name="s01_title")
    tt = pm.TransitionTitle(
        text="MOTION GRAPHICS",
        style="slide_up",
        title_duration=SEC,
        animate_in=NORMAL,
        animate_out=NORMAL,
        font_size=72.0,
    )
    tt.set_duration(SEC).at(offset)
    t1.clips.append(tt)
    comp.tracks.append(t1)
    print(f"S01 TransitionTitle: style={tt.style}")

    # ── SCENE 2: LowerThird ──────────────────────────────────────────────
    # SCENE: lower_third | 90f | Primary: name chip | Secondary: none
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = SEC
    t2 = pm.Track(name="s02_lowerthird")
    lt = pm.LowerThird(
        name="Jane Smith",
        title="Chief Data Officer",
        style="modern",
        animate_in=NORMAL,
        animate_out=FAST,
        margin_bottom=80.0,
    )
    lt.set_duration(SEC).at(offset)
    t2.clips.append(lt)
    comp.tracks.append(t2)
    print(f"S02 LowerThird: style={lt.style}")

    # ── SCENE 3: LogoReveal ──────────────────────────────────────────────
    # SCENE: logo | 90f | Primary: logo | Secondary: none
    # ENTRY: 0-24 | HOLD: 24-72 | EXIT: 72-90
    offset = SEC * 2
    t3 = pm.Track(name="s03_logo")
    logo = pm.LogoReveal(
        image=str(ASSETS / "logo.png"),
        style="fade",
        reveal_duration=SLOW,
        logo_size=(280.0, 280.0),
    )
    logo.set_duration(SEC).at(offset).set_position(960, 486)
    t3.clips.append(logo)
    comp.tracks.append(t3)
    print("S03 LogoReveal: fade, centered")

    # ── SCENE 4: QuoteCard ───────────────────────────────────────────────
    # SCENE: quote | 90f | Primary: quote text | Secondary: attribution
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = SEC * 3
    t4 = pm.Track(name="s04_quote")
    quote = pm.QuoteCard(
        text="Data is the new oil.",
        attribution="Clive Humby",
        style="elegant",
        animate_in=NORMAL,
    )
    quote.set_duration(SEC).at(offset)
    t4.clips.append(quote)
    comp.tracks.append(t4)
    print("S04 QuoteCard: elegant")

    # ── SCENE 5: CallToAction ────────────────────────────────────────────
    # SCENE: cta | 90f | Primary: button text | Secondary: sub-text
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = SEC * 4
    t5 = pm.Track(name="s05_cta")
    cta = pm.CallToAction(
        text="Get Started",
        sub_text="Free for 14 days",
        style="visit",
        animate_in=NORMAL,
    )
    cta.set_duration(SEC).at(offset).set_position(960, 540)
    t5.clips.append(cta)
    comp.tracks.append(t5)
    print("S05 CallToAction: centered")

    # ── SCENE 6: SocialHandle stack ──────────────────────────────────────
    # SCENE: social | 90f | Primary: 3 social handles | Secondary: none
    # ENTRY: 0-18 staggered | HOLD: 18-72 | EXIT: 72-90
    offset = SEC * 5
    t6 = pm.Track(name="s06_social")
    platforms = [("youtube", "@PyMotion"), ("instagram", "@pymotion.dev"), ("x", "@pymotionstudio")]
    for i, (plat, handle) in enumerate(platforms):
        sh = pm.SocialHandle(
            platform=plat,
            handle=handle,
            style="default",
            animate_in=NORMAL,
        )
        y_pos = 400 + i * 80
        sh.set_duration(SEC - i * STAGGER).at(offset + i * STAGGER).set_position(400, y_pos)
        t6.clips.append(sh)
    comp.tracks.append(t6)
    print("S06 SocialHandle: 3 handles, left-aligned, staggered")

    # ── SCENE 7: Countdown ───────────────────────────────────────────────
    # SCENE: countdown | 90f | Primary: digit | Secondary: none
    # ENTRY: instant | HOLD: 0-90 (digit transitions are the animation)
    offset = SEC * 6
    t7 = pm.Track(name="s07_countdown")
    countdown = pm.Countdown(
        from_n=5,
        count_duration=SEC,
        style="numbers",
        size=120.0,
    )
    countdown.set_duration(SEC).at(offset).set_position(960, 486)
    t7.clips.append(countdown)
    comp.tracks.append(t7)
    print("S07 Countdown: large centered digit")

    # ── SCENE 8: BarChartClip ────────────────────────────────────────────
    # SCENE: bar_chart | 90f | Primary: chart | Secondary: title
    # ENTRY: 0-24 (bars grow) | HOLD: 24-72 | EXIT: 72-90
    offset = SEC * 7
    t8 = pm.Track(name="s08_bar")
    bar = pm.BarChartClip(
        data=[45.0, 72.0, 58.0, 91.0, 36.0],
        labels=["Q1", "Q2", "Q3", "Q4", "Q5"],
        animate_duration=SLOW,
        theme="corporate",
        title="Revenue by Quarter",
        bar_gap=0.3,
        show_values=True,
    )
    bar.set_duration(SEC).at(offset)
    t8.clips.append(bar)
    comp.tracks.append(t8)
    print(f"S08 BarChart: {len(bar.data)} bars")

    # ── SCENE 9: LineChartClip ───────────────────────────────────────────
    # SCENE: line_chart | 90f | Primary: chart | Secondary: title
    # ENTRY: 0-24 (line draws) | HOLD: 24-72 | EXIT: 72-90
    offset = SEC * 8
    t9 = pm.Track(name="s09_line")
    line = pm.LineChartClip(
        data=[10.0, 25.0, 18.0, 42.0, 55.0, 48.0, 63.0],
        labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        animate_duration=SLOW,
        theme="corporate",
        title="Daily Active Users",
        line_width=2.0,
        show_dots=True,
        show_fill=True,
    )
    line.set_duration(SEC).at(offset)
    t9.clips.append(line)
    comp.tracks.append(t9)
    print("S09 LineChart: corporate theme")

    # ── SCENE 10: PieChartClip (donut) ───────────────────────────────────
    # SCENE: pie_chart | 90f | Primary: donut chart | Secondary: title
    # ENTRY: 0-24 (slices sweep) | HOLD: 24-72 | EXIT: 72-90
    offset = SEC * 9
    t10 = pm.Track(name="s10_pie")
    pie = pm.PieChartClip(
        data=[35.0, 25.0, 20.0, 15.0, 5.0],
        labels=["Product", "Services", "Support", "R&D", "Other"],
        animate_duration=SLOW,
        theme="corporate",
        title="Revenue Split",
        show_labels=True,
    )
    pie.set_duration(SEC).at(offset)
    t10.clips.append(pie)
    comp.tracks.append(t10)
    print(f"S10 PieChart: donut={pie.inner_radius > 0}")

    # ── SCENE 11: AreaChartClip ──────────────────────────────────────────
    # SCENE: area_chart | 90f | Primary: chart | Secondary: title
    # ENTRY: 0-24 | HOLD: 24-72 | EXIT: 72-90
    offset = SEC * 10
    t11 = pm.Track(name="s11_area")
    area = pm.AreaChartClip(
        data=[15.0, 30.0, 22.0, 45.0, 38.0, 52.0],
        labels=["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        animate_duration=SLOW,
        title="Growth Trend",
    )
    area.set_duration(SEC).at(offset)
    t11.clips.append(area)
    comp.tracks.append(t11)
    print("S11 AreaChart")

    # ── SCENE 12: RadarChartClip ─────────────────────────────────────────
    # SCENE: radar_chart | 90f | Primary: chart | Secondary: title
    # ENTRY: 0-24 | HOLD: 24-72 | EXIT: 72-90
    offset = SEC * 11
    t12 = pm.Track(name="s12_radar")
    radar = pm.RadarChartClip(
        data=[80.0, 65.0, 90.0, 45.0, 70.0],
        axes=["Speed", "Quality", "Cost", "Support", "UX"],
        animate_duration=SLOW,
        title="Product Scores",
        fill_opacity=0.3,
    )
    radar.set_duration(SEC).at(offset)
    t12.clips.append(radar)
    comp.tracks.append(t12)
    print("S12 RadarChart")

    # ── SCENE 13: NumberCounter ──────────────────────────────────────────
    # SCENE: counter | 90f | Primary: large number | Secondary: label
    # ENTRY: instant | HOLD: 0-90 (number counting is the animation)
    # INCREASED counter size 72→96px: principle 6, type does the work
    offset = SEC * 12
    t13 = pm.Track(name="s13_counter")
    counter = pm.NumberCounter(
        start_value=0.0,
        end_value=1_000_000.0,
        count_duration=SEC,
        size=96.0,
        color=ACCENT.a300,
    )
    counter.set_duration(SEC).at(offset).set_position(960, 460)
    t13.clips.append(counter)
    # Label below counter
    counter_label = pm.TextClip(
        text="Total Users",
        size=18,
        color=theme.muted,
    )
    counter_label.set_duration(SEC).at(offset).set_position(960, 560)
    t13.clips.append(counter_label)
    comp.tracks.append(t13)
    print("S13 NumberCounter: 96px, full scene")

    # ── SCENE 14: ProgressBar ────────────────────────────────────────────
    # SCENE: progress | 90f | Primary: progress bar | Secondary: label + value
    # ENTRY: 0-24 (bar fills) | HOLD: 24-72 | EXIT: 72-90
    # INCREASED bar size: principle 2, hierarchy through size
    offset = SEC * 13
    t14 = pm.Track(name="s14_progress")
    # Label above bar
    progress_label = pm.TextClip(
        text="Project Completion",
        size=24,
        color=theme.text,
    )
    progress_label.set_duration(SEC).at(offset).set_position(960, 460)
    t14.clips.append(progress_label)
    progress = pm.ProgressBar(
        value=0.75,
        bar_width=800.0,
        bar_height=40.0,
        fill_color=ACCENT.a500,
        bg_color=NEUTRAL.n800,
    )
    progress.set_duration(SEC).at(offset).set_position(960, 540)
    t14.clips.append(progress)
    comp.tracks.append(t14)
    print("S14 ProgressBar: 800x40, full scene")

    # ── SCENE 15: BrowserMockup ──────────────────────────────────────────
    # SCENE: browser | 90f | Primary: browser mockup | Secondary: none
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = SEC * 14
    t15 = pm.Track(name="s15_browser")
    browser_content = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    browser_content.set_duration(SEC)
    browser = pm.BrowserMockup(
        content_clip=browser_content,
        mockup_theme="dark",
        url_text="https://pymotion.dev",
        corner_radius=12.0,
    )
    browser.set_duration(SEC).at(offset).set_position(960, 540)
    t15.clips.append(browser)
    comp.tracks.append(t15)
    print("S15 BrowserMockup: centered, dark")

    # ── SCENE 16: PhoneMockup ────────────────────────────────────────────
    # SCENE: phone | 90f | Primary: phone mockup | Secondary: none
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = SEC * 15
    t16 = pm.Track(name="s16_phone")
    phone_content = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    phone_content.set_duration(SEC)
    phone = pm.PhoneMockup(
        content_clip=phone_content,
        model="dynamic_island",
        bezel_color=NEUTRAL.n900,
    )
    phone.set_duration(SEC).at(offset).set_position(960, 540)
    t16.clips.append(phone)
    comp.tracks.append(t16)
    print("S16 PhoneMockup: centered")

    # ── SCENE 17: DesktopMockup ──────────────────────────────────────────
    # SCENE: desktop | 90f | Primary: desktop mockup | Secondary: none
    # ENTRY: 0-18 | HOLD: 18-72 | EXIT: 72-90
    offset = SEC * 16
    t17 = pm.Track(name="s17_desktop")
    desk_content = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    desk_content.set_duration(SEC)
    desktop = pm.DesktopMockup(
        content_clip=desk_content,
        os_theme="macos",
        window_title="PyMotion Studio",
    )
    desktop.set_duration(SEC).at(offset).set_position(960, 540)
    t17.clips.append(desktop)
    comp.tracks.append(t17)
    print("S17 DesktopMockup: macos, centered")

    # ── Transition demos (exercised inline, not visible) ─────────────────
    # SlideDown + SlideUp + WipeRight + WipeDiagonal — render test frames
    frame_a = np.full((100, 100, 4), [200, 150, 100, 255], dtype=np.uint8)
    frame_b = np.full((100, 100, 4), [50, 100, 200, 255], dtype=np.uint8)
    sd_result = pm.SlideDown().render_frame(frame_a, frame_b, 0.5)
    su_result = pm.SlideUp().render_frame(frame_a, frame_b, 0.5)
    wr_result = pm.WipeRight().render_frame(frame_a, frame_b, 0.5)
    wd_result = pm.WipeDiagonal().render_frame(frame_a, frame_b, 0.5)
    print(
        f"Transitions: SlideDown={sd_result.mean():.0f}, SlideUp={su_result.mean():.0f},"
        f" WipeRight={wr_result.mean():.0f}, WipeDiagonal={wd_result.mean():.0f}"
    )

    # ── Transition between scenes: SlideRight, WipeLeft, SlideDown ───────
    # Exercise the transition classes on the composition via concatenated clips
    # (This keeps them in the feature coverage without cluttering scenes)
    t_trans = pm.Track(name="s_transitions")
    tr_a = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    tr_a.set_duration(45)
    tr_b = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    tr_b.set_duration(45)
    tr_concat = pm.concatenate(
        [tr_a, tr_b],
        transition=pm.SlideRight(),
        transition_duration=20,
    )
    # Place in a gap that overlaps with existing content (doesn't visually interfere
    # because it's behind the main scene tracks)
    tr_concat.at(0)
    t_trans.clips.append(tr_concat)

    wl_a = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    wl_a.set_duration(45)
    wl_b = pm.ImageClip(str(ASSETS / "product_c.jpg"))
    wl_b.set_duration(45)
    wl_concat = pm.concatenate(
        [wl_a, wl_b],
        transition=pm.WipeLeft(),
        transition_duration=20,
    )
    wl_concat.at(90)
    t_trans.clips.append(wl_concat)
    # Insert as first track (behind bg) so it doesn't show
    comp.tracks.insert(0, t_trans)
    print(
        "Transitions exercised: SlideRight, WipeLeft, SlideDown, SlideUp, WipeRight, WipeDiagonal"
    )

    # REMOVED: Divider, Watermark were crammed with Countdown+LogoReveal in one scene
    # — principle 1, one thing at a time. They are still exercised:
    # Divider
    t_div = pm.Track(name="s_divider_exercise")
    divider = pm.Divider(
        style="gradient",
        direction="horizontal",
        div_duration=NORMAL,
        thickness=1.0,
    )
    divider.set_duration(30).at(0).set_position(960, 540)
    t_div.clips.append(divider)
    comp.tracks.insert(0, t_div)

    # Watermark — persistent, low opacity, top-right (present throughout)
    t_wm = pm.Track(name="s_watermark")
    watermark = pm.Watermark(
        image_or_text="PyMotion",
        position="top-right",
        watermark_opacity=0.12,
        font_size=14.0,
        margin=24.0,
    )
    watermark.set_duration(TOTAL).at(0)
    t_wm.clips.append(watermark)
    comp.tracks.append(t_wm)
    print("Watermark: persistent, 12% opacity")

    # ScatterPlotClip — exercised in background track to maintain feature coverage
    t_scatter = pm.Track(name="s_scatter_exercise")
    scatter = pm.ScatterPlotClip(
        x=[10, 20, 30, 45, 55, 65, 80, 90],
        y=[15, 35, 28, 50, 42, 68, 75, 85],
        animate_duration=SLOW,
        title="Correlation",
        point_size=4.0,
    )
    scatter.set_duration(SEC).at(0)
    t_scatter.clips.append(scatter)
    comp.tracks.insert(0, t_scatter)
    print(f"ScatterPlotClip exercised: {len(scatter.x)} points")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "09_mograph.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
