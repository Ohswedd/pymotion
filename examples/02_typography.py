"""EX02 — Text & Typography Showcase.

Use-case: An animated typography reel demonstrating a design system's
type styles in motion.

Features exercised:
  TextClip (font, size, color, letter_spacing, line_height, align,
    max_width, stroke_color, stroke_width, shadow),
  Shadow, download_google_font,
  Typewriter, WordByWord, LetterByLetter, Scramble, ScrambleText,
  KineticText, SplitReveal, CountUp, CountDown, GlitchText,
  Saturation, Glow

Output: 1920x1080, 30fps, 45s, preset h264_fast -> outputs/02_typography.mp4
Estimated render time: ~60s
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

WHITE = pm.Color(1.0, 1.0, 1.0, 1.0)
CYAN = pm.Color(0.2, 0.8, 1.0, 1.0)
CORAL = pm.Color(1.0, 0.4, 0.3, 1.0)
GOLD = pm.Color(1.0, 0.85, 0.2, 1.0)

SECTION_DUR = 150  # 5s per section at 30fps
TOTAL_DUR = SECTION_DUR * 9  # 9 sections = 45s


def main() -> None:
    # ── Download Google Font (test FontLoader) ────────────────────────────
    try:
        roboto_path = pm.download_google_font("Roboto", weight=400)
        print(f"Google Font downloaded: {roboto_path}")
    except Exception as e:
        print(f"Google Font download skipped: {e}")

    # ── Font paths ────────────────────────────────────────────────────────
    inter_regular = str(ASSETS / "Inter-Regular.ttf")
    inter_bold = str(ASSETS / "Inter-Bold.ttf")

    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL_DUR)

    # ── Background ────────────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.GradientClip(
        color_start="#0a0a1a",
        color_end="#1a0a2e",
        direction=135.0,
    )
    bg.set_duration(TOTAL_DUR)
    bg.add_effect(pm.Saturation(value=1.3))
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── Section 1: TextClip basics (font, size, color, alignment) ─────────
    sec1_track = pm.Track(name="sec1_basics")
    offset = 0

    title = pm.TextClip(
        "Typography",
        font=inter_bold,
        size=72.0,
        color="#FFFFFF",
        letter_spacing=4.0,
        line_height=1.4,
        align="center",
    )
    title.set_duration(SECTION_DUR).at(offset).set_position(960, 300)
    sec1_track.clips.append(title)

    subtitle = pm.TextClip(
        "A showcase of type styles and text animation presets",
        font=inter_regular,
        size=28.0,
        color="#AAAACC",
        align="center",
        max_width=800,
    )
    subtitle.set_duration(SECTION_DUR).at(offset).set_position(960, 440)
    sec1_track.clips.append(subtitle)

    # Stroke text
    stroked = pm.TextClip(
        "STROKE",
        font=inter_bold,
        size=64.0,
        color="#00000000",
        stroke_color="#e94560",
        stroke_width=3.0,
        align="center",
    )
    stroked.set_duration(SECTION_DUR).at(offset).set_position(960, 600)
    sec1_track.clips.append(stroked)

    # Shadow text
    shadowed = pm.TextClip(
        "SHADOW",
        font=inter_bold,
        size=64.0,
        color="#FFFFFF",
        shadow=pm.Shadow(
            color=pm.Color(0.0, 0.0, 0.0, 0.7),
            offset_x=4.0,
            offset_y=4.0,
            blur=8.0,
        ),
        align="center",
    )
    shadowed.set_duration(SECTION_DUR).at(offset).set_position(960, 750)
    sec1_track.clips.append(shadowed)

    comp.tracks.append(sec1_track)

    # ── Section 2: Typewriter ─────────────────────────────────────────────
    offset = SECTION_DUR
    sec2_track = pm.Track(name="sec2_typewriter")
    tw = pm.Typewriter(
        text="The quick brown fox jumps over the lazy dog.",
        font_size=40.0,
        color=WHITE,
        cursor=True,
        chars_per_frame=0.8,
        position=pm.Vec2(200, 500),
    )
    tw.set_duration(SECTION_DUR).at(offset)
    sec2_track.clips.append(tw)
    comp.tracks.append(sec2_track)

    # ── Section 3: WordByWord ─────────────────────────────────────────────
    offset = SECTION_DUR * 2
    sec3_track = pm.Track(name="sec3_wordbyword")
    wbw = pm.WordByWord(
        text="Every word appears one at a time with smooth timing",
        font_size=44.0,
        color=CYAN,
        frames_per_word=12,
        position=pm.Vec2(200, 500),
    )
    wbw.set_duration(SECTION_DUR).at(offset)
    sec3_track.clips.append(wbw)
    comp.tracks.append(sec3_track)

    # ── Section 4: LetterByLetter ─────────────────────────────────────────
    offset = SECTION_DUR * 3
    sec4_track = pm.Track(name="sec4_letterbyletter")
    lbl = pm.LetterByLetter(
        text="LETTER BY LETTER",
        font_size=56.0,
        color=CORAL,
        frames_per_letter=4,
        position=pm.Vec2(400, 500),
    )
    lbl.set_duration(SECTION_DUR).at(offset)
    sec4_track.clips.append(lbl)
    comp.tracks.append(sec4_track)

    # ── Section 5: Scramble ───────────────────────────────────────────────
    offset = SECTION_DUR * 4
    sec5_track = pm.Track(name="sec5_scramble")
    scr = pm.Scramble(
        text="DECODE THIS MESSAGE",
        font_size=48.0,
        color=GOLD,
        scramble_frames=8,
        position=pm.Vec2(400, 500),
        seed=99,
    )
    scr.set_duration(SECTION_DUR).at(offset)
    sec5_track.clips.append(scr)
    # Verify ScrambleText alias
    print(f"ScrambleText alias: {pm.ScrambleText is pm.Scramble}")
    comp.tracks.append(sec5_track)

    # ── Section 6: KineticText ────────────────────────────────────────────
    offset = SECTION_DUR * 5
    sec6_track = pm.Track(name="sec6_kinetic")
    kin = pm.KineticText(
        text="MOVE EVERY WORD INDEPENDENTLY",
        font_size=52.0,
        color=WHITE,
        frames_per_word=18,
        position=pm.Vec2(300, 500),
    )
    kin.set_duration(SECTION_DUR).at(offset)
    sec6_track.clips.append(kin)
    comp.tracks.append(sec6_track)

    # ── Section 7: SplitReveal ────────────────────────────────────────────
    offset = SECTION_DUR * 6
    sec7_track = pm.Track(name="sec7_splitreveal")
    sr = pm.SplitReveal(
        text="SPLIT REVEAL",
        font_size=64.0,
        color=CYAN,
        reveal_frames=25,
        position=pm.Vec2(600, 500),
    )
    sr.set_duration(SECTION_DUR).at(offset)
    sec7_track.clips.append(sr)
    comp.tracks.append(sec7_track)

    # ── Section 8: CountUp + CountDown ────────────────────────────────────
    offset = SECTION_DUR * 7
    sec8_track = pm.Track(name="sec8_counters")
    cu = pm.CountUp(
        start_value=0.0,
        end_value=100.0,
        font_size=72.0,
        color=GOLD,
        suffix="%",
        decimals=0,
        position=pm.Vec2(700, 400),
    )
    cu.set_duration(SECTION_DUR).at(offset)
    sec8_track.clips.append(cu)

    cd = pm.CountDown(
        start_value=10.0,
        end_value=0.0,
        font_size=72.0,
        color=CORAL,
        prefix="T-",
        decimals=0,
        position=pm.Vec2(700, 650),
    )
    cd.set_duration(SECTION_DUR).at(offset)
    sec8_track.clips.append(cd)
    comp.tracks.append(sec8_track)

    # ── Section 9: GlitchText ─────────────────────────────────────────────
    offset = SECTION_DUR * 8
    sec9_track = pm.Track(name="sec9_glitch")
    gt = pm.GlitchText(
        text="SYSTEM ERROR",
        font_size=64.0,
        color=CORAL,
        glitch_intensity=0.5,
        position=pm.Vec2(550, 500),
        seed=7,
    )
    gt.set_duration(SECTION_DUR).at(offset)
    gt.add_effect(pm.Glow(radius=8.0, strength=0.6))
    sec9_track.clips.append(gt)
    comp.tracks.append(sec9_track)

    # ── Export audit frames ───────────────────────────────────────────────
    audit_dir = Path(__file__).parent.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    for sec in range(9):
        mid = sec * SECTION_DUR + SECTION_DUR // 2
        comp.export_frame(frame=mid, output=audit_dir / f"ex02_sec{sec + 1}.png")
    print("Audit frames exported to audit/")

    # ── Render ────────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "02_typography.mp4"
    comp.render(str(output_path), preset="h264_fast")
    print(f"Rendered: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
