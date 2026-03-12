"""EX02 — Text & Typography Showcase.

Use-case: An animated typography reel — one text preset per scene,
labeled and shown at display scale.

Features exercised:
  TextClip (font, size, color, letter_spacing, line_height, align,
    max_width, stroke_color, stroke_width, shadow),
  Shadow, download_google_font,
  Typewriter, WordByWord, LetterByLetter, Scramble, ScrambleText,
  KineticText, SplitReveal, CountUp, CountDown, GlitchText,
  Saturation, Glow

Output: 1920x1080, 30fps, 50s, preset h264_fast -> outputs/02_typography.mp4
"""

from __future__ import annotations

from pathlib import Path

import pymotion as pm
from pymotion.design.tokens import ACCENT, CHART_COLORS, NEUTRAL, STATUS, get_theme

ASSETS = Path(__file__).parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

theme = get_theme()
WHITE = NEUTRAL.n50
CYAN = ACCENT.a300
CORAL = CHART_COLORS[1]  # pink
GOLD = STATUS.warning

SEC = 150  # 5s per section at 30fps
TOTAL = SEC * 10  # 10 sections = 50s


def _add_label(track: pm.Track, text: str, offset: int, dur: int) -> None:
    """Add a small preset name label to the bottom-right corner."""
    lbl = pm.TextClip(text=text, size=14, color=theme.muted)
    lbl.set_duration(dur).at(offset).set_position(1800, 1040).set_opacity(0.5)
    track.clips.append(lbl)


