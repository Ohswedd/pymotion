"""Example 06 — Video Editing Showcase.

Demonstrates v1.2 clip operations, speed/time manipulation,
keying effects, layout helpers, and proxy workflow.

Niche: Video editor / post-production demo reel
"""

from __future__ import annotations

from pathlib import Path

from pymotion import (
    ColorClip,
    Composition,
    CrossDissolve,
    TextClip,
    Track,
    concatenate,
    grid,
    pip,
    split_screen,
    stack,
)
from pymotion.effects.keying import ChromaKey, LumaKey
from pymotion.text.animated import Typewriter
from pymotion.utils.color import Color

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def make_color_clip(color: str, duration: int = 90) -> ColorClip:
    """Create a color clip with the given hex color and duration."""
    clip = ColorClip(color=Color.parse(color))
    clip.set_duration(duration)
    return clip


def demo_clip_operations() -> Composition:
    """Split, join, subclip, repeat — then concatenate the results."""
    original = make_color_clip("#E94560", 120)
    first_half, second_half = original.split(60)

    excerpt = first_half.subclip(10, 50)  # 40 frames
    looped = excerpt.repeat(2)  # 80 frames
    blue = make_color_clip("#0F3460", 40)
    combined = second_half.join(blue)  # 100 frames

    # Concatenate all pieces into one sequence
    final = concatenate([looped, combined])

    comp = Composition(1920, 1080, fps=30, duration=final.duration)
    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", final.duration)
    bg_track.add(bg)

    label_track = Track(name="label")
    label = Typewriter(
        text="split + subclip + repeat + join",
        font_size=48.0,
        color=Color(1.0, 0.84, 0.0, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(final.duration).set_position(960.0, 200.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(label_track)
    return comp


def demo_speed_time() -> Composition:
    """Speed, reverse, speed ramp — build a sequence from each result."""
    clip = make_color_clip("#4FC3F7", 60)

    fast = clip.speed(2.0)  # 30 frames
    backwards = fast.reverse()  # 30 frames
    ramped = clip.speed_ramp(
        [
            (0, 1.0),
            (20, 0.5),
            (40, 2.0),
            (60, 1.0),
        ]
    )

    # Chain: fast → reversed → ramped
    sequence = concatenate(
        [fast, backwards, ramped],
        transition=CrossDissolve(),
        transition_duration=10,
    )

    comp = Composition(1920, 1080, fps=30, duration=sequence.duration)
    bg_track = Track(name="bg")
    bg = make_color_clip("#1B2838", sequence.duration)
    bg_track.add(bg)

    label_track = Track(name="label")
    label = Typewriter(
        text="speed(2x) > reverse > speed_ramp",
        font_size=44.0,
        color=Color(0.31, 0.76, 0.97, 1.0),
        chars_per_frame=2.0,
    )
    label.set_duration(sequence.duration).set_position(960.0, 200.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(label_track)
    return comp


def demo_keying() -> Composition:
    """Apply ChromaKey and LumaKey to clips in a composition."""
    duration = 120
    comp = Composition(1920, 1080, fps=30, duration=duration)

    # Background layer
    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", duration)
    bg_track.add(bg)

    # Foreground with ChromaKey — the green is keyed out
    fg_track = Track(name="chroma")
    green_clip = make_color_clip("#00FF00", duration)
    green_clip.add_effect(ChromaKey(color="#00FF00", tolerance=0.3))
    green_clip.set_position(200.0, 300.0)
    fg_track.add(green_clip)

    # Another layer with LumaKey — dark areas removed
    luma_track = Track(name="luma")
    dark_clip = make_color_clip("#1A1A1A", duration)
    dark_clip.add_effect(LumaKey(threshold=0.2, softness=0.1))
    dark_clip.set_position(960.0, 300.0)
    luma_track.add(dark_clip)

    # Label
    label_track = Track(name="label")
    label = TextClip("ChromaKey + LumaKey", font="Arial", size=40.0, color="#00FF88")
    label.set_duration(duration).set_position(960.0, 100.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(fg_track)
    comp.add_track(luma_track)
    comp.add_track(label_track)
    return comp


def demo_layouts() -> Composition:
    """Render four layout modes: grid, split screen, stack, PiP."""
    duration = 90

    # --- Grid 2x2 ---
    grid_clips = [
        make_color_clip("#E94560", duration),
        make_color_clip("#0F3460", duration),
        make_color_clip("#533483", duration),
        make_color_clip("#16213E", duration),
    ]
    return grid(grid_clips, rows=2, cols=2, gap=8, background="#000000")


def demo_split_screen() -> Composition:
    """Horizontal split screen."""
    duration = 90
    left = make_color_clip("#E94560", duration)
    right = make_color_clip("#0F3460", duration)
    return split_screen([left, right], layout="horizontal")


def demo_stack() -> Composition:
    """Vertical stack."""
    duration = 90
    top = make_color_clip("#4FC3F7", duration)
    bottom = make_color_clip("#FF6F61", duration)
    return stack([top, bottom], direction="vertical", gap=4)


def demo_pip() -> Composition:
    """Picture-in-picture with bottom-right overlay."""
    duration = 90
    main_clip = make_color_clip("#1a1a2e", duration)
    overlay_clip = make_color_clip("#E94560", duration)
    return pip(main_clip, overlay_clip, position="bottom-right", size=(384, 216))


def demo_concatenate_transitions() -> Composition:
    """Concatenate four clips with CrossDissolve transitions."""
    clips = [
        make_color_clip("#E94560", 60),
        make_color_clip("#0F3460", 60),
        make_color_clip("#533483", 60),
        make_color_clip("#16213E", 60),
    ]
    return concatenate(clips, transition=CrossDissolve(), transition_duration=15)


def demo_proxy() -> Composition:
    """Create a low-res proxy and display its dimensions."""
    source = make_color_clip("#E94560", 90)
    proxy = source.create_proxy(scale=0.25)

    comp = Composition(1920, 1080, fps=30, duration=90)

    bg_track = Track(name="bg")
    bg = make_color_clip("#0D1B2A", 90)
    bg_track.add(bg)

    label_track = Track(name="label")
    label = TextClip(
        f"Proxy: {proxy._width}x{proxy._height} (25% of 1920x1080)",
        font="Arial",
        size=36.0,
        color="#FFFFFF",
    )
    label.set_duration(90).set_position(960.0, 540.0)
    label_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(label_track)
    return comp


def main() -> None:
    """Run the video editing showcase."""
    print("=== PyMotion v1.2 Video Editing Showcase ===\n")

    demos = [
        ("06_clip_operations.mp4", "Clip operations", demo_clip_operations),
        ("06_speed_time.mp4", "Speed & time", demo_speed_time),
        ("06_keying.mp4", "Keying effects", demo_keying),
        ("06_grid_layout.mp4", "Grid layout", demo_layouts),
        ("06_split_screen.mp4", "Split screen", demo_split_screen),
        ("06_stack.mp4", "Stack layout", demo_stack),
        ("06_pip.mp4", "Picture-in-picture", demo_pip),
        ("06_concatenated.mp4", "Concatenation + transitions", demo_concatenate_transitions),
        ("06_proxy.mp4", "Proxy workflow", demo_proxy),
    ]

    for i, (filename, label, fn) in enumerate(demos, 1):
        print(f"[{i}/{len(demos)}] {label}...")
        comp = fn()
        comp.render(str(OUTPUT_DIR / filename), preset="h264_1080p")

    print(f"\nAll {len(demos)} demos rendered to examples/output/")


if __name__ == "__main__":
    main()
