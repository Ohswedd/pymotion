"""EX09 — Motion Graphics & Charts.

Use-case: A data-driven dashboard video with animated charts,
motion graphics titles, device mockups, and branded overlays.

Features exercised:
  TransitionTitle, LowerThird, Divider, QuoteCard, CallToAction,
  SocialHandle, Watermark, Countdown, LogoReveal,
  BarChartClip, LineChartClip, PieChartClip, AreaChartClip,
  RadarChartClip, ScatterPlotClip, NumberCounter, ProgressBar,
  BrowserMockup, DesktopMockup, PhoneMockup

Output: 1920x1080, 30fps, 30s, preset h264_fast -> outputs/09_mograph.mp4
Estimated render time: ~60s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 75  # 2.5s per section
TOTAL = SEC * 12  # 12 sections = 30s


def main() -> None:
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Background ───────────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.GradientClip(color_start="#0f172a", color_end="#1e293b", direction=135.0)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── Section 1: TransitionTitle ───────────────────────────────────────
    offset = 0
    sec1 = pm.Track(name="sec1")
    tt = pm.TransitionTitle(
        text="QUARTERLY REPORT",
        style="slide_up",
        title_duration=SEC,
        animate_in=15,
        animate_out=15,
        font_size=64.0,
    )
    tt.set_duration(SEC).at(offset)
    sec1.clips.append(tt)
    comp.tracks.append(sec1)
    print(f"1. TransitionTitle: style={tt.style}")

    # ── Section 2: LowerThird ────────────────────────────────────────────
    offset = SEC
    sec2 = pm.Track(name="sec2")
    lt = pm.LowerThird(
        name="Jane Smith",
        title="Chief Data Officer",
        style="modern",
        animate_in=15,
        animate_out=10,
        margin_bottom=80.0,
    )
    lt.set_duration(SEC).at(offset)
    sec2.clips.append(lt)
    comp.tracks.append(sec2)
    print(f"2. LowerThird: style={lt.style}")

    # ── Section 3: BarChartClip ──────────────────────────────────────────
    offset = SEC * 2
    sec3 = pm.Track(name="sec3")
    bar = pm.BarChartClip(
        data=[45.0, 72.0, 58.0, 91.0, 36.0],
        labels=["Q1", "Q2", "Q3", "Q4", "Q5"],
        animate_duration=30,
        theme="corporate",
        title="Revenue by Quarter",
        bar_gap=0.3,
        show_values=True,
    )
    bar.set_duration(SEC).at(offset)
    sec3.clips.append(bar)
    comp.tracks.append(sec3)
    print(f"3. BarChartClip: {len(bar.data)} bars, theme={bar.theme}")

    # ── Section 4: LineChartClip ─────────────────────────────────────────
    offset = SEC * 3
    sec4 = pm.Track(name="sec4")
    line = pm.LineChartClip(
        data=[10.0, 25.0, 18.0, 42.0, 55.0, 48.0, 63.0],
        labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        animate_duration=30,
        theme="neon",
        title="Daily Active Users",
        line_width=3.0,
        show_dots=True,
        show_fill=True,
    )
    line.set_duration(SEC).at(offset)
    sec4.clips.append(line)
    comp.tracks.append(sec4)
    print(f"4. LineChartClip: theme={line.theme}")

    # ── Section 5: PieChartClip ──────────────────────────────────────────
    offset = SEC * 4
    sec5 = pm.Track(name="sec5")
    pie = pm.PieChartClip(
        data=[35.0, 25.0, 20.0, 15.0, 5.0],
        labels=["Product", "Services", "Support", "R&D", "Other"],
        animate_duration=30,
        theme="gradient",
        title="Revenue Split",
        show_labels=True,
        inner_radius=0.4,
    )
    pie.set_duration(SEC).at(offset)
    sec5.clips.append(pie)
    comp.tracks.append(sec5)
    print(f"5. PieChartClip: donut={pie.inner_radius > 0}")

    # ── Section 6: AreaChartClip + RadarChartClip ────────────────────────
    offset = SEC * 5
    sec6 = pm.Track(name="sec6")
    area = pm.AreaChartClip(
        data=[15.0, 30.0, 22.0, 45.0, 38.0, 52.0],
        labels=["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        animate_duration=25,
        title="Growth Trend",
        fill_opacity=0.4,
    )
    area.set_duration(SEC).at(offset)
    sec6.clips.append(area)
    comp.tracks.append(sec6)
    print(f"6. AreaChartClip: fill_opacity={area.fill_opacity}")

    # ── Section 7: RadarChartClip ────────────────────────────────────────
    offset = SEC * 6
    sec7 = pm.Track(name="sec7")
    radar = pm.RadarChartClip(
        data=[80.0, 65.0, 90.0, 45.0, 70.0],
        axes=["Speed", "Quality", "Cost", "Support", "UX"],
        animate_duration=30,
        title="Product Scores",
        fill_opacity=0.3,
    )
    radar.set_duration(SEC).at(offset)
    sec7.clips.append(radar)
    comp.tracks.append(sec7)
    print(f"7. RadarChartClip: {len(radar.data)} axes")

    # ── Section 8: ScatterPlotClip ───────────────────────────────────────
    offset = SEC * 7
    sec8 = pm.Track(name="sec8")
    scatter = pm.ScatterPlotClip(
        x=[10, 20, 30, 45, 55, 65, 80, 90],
        y=[15, 35, 28, 50, 42, 68, 75, 85],
        animate_duration=25,
        title="Correlation",
        point_size=6.0,
    )
    scatter.set_duration(SEC).at(offset)
    sec8.clips.append(scatter)
    comp.tracks.append(sec8)
    print(f"8. ScatterPlotClip: {len(scatter.x)} points")

    # ── Section 9: NumberCounter + ProgressBar ───────────────────────────
    offset = SEC * 8
    sec9 = pm.Track(name="sec9")
    counter = pm.NumberCounter(
        start_value=0.0,
        end_value=1_000_000.0,
        count_duration=SEC,
        size=72.0,
        color=pm.Color(0.2, 0.8, 1.0, 1.0),
    )
    counter.set_duration(SEC).at(offset).set_position(960, 400)
    sec9.clips.append(counter)

    progress = pm.ProgressBar(
        value=0.75,
        bar_width=600.0,
        bar_height=30.0,
        fill_color=pm.Color.parse("#2563EB"),
        bg_color=pm.Color.parse("#334155"),
        radius=8.0,
    )
    progress.set_duration(SEC).at(offset).set_position(960, 600)
    sec9.clips.append(progress)
    comp.tracks.append(sec9)
    print(f"9. NumberCounter + ProgressBar: value={progress.value}")

    # ── Section 10: QuoteCard + CallToAction + SocialHandle ──────────────
    offset = SEC * 9
    sec10 = pm.Track(name="sec10")
    quote = pm.QuoteCard(
        text="Data is the new oil.",
        attribution="Clive Humby",
        style="elegant",
        animate_in=20,
    )
    quote.set_duration(SEC).at(offset)
    sec10.clips.append(quote)

    cta = pm.CallToAction(
        text="Learn More",
        sub_text="Visit our website",
        style="visit",
        animate_in=15,
    )
    cta.set_duration(SEC).at(offset).set_position(960, 900)
    sec10.clips.append(cta)

    social = pm.SocialHandle(
        platform="youtube",
        handle="@PyMotion",
        style="default",
        animate_in=15,
    )
    social.set_duration(SEC).at(offset).set_position(960, 980)
    sec10.clips.append(social)
    comp.tracks.append(sec10)
    print("10. QuoteCard + CallToAction + SocialHandle")

    # ── Section 11: Divider + Watermark + Countdown + LogoReveal ─────────
    offset = SEC * 10
    sec11 = pm.Track(name="sec11")
    divider = pm.Divider(
        style="gradient",
        direction="horizontal",
        div_duration=20,
        thickness=3.0,
    )
    divider.set_duration(SEC).at(offset).set_position(960, 540)
    sec11.clips.append(divider)

    watermark = pm.Watermark(
        image_or_text="PyMotion",
        position="bottom-right",
        watermark_opacity=0.3,
        font_size=18.0,
        margin=20.0,
    )
    watermark.set_duration(SEC).at(offset)
    sec11.clips.append(watermark)

    countdown = pm.Countdown(
        from_n=5,
        count_duration=SEC,
        style="numbers",
        size=100.0,
    )
    countdown.set_duration(SEC).at(offset).set_position(960, 300)
    sec11.clips.append(countdown)

    logo_reveal = pm.LogoReveal(
        image=str(ASSETS / "logo.png"),
        style="fade",
        reveal_duration=30,
        logo_size=(200.0, 200.0),
    )
    logo_reveal.set_duration(SEC).at(offset).set_position(960, 750)
    sec11.clips.append(logo_reveal)
    comp.tracks.append(sec11)
    print("11. Divider + Watermark + Countdown + LogoReveal")

    # ── Section 12: BrowserMockup + PhoneMockup + DesktopMockup ──────────
    offset = SEC * 11
    sec12 = pm.Track(name="sec12")

    content_img = pm.ImageClip(str(ASSETS / "product_hero.jpg"))
    content_img.set_duration(SEC)

    browser = pm.BrowserMockup(
        content_clip=content_img,
        mockup_theme="dark",
        url_text="https://pymotion.dev",
        corner_radius=12.0,
    )
    browser.set_duration(SEC).at(offset).set_position(480, 540)
    sec12.clips.append(browser)

    phone_content = pm.ImageClip(str(ASSETS / "product_a.jpg"))
    phone_content.set_duration(SEC)
    phone = pm.PhoneMockup(
        content_clip=phone_content,
        model="dynamic_island",
        bezel_color=pm.Color.parse("#1F2937"),
    )
    phone.set_duration(SEC).at(offset).set_position(1200, 540)
    sec12.clips.append(phone)

    desk_content = pm.ImageClip(str(ASSETS / "product_b.jpg"))
    desk_content.set_duration(SEC)
    desktop = pm.DesktopMockup(
        content_clip=desk_content,
        os_theme="macos",
        window_title="PyMotion Studio",
    )
    desktop.set_duration(SEC).at(offset).set_position(1600, 540)
    sec12.clips.append(desktop)
    comp.tracks.append(sec12)
    print("12. BrowserMockup + PhoneMockup + DesktopMockup")

    # ── Audit frames ─────────────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for sec_idx in range(12):
        mid = sec_idx * SEC + SEC // 2
        try:
            comp.export_frame(frame=mid, output=audit_dir / f"ex09_sec{sec_idx + 1}.png")
        except (ValueError, RuntimeError) as e:
            print(f"  Audit sec{sec_idx + 1} skipped: {e}")
    print("Audit frames exported")

    # ── Render ───────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "09_mograph.mp4"
    comp.render(str(output_path), preset="h264_fast")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Rendered: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