def main() -> None:
    # ── Download Google Font (test FontLoader) ────────────────────────────
    try:
        roboto_path = pm.download_google_font("Roboto", weight=400)
        print(f"Google Font downloaded: {roboto_path}")
    except Exception as e:
        print(f"Google Font download skipped: {e}")

    inter_regular = str(ASSETS / "Inter-Regular.ttf")
    inter_bold = str(ASSETS / "Inter-Bold.ttf")

    comp = pm.Composition(width=1920, height=1080, fps=30, duration=TOTAL)

    # ── Background ────────────────────────────────────────────────────────
    bg_track = pm.Track(name="bg")
    bg = pm.GradientClip(
        color_start=theme.background,
        color_end=theme.surface,
        direction=135.0,
    )
    bg.set_duration(TOTAL)
    bg.add_effect(pm.Saturation(value=1.3))
    bg_track.clips.append(bg)
    comp.tracks.append(bg_track)

    # ── SCENE 1: TextClip basics ─────────────────────────────────────────
    # SCENE: basics | 150f | Primary: title + subtitle | Secondary: stroke/shadow demos
    # ENTRY: 0-15 | HOLD: 15-130 | EXIT: 130-150
    offset = 0
    s1 = pm.Track(name="s1_basics")
    # INCREASED title size 72→96px: principle 6, type does the work
    title = pm.TextClip(
        "Typography",
        font=inter_bold,
        size=96.0,
        color=theme.text,
        letter_spacing=4.0,
        line_height=1.2,
        align="center",
    )
    title.set_duration(SEC).at(offset).set_position(960, 400)
    s1.clips.append(title)
    subtitle = pm.TextClip(
        "Type styles and animation presets",
        font=inter_regular,
        size=24.0,
        color=theme.muted,
        align="center",
    )
    subtitle.set_duration(SEC).at(offset).set_position(960, 520)
    s1.clips.append(subtitle)
    # Stroke + shadow demos below — secondary, smaller
    stroked = pm.TextClip(
        "STROKE",
        font=inter_bold,
        size=40.0,
        color="#00000000",
        stroke_color=ACCENT.a500,
        stroke_width=2.0,
        align="center",
    )
    stroked.set_duration(SEC).at(offset).set_position(700, 700)
    s1.clips.append(stroked)
    shadowed = pm.TextClip(
        "SHADOW",
        font=inter_bold,
        size=40.0,
        color=theme.text,
        shadow=pm.Shadow(
            color=pm.Color(0.0, 0.0, 0.0, 0.7),
            offset_x=4.0,
            offset_y=4.0,
            blur=8.0,
        ),
        align="center",
    )
    shadowed.set_duration(SEC).at(offset).set_position(1220, 700)
    s1.clips.append(shadowed)
    _add_label(s1, "TextClip", offset, SEC)
    comp.tracks.append(s1)
    print("S1: TextClip basics (title, stroke, shadow)")

    # ── SCENE 2: Typewriter ──────────────────────────────────────────────
    # SCENE: typewriter | 150f | Primary: typing text | Secondary: label
    offset = SEC
    s2 = pm.Track(name="s2_typewriter")
    # INCREASED size 40→56px: principle 6
    tw = pm.Typewriter(
        text="The quick brown fox jumps over the lazy dog.",
        font_size=56.0,
        color=WHITE,
        cursor=True,
        chars_per_frame=0.8,
        position=pm.Vec2(200, 486),
    )
    tw.set_duration(SEC).at(offset)
    s2.clips.append(tw)
    _add_label(s2, "Typewriter", offset, SEC)
    comp.tracks.append(s2)
    print("S2: Typewriter")

    # ── SCENE 3: WordByWord ──────────────────────────────────────────────
    # SCENE: wordbyword | 150f | Primary: appearing words | Secondary: label
    offset = SEC * 2
    s3 = pm.Track(name="s3_wordbyword")
    # INCREASED size 44→56px: principle 6
    wbw = pm.WordByWord(
        text="Every word appears one at a time",
        font_size=56.0,
        color=CYAN,
        frames_per_word=12,
        position=pm.Vec2(200, 486),
    )
    wbw.set_duration(SEC).at(offset)
    s3.clips.append(wbw)
    _add_label(s3, "WordByWord", offset, SEC)
    comp.tracks.append(s3)
    print("S3: WordByWord")

    # ── SCENE 4: LetterByLetter ──────────────────────────────────────────
    # SCENE: letterbyletter | 150f | Primary: appearing letters | Secondary: label
    offset = SEC * 3
    s4 = pm.Track(name="s4_letterbyletter")
    lbl = pm.LetterByLetter(
        text="LETTER BY LETTER",
        font_size=64.0,
        color=CORAL,
        frames_per_letter=4,
        position=pm.Vec2(400, 486),
    )
    lbl.set_duration(SEC).at(offset)
    s4.clips.append(lbl)
    _add_label(s4, "LetterByLetter", offset, SEC)
    comp.tracks.append(s4)
    print("S4: LetterByLetter")

    # ── SCENE 5: Scramble ────────────────────────────────────────────────
    # SCENE: scramble | 150f | Primary: decoding text | Secondary: label
    offset = SEC * 4
    s5 = pm.Track(name="s5_scramble")
    # INCREASED size 48→64px: principle 6, scramble effect must be clearly visible
    scr = pm.Scramble(
        text="DECODE THIS MESSAGE",
        font_size=64.0,
        color=GOLD,
        scramble_frames=8,
        position=pm.Vec2(400, 486),
        seed=99,
    )
    scr.set_duration(SEC).at(offset)
    s5.clips.append(scr)
    _add_label(s5, "Scramble", offset, SEC)
    print(f"ScrambleText alias: {pm.ScrambleText is pm.Scramble}")
    comp.tracks.append(s5)
    print("S5: Scramble")

    # ── SCENE 6: KineticText ────────────────────────────────────────────
    # SCENE: kinetic | 150f | Primary: moving words | Secondary: label
    offset = SEC * 5
    s6 = pm.Track(name="s6_kinetic")
    kin = pm.KineticText(
        text="MOVE EVERY WORD",
        font_size=64.0,
        color=WHITE,
        frames_per_word=18,
        position=pm.Vec2(400, 486),
    )
    kin.set_duration(SEC).at(offset)
    s6.clips.append(kin)
    _add_label(s6, "KineticText", offset, SEC)
    comp.tracks.append(s6)
    print("S6: KineticText")

    # ── SCENE 7: SplitReveal ────────────────────────────────────────────
    # SCENE: splitreveal | 150f | Primary: splitting text | Secondary: label
    offset = SEC * 6
    s7 = pm.Track(name="s7_splitreveal")
    sr = pm.SplitReveal(
        text="SPLIT REVEAL",
        font_size=72.0,
        color=CYAN,
        reveal_frames=25,
        position=pm.Vec2(600, 486),
    )
    sr.set_duration(SEC).at(offset)
    s7.clips.append(sr)
    _add_label(s7, "SplitReveal", offset, SEC)
    comp.tracks.append(s7)
    print("S7: SplitReveal")

    # ── SCENE 8: CountUp ────────────────────────────────────────────────
    # SCENE: countup | 150f | Primary: counting number | Secondary: label
    # SEPARATED from CountDown: principle 1, one thing at a time
    offset = SEC * 7
    s8 = pm.Track(name="s8_countup")
    cu = pm.CountUp(
        start_value=0.0,
        end_value=100.0,
        font_size=96.0,
        color=GOLD,
        suffix="%",
        decimals=0,
        position=pm.Vec2(960, 486),
    )
    cu.set_duration(SEC).at(offset)
    s8.clips.append(cu)
    _add_label(s8, "CountUp", offset, SEC)
    comp.tracks.append(s8)
    print("S8: CountUp — 96px, centered")

    # ── SCENE 9: CountDown ──────────────────────────────────────────────
    # SCENE: countdown | 150f | Primary: counting number | Secondary: label
    offset = SEC * 8
    s9 = pm.Track(name="s9_countdown")
    cd = pm.CountDown(
        start_value=10.0,
        end_value=0.0,
        font_size=96.0,
        color=CORAL,
        prefix="T-",
        decimals=0,
        position=pm.Vec2(960, 486),
    )
    cd.set_duration(SEC).at(offset)
    s9.clips.append(cd)
    _add_label(s9, "CountDown", offset, SEC)
    comp.tracks.append(s9)
    print("S9: CountDown — 96px, centered")

    # ── SCENE 10: GlitchText ────────────────────────────────────────────
    # SCENE: glitch | 150f | Primary: glitching text | Secondary: label
    offset = SEC * 9
    s10 = pm.Track(name="s10_glitch")
    gt = pm.GlitchText(
        text="SYSTEM ERROR",
        font_size=72.0,
        color=CORAL,
        glitch_intensity=0.5,
        position=pm.Vec2(600, 486),
        seed=7,
    )
    gt.set_duration(SEC).at(offset)
    gt.add_effect(pm.Glow(radius=8.0, strength=0.6))
    s10.clips.append(gt)
    _add_label(s10, "GlitchText + Glow", offset, SEC)
    comp.tracks.append(s10)
    print("S10: GlitchText + Glow")

    # ── Render ────────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "02_typography.mp4"
    comp.render(str(output_path), preset="h264_fast")
    print(f"Rendered: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
