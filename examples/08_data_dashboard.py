"""Example 08 — Data Dashboard.

Demonstrates v1.4 data visualization features: animated charts,
number counters, progress bars, device mockups, and motion graphics
overlays for a polished dashboard-style video.

Niche: Data visualization / SaaS product demos
"""

from __future__ import annotations

from pathlib import Path

from pymotion import (
    AreaChartClip,
    BarChartClip,
    BrowserMockup,
    CallToAction,
    ColorClip,
    Composition,
    Countdown,
    DesktopMockup,
    Divider,
    LineChartClip,
    LowerThird,
    NumberCounter,
    PhoneMockup,
    PieChartClip,
    ProgressBar,
    QuoteCard,
    RadarChartClip,
    ScatterPlotClip,
    SocialHandle,
    TextClip,
    Track,
    TransitionTitle,
    Watermark,
)
from pymotion.utils.color import Color

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def demo_bar_chart() -> None:
    """Animated bar chart with corporate theme."""
    comp = Composition(1920, 1080, fps=30, duration=90)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#0D1B2A").set_duration(90)
    bg_track.add(bg)

    chart_track = Track(name="chart")
    chart = BarChartClip(
        data={"Q1": 120, "Q2": 200, "Q3": 180, "Q4": 250},
        animate_duration=30,
        theme="corporate",
        title="Quarterly Revenue ($K)",
        show_values=True,
    )
    chart.set_duration(90)
    chart_track.add(chart)

    comp.add_track(bg_track)
    comp.add_track(chart_track)
    comp.render(str(OUTPUT_DIR / "08a_bar_chart.mp4"), preset="h264_1080p")


def demo_line_and_pie() -> None:
    """Line chart with neon theme and pie chart with gradient theme."""
    comp = Composition(1920, 1080, fps=30, duration=90)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#111111").set_duration(90)
    bg_track.add(bg)

    line_track = Track(name="line")
    line = LineChartClip(
        data=[10, 25, 15, 30, 22, 35, 28],
        labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        animate_duration=30,
        theme="neon",
        show_dots=True,
        show_fill=True,
    )
    line.set_duration(90).set_position(60.0, 60.0)
    line_track.add(line)

    pie_track = Track(name="pie")
    pie = PieChartClip(
        data={"Desktop": 55, "Mobile": 35, "Tablet": 10},
        animate_duration=30,
        theme="gradient",
        inner_radius=0.4,
    )
    pie.set_duration(90).set_position(1020.0, 60.0)
    pie_track.add(pie)

    comp.add_track(bg_track)
    comp.add_track(line_track)
    comp.add_track(pie_track)
    comp.render(str(OUTPUT_DIR / "08b_line_and_pie.mp4"), preset="h264_1080p")


