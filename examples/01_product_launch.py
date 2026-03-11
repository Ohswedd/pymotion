"""Product launch showcase video — 4K, 90 seconds at 30fps (2700 frames).

Demonstrates: compositions, animated text (Typewriter, WordByWord, CountUp,
LetterByLetter), particle overlays (sparkles, confetti), effects (Vignette,
Bloom), gradient backgrounds, multi-track z-ordering, CrossDissolve
transitions, LowerThird callouts, LogoReveal, and TransitionTitle.

Optionally uses stock photo / audio assets from ``examples/assets/``
(run ``python examples/download_assets.py`` first).  Falls back to
fully synthetic content when assets are not present.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from pymotion import (
    AdjustmentLayer,
    AudioClip,
    AudioClipData,
    AudioMixer,
    BlendMode,
    Bloom,
    CallToAction,
    Composition,
    CountUp,
    GradientClip,
    ImageClip,
    LetterByLetter,
    LogoReveal,
    LowerThird,
    ShapeClip,
    TextClip,
    Track,
    TransitionTitle,
    Typewriter,
    Vignette,
    WordByWord,
    confetti,
    sparkles,
)
from pymotion.utils.color import Color
from pymotion.utils.math import Vec2

logger = structlog.get_logger(__name__)

# ── Assets (optional — run download_assets.py first) ─────────────────
ASSETS = Path(__file__).parent / "assets"

# ── Constants ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 3840, 2160
FPS = 30
TOTAL_FRAMES = 2700  # 90 seconds

# Dark theme palette
BG_DARK = "#0A0A1A"
ACCENT_BLUE = "#3B82F6"
ACCENT_PURPLE = "#8B5CF6"
ACCENT_PINK = "#EC4899"
TEXT_WHITE = "#F8FAFC"
TEXT_MUTED = "#94A3B8"


def _build_composition() -> Composition:
    """Assemble the full product-launch composition."""
    comp = Composition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        duration=TOTAL_FRAMES,
        background=BG_DARK,
    )

    # ── Track 1: Background gradients ─────────────────────────────────
    bg_track = Track(name="backgrounds")

    # Hero background image (falls back to gradient if asset not downloaded)
    if (ASSETS / "product_hero.jpg").exists():
        hero_bg = ImageClip(str(ASSETS / "product_hero.jpg"), fit_mode="cover")
        hero_bg.set_duration(900).at(0).set_opacity(0.25)
        bg_track.add(hero_bg)
        logger.info("asset_loaded", file="product_hero.jpg", section="hero")

    # Opening gradient — deep purple to dark blue
    opening_grad = GradientClip(
        color_start="#0F0A2E",
        color_end="#1A103D",
        direction=135.0,
    )
    opening_grad.set_duration(900).at(0)
    bg_track.add(opening_grad)

    # Middle section — dark teal accent
    mid_grad = GradientClip(
        color_start="#0A1628",
        color_end="#0D2137",
        direction=90.0,
    )
    mid_grad.set_duration(1200).at(900)
    bg_track.add(mid_grad)

    # Closing gradient — warm dark
    close_grad = GradientClip(
        color_start="#1A0A2E",
        color_end="#2D1040",
        direction=180.0,
    )
    close_grad.set_duration(600).at(2100)
    bg_track.add(close_grad)

    comp.add_track(bg_track)

    # ── Track 2: Decorative shapes ────────────────────────────────────
    decor_track = Track(name="decorations")

    # Subtle accent line at top
    top_line = ShapeClip.rect(
        x=0,
        y=0,
        w=WIDTH,
        h=4,
        fill=ACCENT_BLUE,
    )
    top_line.set_duration(TOTAL_FRAMES).at(0).set_opacity(0.6)
    decor_track.add(top_line)

    # Accent circle — bottom-right glow
    glow_circle = ShapeClip.circle(
        cx=WIDTH - 400,
        cy=HEIGHT - 400,
        r=300,
        fill="#8B5CF620",
    )
    glow_circle.set_duration(TOTAL_FRAMES).at(0).set_opacity(0.3)
    decor_track.add(glow_circle)

    comp.add_track(decor_track)

    # ── Track 3: Logo reveal (frames 30-210) ──────────────────────────
    logo_track = Track(name="logo")

    logo = LogoReveal(
        style="grow",
        reveal_duration=60,
        logo_color=Color.parse(ACCENT_BLUE),
        logo_size=(300.0, 300.0),
    )
    logo.set_duration(180).at(30)
    logo_track.add(logo)

    comp.add_track(logo_track)

    # ── Track 4: Main text content ────────────────────────────────────
    text_track = Track(name="text")

    # Title reveal with Typewriter (frames 240-600)
    title = Typewriter(
        text="Introducing PyMotion 3.0",
        font_size=96.0,
        color=Color(1.0, 1.0, 1.0, 1.0),
        chars_per_frame=0.8,
        position=Vec2(400.0, 500.0),
    )
    title.set_duration(360).at(240)
    text_track.add(title)

    # Subtitle
    subtitle = WordByWord(
        text="The Future of Code-First Video Generation",
        font_size=48.0,
        color=Color(0.58, 0.64, 0.72, 1.0),
        frames_per_word=8,
        position=Vec2(400.0, 650.0),
    )
    subtitle.set_duration(300).at(360)
    text_track.add(subtitle)

    # ── Section 1: Feature callouts (frames 700-1200) ─────────────────
    section1_title = TransitionTitle(
        text="Powerful Features",
        style="slide_up",
        title_duration=90,
        animate_in=20,
        animate_out=20,
        font_size=72.0,
    )
    section1_title.set_duration(90).at(700)
    text_track.add(section1_title)

    features = [
        ("GPU-Accelerated Rendering", 820, "product_feature_1.jpg"),
        ("Node-Based Compositor", 940, "product_feature_2.jpg"),
        ("Real-Time Preview", 1060, "product_feature_3.jpg"),
    ]
    for feat_text, start_frame, _feat_img in features:
        feat = WordByWord(
            text=feat_text,
            font_size=64.0,
            color=Color(1.0, 1.0, 1.0, 1.0),
            frames_per_word=6,
            position=Vec2(500.0, 900.0),
        )
        feat.set_duration(100).at(start_frame)
        text_track.add(feat)

    # Feature images alongside text (optional)
    feat_img_track = Track(name="feature_images")
    for _feat_text, start_frame, feat_img in features:
        if (ASSETS / feat_img).exists():
            fimg = ImageClip(str(ASSETS / feat_img), fit_mode="contain")
            fimg.set_duration(100).at(start_frame).set_position(2400.0, 600.0)
            fimg.set_opacity(0.85)
            feat_img_track.add(fimg)
            logger.info("asset_loaded", file=feat_img, section="features")
    comp.add_track(feat_img_track)

    # ── Section 2: Statistics with CountUp (frames 1300-1900) ─────────
    section2_title = TransitionTitle(
        text="By the Numbers",
        style="fade",
        title_duration=90,
        animate_in=20,
        animate_out=20,
        font_size=72.0,
    )
    section2_title.set_duration(90).at(1300)
    text_track.add(section2_title)

    stats = [
        ("", "10", "x Faster", Vec2(400.0, 700.0), 1420),
        ("", "2185", " Tests", Vec2(1500.0, 700.0), 1480),
        ("", "89", "% Coverage", Vec2(2600.0, 700.0), 1540),
    ]
    for prefix, end_val, suffix, pos, start in stats:
        counter = CountUp(
            start_value=0.0,
            end_value=float(end_val),
            font_size=120.0,
            color=Color.parse(ACCENT_BLUE),
            prefix=prefix,
            suffix=suffix,
            position=pos,
        )
        counter.set_duration(180).at(start)
        text_track.add(counter)

    # Stat labels
    stat_labels = [
        ("Render Speed", Vec2(400.0, 860.0), 1450),
        ("Passing Tests", Vec2(1500.0, 860.0), 1510),
        ("Code Coverage", Vec2(2600.0, 860.0), 1570),
    ]
    for label, pos, start in stat_labels:
        lbl = TextClip(
            text=label,
            font_size=36.0,
            color=TEXT_MUTED,
        )
        lbl.set_duration(240).at(start).set_position(pos.x, pos.y)
        text_track.add(lbl)

    # ── Section 3: CTA (frames 2100-2700) ─────────────────────────────
    cta_intro = LetterByLetter(
        text="Start Building Today",
        font_size=80.0,
        color=Color(1.0, 1.0, 1.0, 1.0),
        frames_per_letter=2,
        position=Vec2(600.0, 800.0),
    )
    cta_intro.set_duration(240).at(2200)
    text_track.add(cta_intro)

    cta_sub = TextClip(
        text="pip install pymotion",
        font_size=48.0,
        color=ACCENT_PURPLE,
    )
    cta_sub.set_duration(300).at(2300).set_position(800.0, 1000.0)
    text_track.add(cta_sub)

    comp.add_track(text_track)

    # ── Track 5: Lower thirds ─────────────────────────────────────────
    lt_track = Track(name="lower_thirds")

    lower_thirds = [
        ("GPU Compositor", "Hardware-accelerated blending", "modern", 850, 180),
        ("Node Editor", "Visual programming interface", "corporate", 970, 180),
        ("Live Preview", "60fps interactive playback", "neon", 1090, 180),
    ]
    for name, title, style, start, dur in lower_thirds:
        lt = LowerThird(
            name=name,
            title=title,
            style=style,
            animate_in=15,
            animate_out=15,
        )
        lt.set_duration(dur).at(start)
        lt_track.add(lt)

    comp.add_track(lt_track)

    # ── Track 6: CTA button ──────────────────────────────────────────
    cta_track = Track(name="cta")

    cta_button = CallToAction(
        text="Get Started",
        sub_text="Free and Open Source",
        style="default",
        animate_in=20,
    )
    cta_button.set_duration(300).at(2400)
    cta_track.add(cta_button)

    comp.add_track(cta_track)

    # ── Track 7: Sparkle particles ────────────────────────────────────
    particle_track = Track(name="particles", blend_mode=BlendMode.ADD)

    # Sparkles during title reveal
    spark_sys = sparkles(WIDTH, HEIGHT)
    spark_clip = spark_sys.to_clip(duration=400)
    spark_clip.at(250)
    particle_track.add(spark_clip)

    # Confetti at statistics section
    confetti_sys = confetti(WIDTH, HEIGHT)
    confetti_clip = confetti_sys.to_clip(duration=300)
    confetti_clip.at(1400)
    particle_track.add(confetti_clip)

    # Final sparkles at CTA
    final_sparks = sparkles(WIDTH, HEIGHT)
    final_clip = final_sparks.to_clip(duration=300)
    final_clip.at(2400)
    particle_track.add(final_clip)

    comp.add_track(particle_track)

    # ── Track 8: Adjustment layer for global effects ──────────────────
    fx_track = Track(name="effects")

    vignette_layer = AdjustmentLayer()
    vignette_layer.add_effect(Vignette(strength=0.4, radius=0.85, feather=0.35))
    vignette_layer.set_duration(TOTAL_FRAMES).at(0)
    fx_track.add(vignette_layer)

    bloom_layer = AdjustmentLayer()
    bloom_layer.add_effect(Bloom(radius=12.0, strength=0.3, threshold=210.0))
    bloom_layer.set_duration(TOTAL_FRAMES).at(0)
    fx_track.add(bloom_layer)

    comp.add_track(fx_track)

    return comp


def main() -> None:
    """Build and render the product launch video."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "01_product_launch.mp4"

    logger.info("building_composition", width=WIDTH, height=HEIGHT, fps=FPS)
    comp = _build_composition()

    # ── Background music (optional) ────────────────────────────────────
    music_path = ASSETS / "music_corporate.wav"
    if music_path.exists():
        try:
            music = AudioClip(str(music_path), volume=0.4)
            music.fade_in(1.0).fade_out(2.0)
            mixer = AudioMixer(sample_rate=48000)
            clip_data = AudioClipData(
                samples=music.get_samples(),
                start_sample=0,
            )
            mixer.add(clip_data, track="music")
            mixer.render()
            logger.info("audio_prepared", file="music_corporate.wav")
        except Exception:
            logger.warning("audio_skipped", reason="failed to load music_corporate.wav")

    logger.info("rendering", output=str(output_path))
    comp.render(str(output_path), preset="h264_1080p")
    logger.info("render_complete", output=str(output_path))


if __name__ == "__main__":
    main()
