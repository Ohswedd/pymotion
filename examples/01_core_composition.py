"""EX01 — Core Composition & 2D Rendering.

Use-case: A technical demo showcasing PyMotion's core primitives —
one feature per scene, labeled and clearly visible.

Features exercised:
  Composition, CompositionClip, Track, ColorClip, GradientClip, ImageClip,
  ShapeClip (rect, circle, polygon, line), BlendMode (SCREEN, MULTIPLY,
  OVERLAY), Clip.set_position/set_scale/set_rotation/set_opacity/set_duration/at,
  Clip.add_effect, GaussianBlur, Vignette, Brightness, Contrast,
  Color, Vec2, Vec3, Effect, Align, Resolution, RenderContext, TimeRange,
  Keyframe, KeyframeTrack, animate, AnimatableValue, interpolate,
  EasingFn, get_easing, cubic_bezier, spring, steps,
  OutputPreset, get_preset, PyMotionConfig, get_config, set_config, reset_config,
  Transition, Cut, Fade, DipToColor,
  Bottleneck, ClipTiming, FrameProfile, MemoryReport, RenderProfile,
  benchmark, detect_bottlenecks, memory_report, profile_composition

Output: 1920x1080, 30fps, 30s, preset h264_fast -> outputs/01_core.mp4
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm
from pymotion.design.tokens import ACCENT, NEUTRAL, get_theme

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SEC = 150  # 5s per scene at 30fps
TOTAL = SEC * 6  # 6 scenes = 30s


def main() -> None:
    # ── Config ────────────────────────────────────────────────────────────
    cfg = pm.get_config()
    print(f"Config: allow_network={cfg.allow_network}, cache_max={cfg.cache_max_bytes}")
    pm.set_config(pm.PyMotionConfig(allow_network=False))
    pm.reset_config()

    # ── Verify preset existence ───────────────────────────────────────────
    preset = pm.get_preset("h264_fast")
    print(f"Preset: {preset.name}, codec={preset.codec}")

    # ── Demonstrate core types (print-only, no visual) ────────────────────
    c1 = ACCENT.a500
    c2 = pm.Color(1.0, 0.4, 0.2, 1.0)
    v2 = pm.Vec2(960, 540)
    v3 = pm.Vec3(0.0, 1.0, 0.0)
    res = pm.Resolution(1920, 1080)
    tr = pm.TimeRange(0, 900)
    print(f"Colors: {c1}, {c2}, Vec2: {v2}, Vec3: {v3}, Res: {res}, TR: {tr}")

    # ── Animation primitives (print-only) ─────────────────────────────────
    kf = pm.Keyframe(frame=0, value=0.0)
    track_kf = pm.KeyframeTrack(keyframes=[pm.Keyframe(0, 0.0), pm.Keyframe(30, 1.0)])
    ease_fn = pm.get_easing("ease_in_out_cubic")
    custom_ease = pm.cubic_bezier(0.25, 0.1, 0.25, 1.0)
    spring_val = pm.spring(stiffness=200, damping=15)
    step_val = pm.steps(4)
    interp = pm.interpolate(0.5, 0.0, 100.0)
    anim_val: pm.AnimatableValue = pm.animate(0.0, 1.0, duration=30)
    print(
        f"Keyframe: {kf}, Track: {track_kf}, Easing: {ease_fn}, "
        f"Bezier: {custom_ease}, Spring: {spring_val}, Steps: {step_val}, "
        f"Interp: {interp}, Anim: {anim_val}"
    )

    # ── Effect base, Align, RenderContext, Transitions ─────────────────────
    print(f"Effect base: {pm.Effect.__name__}")
    print(f"Align: {pm.Align.CENTER}")
    ctx = pm.RenderContext(
        frame=0,
        fps=30,
        resolution=pm.Resolution(1920, 1080),
        time_range=pm.TimeRange(0, 900),
        local_frame=0,
        progress=0.0,
    )
    print(f"RenderContext: frame={ctx.frame}")
    print(f"Transitions: {pm.Cut.__name__}, {pm.Fade.__name__}, {pm.DipToColor.__name__}")

    theme = get_theme()
    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Global background ─────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.ColorClip(color=theme.background)
    bg.set_duration(TOTAL)
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── SCENE 1: GradientClip — "Gradients" ─────────────────────────────
    # SCENE: gradients | 150f | Primary: gradient fill | Secondary: label
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = 0
    s1 = pm.Track(name="s1_gradient")
    grad = pm.GradientClip(
        color_start=theme.background,
        color_end=theme.surface,
        direction=135.0,
        gradient_type="linear",
    )
    grad.set_duration(SEC).at(offset)
    s1.clips.append(grad)
    # Radial accent overlay
    radial = pm.GradientClip(
        color_start=ACCENT.a500,
        color_end=NEUTRAL.n900,
        gradient_type="radial",
        center_x=0.5,
        center_y=0.45,
        radius=0.5,
    )
    radial.set_duration(SEC).at(offset).set_opacity(0.3)
    radial.blend_mode = pm.BlendMode.SCREEN
    s1.clips.append(radial)
    # Label
    lbl1 = pm.TextClip(text="GradientClip", size=56, color=theme.text)
    lbl1.set_duration(SEC).at(offset).set_position(960, 486)
    s1.clips.append(lbl1)
    sub1 = pm.TextClip(text="Linear + Radial · BlendMode.SCREEN", size=18, color=theme.muted)
    sub1.set_duration(SEC).at(offset).set_position(960, 560)
    s1.clips.append(sub1)
    comp.tracks.append(s1)
    print("S1: GradientClip + BlendMode.SCREEN")

    # ── SCENE 2: ShapeClip variants ──────────────────────────────────────
    # SCENE: shapes | 150f | Primary: 4 shapes | Secondary: label
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = SEC
    s2 = pm.Track(name="s2_shapes")
    # Rect — top-left quadrant
    rect = pm.ShapeClip.rect(
        x=280,
        y=280,
        w=320,
        h=240,
        fill=NEUTRAL.n500,
        stroke=ACCENT.a500,
        stroke_width=2.0,
    )
    rect.set_duration(SEC).at(offset).set_opacity(0.9).set_rotation(3.0)
    rect.blend_mode = pm.BlendMode.OVERLAY
    s2.clips.append(rect)
    # Circle — top-right quadrant
    circle = pm.ShapeClip.circle(
        cx=1440,
        cy=340,
        r=140,
        fill=ACCENT.a500,
        stroke=NEUTRAL.n100,
        stroke_width=1.5,
    )
    circle.set_duration(SEC).at(offset).set_opacity(0.85)
    s2.clips.append(circle)
    # Polygon — bottom-left quadrant
    tri = pm.ShapeClip.polygon(
        points=[(400, 650), (550, 850), (250, 850)],
        fill=NEUTRAL.n400,
    )
    tri.set_duration(SEC).at(offset).set_opacity(0.8)
    s2.clips.append(tri)
    # Line — bottom-right quadrant
    line = pm.ShapeClip.line(
        x1=1200,
        y1=750,
        x2=1650,
        y2=750,
        color=ACCENT.a500,
        width=3.0,
    )
    line.set_duration(SEC).at(offset)
    s2.clips.append(line)
    # Label
    lbl2 = pm.TextClip(text="ShapeClip", size=56, color=theme.text)
    lbl2.set_duration(SEC).at(offset).set_position(960, 486)
    s2.clips.append(lbl2)
    sub2 = pm.TextClip(text="rect · circle · polygon · line", size=18, color=theme.muted)
    sub2.set_duration(SEC).at(offset).set_position(960, 560)
    s2.clips.append(sub2)
    comp.tracks.append(s2)
    print("S2: ShapeClip (rect, circle, polygon, line) + BlendModes")

    # ── SCENE 3: ImageClip + Brightness + Contrast ───────────────────────
    # SCENE: image_fx | 150f | Primary: product image | Secondary: label
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = SEC * 2
    s3 = pm.Track(name="s3_image")
    product = pm.ImageClip(str(ASSETS / "product_hero.png"))
    product.set_duration(SEC).at(offset).set_position(192, 60).set_scale(0.8)
    product.add_effect(pm.Brightness(value=1.1))
    product.add_effect(pm.Contrast(value=1.15))
    s3.clips.append(product)
    lbl3 = pm.TextClip(text="Brightness + Contrast", size=40, color=theme.text)
    lbl3.set_duration(SEC).at(offset).set_position(960, 680)
    s3.clips.append(lbl3)
    comp.tracks.append(s3)
    print("S3: ImageClip + Brightness + Contrast")

    # ── SCENE 4: GaussianBlur ────────────────────────────────────────────
    # SCENE: blur | 150f | Primary: blurred image | Secondary: label
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = SEC * 3
    s4 = pm.Track(name="s4_blur")
    blur_img = pm.ImageClip(str(ASSETS / "product_hero.png"))
    blur_img.set_duration(SEC).at(offset).set_position(192, 60).set_scale(0.8)
    blur_img.add_effect(pm.GaussianBlur(radius=8.0))
    s4.clips.append(blur_img)
    lbl4 = pm.TextClip(text="GaussianBlur — radius: 8.0", size=40, color=theme.text)
    lbl4.set_duration(SEC).at(offset).set_position(960, 680)
    s4.clips.append(lbl4)
    comp.tracks.append(s4)
    print("S4: GaussianBlur")

    # ── SCENE 5: Vignette ────────────────────────────────────────────────
    # SCENE: vignette | 150f | Primary: vignetted image | Secondary: label
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = SEC * 4
    s5 = pm.Track(name="s5_vignette")
    vig_img = pm.ImageClip(str(ASSETS / "product_hero.png"))
    vig_img.set_duration(SEC).at(offset).set_position(192, 60).set_scale(0.8)
    vig_img.add_effect(pm.Vignette(strength=0.8, radius=0.6, feather=0.3))
    s5.clips.append(vig_img)
    lbl5 = pm.TextClip(text="Vignette — strength: 0.8", size=40, color=theme.text)
    lbl5.set_duration(SEC).at(offset).set_position(960, 680)
    s5.clips.append(lbl5)
    comp.tracks.append(s5)
    print("S5: Vignette")

    # ── SCENE 6: Logo + ColorClip strip ──────────────────────────────────
    # SCENE: branding | 150f | Primary: logo | Secondary: accent strip
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = SEC * 5
    s6 = pm.Track(name="s6_branding")
    logo = pm.ImageClip(str(ASSETS / "logo.png"))
    logo.set_duration(SEC).at(offset).set_position(384, 120).set_scale(0.6, 0.6)
    logo.set_opacity(0.9)
    s6.clips.append(logo)
    # ColorClip accent strip below logo
    strip = pm.ColorClip(color=ACCENT.a500)
    strip.set_duration(SEC).at(offset).set_position(660, 780).set_scale(600, 3)
    strip.set_opacity(0.8)
    s6.clips.append(strip)
    lbl6 = pm.TextClip(text="ImageClip + ColorClip", size=40, color=theme.text)
    lbl6.set_duration(SEC).at(offset).set_position(960, 830)
    s6.clips.append(lbl6)
    comp.tracks.append(s6)
    print("S6: Logo + ColorClip branding")

    # ── Profiling & diagnostics ───────────────────────────────────────────
    profile = pm.profile_composition(comp, start=0, end=5)
    print(f"Profile: {profile.total_ms:.1f}ms for {profile.total_frames} frames")
    print(f"  Avg frame: {profile.avg_frame_ms:.1f}ms")

    bottlenecks = pm.detect_bottlenecks(comp, n_frames=5)
    for b in bottlenecks[:3]:
        print(f"  Bottleneck: {b.category} — {b.description} ({b.time_ms:.1f}ms)")

    mem = pm.memory_report(comp, n_frames=3)
    print(f"  Peak memory: {mem.peak_ram_bytes / 1024 / 1024:.1f} MB")

    # ── Render ────────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "01_core.mp4"
    comp.render(str(output_path), preset="h264_fast")
    print(f"Rendered: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