def demo_counter_and_progress() -> None:
    """Number counter and progress bar animation."""
    comp = Composition(1920, 1080, fps=30, duration=120)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#1a1a2e").set_duration(120)
    bg_track.add(bg)

    counter_track = Track(name="counter")
    counter = NumberCounter(
        start_value=0,
        end_value=1_000_000,
        count_duration=60,
        format_fn=lambda v: f"${v:,.0f}",
        size=96.0,
    )
    counter.set_duration(120).set_position(660.0, 300.0)
    counter_track.add(counter)

    bar_track = Track(name="bar")
    bar = ProgressBar(
        value=lambda f: min(f / 90.0, 1.0),
        bar_width=600,
        bar_height=40,
        fill_color=Color.parse("#10B981"),
        radius=20,
    )
    bar.set_duration(120).set_position(660.0, 550.0)
    bar_track.add(bar)

    label_track = Track(name="labels")
    label = TextClip("Total Revenue", font="Arial", size=32.0, color="#FFFFFF")
    label.set_duration(120).set_position(810.0, 250.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(counter_track)
    comp.add_track(bar_track)
    comp.add_track(label_track)
    comp.render(str(OUTPUT_DIR / "08c_counter_progress.mp4"), preset="h264_1080p")


def demo_device_mockups() -> None:
    """Browser, phone, and desktop mockups wrapping content clips."""
    comp = Composition(1920, 1080, fps=30, duration=90)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#0f0f23").set_duration(90)
    bg_track.add(bg)

    # Browser mockup
    browser_track = Track(name="browser")
    web_content = ColorClip(color="#2563EB").set_duration(90)
    browser = BrowserMockup(
        content_clip=web_content,
        mockup_theme="dark",
        url_text="https://pymotion.dev",
        animate_in_frames=15,
    )
    browser.set_duration(90).set_position(60.0, 120.0)
    browser_track.add(browser)

    # Phone mockup
    phone_track = Track(name="phone")
    app_content = ColorClip(color="#10B981").set_duration(90)
    phone = PhoneMockup(
        content_clip=app_content,
        model="dynamic_island",
        animate_in_frames=15,
    )
    phone.set_duration(90).set_position(1400.0, 120.0)
    phone_track.add(phone)

    comp.add_track(bg_track)
    comp.add_track(browser_track)
    comp.add_track(phone_track)
    comp.render(str(OUTPUT_DIR / "08d_device_mockups.mp4"), preset="h264_1080p")


def demo_motion_graphics_overlay() -> None:
    """Lower third, watermark, CTA, and transition title overlays."""
    comp = Composition(1920, 1080, fps=30, duration=150)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#16213e").set_duration(150)
    bg_track.add(bg)

    # Transition title intro
    title_track = Track(name="title")
    title = TransitionTitle(
        text="Q4 Performance Report",
        style="slide_up",
        animate_in=15,
        animate_out=15,
        font_size=56.0,
    )
    title.set_duration(60)
    title_track.add(title)

    # Bar chart as main content
    chart_track = Track(name="chart")
    chart = BarChartClip(
        data={"Jan": 80, "Feb": 95, "Mar": 110, "Apr": 130},
        animate_duration=30,
        theme="neon",
        title="Monthly Growth",
        show_values=True,
    )
    chart.set_duration(90).at(60)
    chart_track.add(chart)

    # Lower third
    lt_track = Track(name="lower_third")
    lt = LowerThird(
        name="Jane Smith",
        title="VP of Analytics",
        style="modern",
        animate_in=15,
        animate_out=15,
    )
    lt.set_duration(90).at(60)
    lt_track.add(lt)

    # CTA
    cta_track = Track(name="cta")
    cta = CallToAction(
        text="Learn More",
        sub_text="pymotion.dev/analytics",
        style="visit",
        animate_in=15,
    )
    cta.set_duration(60).at(90)
    cta_track.add(cta)

    # Watermark
    wm_track = Track(name="watermark")
    wm = Watermark(
        image_or_text="PyMotion Demo",
        position="top-right",
        watermark_opacity=0.3,
        font_size=16.0,
    )
    wm.set_duration(150)
    wm_track.add(wm)

    comp.add_track(bg_track)
    comp.add_track(title_track)
    comp.add_track(chart_track)
    comp.add_track(lt_track)
    comp.add_track(cta_track)
    comp.add_track(wm_track)
    comp.render(str(OUTPUT_DIR / "08e_motion_graphics.mp4"), preset="h264_1080p")


def demo_full_dashboard() -> None:
    """Complete dashboard combining charts, mockups, and overlays."""
    comp = Composition(1920, 1080, fps=30, duration=180)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#0D1B2A").set_duration(180)
    bg_track.add(bg)

    # Radar chart
    radar_track = Track(name="radar")
    radar = RadarChartClip(
        data=[85, 70, 90, 60, 75],
        axes=["Speed", "Power", "Range", "Defense", "HP"],
        animate_duration=25,
        theme="minimal",
    )
    radar.set_duration(90).set_position(60.0, 60.0)
    radar_track.add(radar)

    # Area chart
    area_track = Track(name="area")
    area = AreaChartClip(
        data=[5, 15, 10, 25, 20, 30],
        animate_duration=20,
        fill_opacity=0.5,
    )
    area.set_duration(90).set_position(960.0, 60.0)
    area_track.add(area)

    # Scatter plot
    scatter_track = Track(name="scatter")
    scatter = ScatterPlotClip(
        x=[1, 2, 3, 4, 5, 6, 7],
        y=[2.1, 4.0, 3.5, 5.2, 4.8, 6.1, 5.5],
        animate_duration=30,
        point_size=6.0,
    )
    scatter.set_duration(90).at(90).set_position(60.0, 60.0)
    scatter_track.add(scatter)

    # Desktop mockup
    desktop_track = Track(name="desktop")
    desktop_content = ColorClip(color="#6366F1").set_duration(90)
    desktop = DesktopMockup(
        content_clip=desktop_content,
        os_theme="macos",
        window_title="Analytics Dashboard",
        animate_in_frames=15,
    )
    desktop.set_duration(90).at(90).set_position(960.0, 60.0)
    desktop_track.add(desktop)

    # Divider
    div_track = Track(name="divider")
    div = Divider(
        style="gradient",
        direction="horizontal",
        div_duration=20,
    )
    div.set_duration(30).at(85)
    div_track.add(div)

    # Social handle
    social_track = Track(name="social")
    handle = SocialHandle(
        platform="youtube",
        handle="@pymotion",
        animate_in=15,
    )
    handle.set_duration(60).at(120)
    social_track.add(handle)

    # Countdown
    timer_track = Track(name="timer")
    timer = Countdown(
        from_n=5,
        count_duration=150,
        style="numbers",
        size=48.0,
    )
    timer.set_duration(150).at(30).set_position(1750.0, 50.0)
    timer_track.add(timer)

    # Quote card
    quote_track = Track(name="quote")
    quote = QuoteCard(
        text="Data tells the story.",
        attribution="— PyMotion Team",
        style="elegant",
        animate_in=20,
    )
    quote.set_duration(60).at(120).set_position(400.0, 400.0)
    quote_track.add(quote)

    comp.add_track(bg_track)
    comp.add_track(radar_track)
    comp.add_track(area_track)
    comp.add_track(scatter_track)
    comp.add_track(desktop_track)
    comp.add_track(div_track)
    comp.add_track(social_track)
    comp.add_track(timer_track)
    comp.add_track(quote_track)
    comp.render(str(OUTPUT_DIR / "08f_full_dashboard.mp4"), preset="h264_1080p")


if __name__ == "__main__":
    demo_bar_chart()
    demo_line_and_pie()
    demo_counter_and_progress()
    demo_device_mockups()
    demo_motion_graphics_overlay()
    demo_full_dashboard()
