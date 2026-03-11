"""Example 10 — AI-Powered Editing Showcase.

Demonstrates v2.0 AI features with real method calls:

- **No-deps helpers** (pure NumPy, work out of the box):
  SceneDetector, SilenceRemover, HighlightDetector,
  ContentAwareCrop, AutoColor, AutoEdit, FaceDetector,
  FaceTracker, FaceBlur

- **Optional-deps effects** (need pip install "pymotion-studio[ai]"):
  RemoveBackground, ReplaceBackground, ObjectSegmentation,
  RemoveObject, ExtendFrame, Upscale, Denoise, Deblur,
  FrameInterpolation, ColorizeClip, VoiceConversion,
  MusicGeneration, SoundFXGeneration

Niche: AI-assisted post-production workflows
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from pymotion import (
    AutoColor,
    AutoEdit,
    ColorClip,
    Composition,
    ContentAwareCrop,
    Deblur,
    Denoise,
    ExtendFrame,
    FaceBlur,
    FaceDetector,
    FaceTracker,
    HighlightDetector,
    LowerThird,
    MusicGeneration,
    ObjectSegmentation,
    RemoveBackground,
    RemoveObject,
    ReplaceBackground,
    SceneDetector,
    SilenceRemover,
    SoundFXGeneration,
    TextClip,
    Track,
    Upscale,
    VoiceConversion,
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FPS = 30
WIDTH, HEIGHT = 640, 480


def _make_clip(
    num_frames: int = 90,
    *,
    varied: bool = True,
) -> MagicMock:
    """Create a mock clip with synthetic frames for analysis demos.

    When ``varied=True`` each frame is slightly different so detectors
    can find scene changes and motion.
    """
    clip = MagicMock()
    clip.start = 0
    clip.end = num_frames
    clip.width = WIDTH
    clip.height = HEIGHT
    clip.fps = FPS

    rng = np.random.default_rng(42)

    if varied:
        # Pre-generate distinct frames so detectors see real changes
        frames = [
            rng.integers(0, 255, (HEIGHT, WIDTH, 4), dtype=np.uint8) for _ in range(num_frames)
        ]
        clip.render_frame = MagicMock(
            side_effect=lambda ctx, **kw: frames[
                min(getattr(ctx, "local_frame", 0), len(frames) - 1)
            ]
        )
    else:
        static = rng.integers(0, 255, (HEIGHT, WIDTH, 4), dtype=np.uint8)
        clip.render_frame = MagicMock(return_value=static)

    return clip


# ─────────────────────────────────────────────────────────────────────
# 1. Rendered composition (always works)
# ─────────────────────────────────────────────────────────────────────


def demo_ai_showcase_video() -> None:
    """Render a 1080p composition listing all AI features."""
    comp = Composition(1920, 1080, fps=30, duration=150)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#0D1117").set_duration(150)
    bg_track.add(bg)

    title_track = Track(name="title")
    title = TextClip("AI-Powered Effects", font="Arial", size=64.0, color="#FFFFFF")
    title.set_duration(150).set_position(560.0, 40.0)
    title_track.add(title)

    cards_track = Track(name="cards")
    for i, name in enumerate(
        [
            "RemoveBackground",
            "ReplaceBackground",
            "ObjectSegmentation",
            "RemoveObject",
            "ExtendFrame",
        ]
    ):
        label = TextClip(f"* {name}", font="Arial", size=32.0, color="#58A6FF")
        label.set_duration(120).at(15).set_position(200.0, 180.0 + i * 60.0)
        cards_track.add(label)

    for i, name in enumerate(
        ["Upscale (2x/4x)", "Denoise", "Deblur", "FrameInterpolation", "ColorizeClip"]
    ):
        label = TextClip(f"* {name}", font="Arial", size=32.0, color="#7EE787")
        label.set_duration(120).at(15).set_position(1000.0, 180.0 + i * 60.0)
        cards_track.add(label)

    lt_track = Track(name="lower_third")
    lt = LowerThird(
        name="PyMotion v2.0",
        title="AI-Powered Features",
        style="modern",
        animate_in=15,
        animate_out=15,
    )
    lt.set_duration(90).at(30)
    lt_track.add(lt)

    helpers_track = Track(name="helpers")
    for i, name in enumerate(
        [
            "SceneDetector",
            "SilenceRemover / HighlightDetector",
            "ContentAwareCrop / AutoColor / AutoEdit",
            "FaceDetector / FaceTracker / FaceBlur",
            "VoiceConversion / MusicGeneration / SoundFXGeneration",
        ]
    ):
        label = TextClip(f"-> {name}", font="Arial", size=26.0, color="#D2A8FF")
        label.set_duration(100).at(30).set_position(200.0, 560.0 + i * 48.0)
        helpers_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(title_track)
    comp.add_track(cards_track)
    comp.add_track(lt_track)
    comp.add_track(helpers_track)
    comp.render(str(OUTPUT_DIR / "10a_ai_showcase.mp4"), preset="h264_1080p")


# ─────────────────────────────────────────────────────────────────────
# 2. No-deps helpers — real method calls, pure NumPy
# ─────────────────────────────────────────────────────────────────────


def demo_scene_detection() -> None:
    """Detect scene boundaries in a synthetic clip."""
    clip = _make_clip(90)
    detector = SceneDetector(clip=clip, threshold=0.3)
    boundaries = detector.detect()
    print(f"  SceneDetector: found {len(boundaries)} scene boundaries at frames {boundaries[:8]}")


def demo_silence_removal() -> None:
    """Detect silent segments."""
    clip = _make_clip(90)
    remover = SilenceRemover(clip=clip, threshold_db=-40.0, min_silence_sec=0.3)
    silent = remover.detect_silence()
    non_silent = remover.remove()
    print(f"  SilenceRemover: {len(silent)} silent segments, {len(non_silent)} kept segments")


def demo_highlight_detection() -> None:
    """Find the most visually interesting segments."""
    clip = _make_clip(90)
    detector = HighlightDetector(clip=clip, criteria="motion", top_n=3)
    highlights = detector.detect()
    print(f"  HighlightDetector: top {len(highlights)} highlights = {highlights}")


def demo_content_aware_crop() -> None:
    """AI reframing to a different aspect ratio."""
    clip = _make_clip(30)
    cropper = ContentAwareCrop(clip=clip, target_ratio="9:16", smoothing=5)
    regions = cropper.analyze()
    print(f"  ContentAwareCrop: {len(regions)} crop regions, first = {regions[0]}")


def demo_auto_color() -> None:
    """One-click color correction analysis."""
    clip = _make_clip(30)
    corrector = AutoColor(clip=clip, strength=0.8)
    corrections = corrector.analyze()
    print(f"  AutoColor: corrections = {corrections}")


def demo_auto_edit() -> None:
    """AI-powered automatic editing from multiple clips."""
    clips = [_make_clip(30) for _ in range(3)]
    editor = AutoEdit(clips=clips, style="fast", target_duration=60)
    segments = editor.edit()
    print(f"  AutoEdit: assembled {len(segments)} segments = {segments}")


def demo_face_detection() -> None:
    """Detect faces in a clip (requires OpenCV)."""
    clip = _make_clip(30)
    detector = FaceDetector(clip=clip, method="haar", min_confidence=0.5)
    try:
        faces = detector.detect()
        total_faces = sum(len(v) for v in faces.values())
        print(f"  FaceDetector: scanned {len(faces)} frames, found {total_faces} face detections")
    except ImportError:
        print("  FaceDetector: skipped (requires opencv-python)")


def demo_face_tracking() -> None:
    """Track faces across frames (requires OpenCV)."""
    clip = _make_clip(30)
    tracker = FaceTracker(clip=clip, max_distance=100.0)
    try:
        tracks = tracker.track()
        print(f"  FaceTracker: tracking {len(tracks)} face identities across frames")
    except ImportError:
        print("  FaceTracker: skipped (requires opencv-python)")


def demo_face_blur() -> None:
    """Get blur regions for privacy anonymization (requires OpenCV)."""
    clip = _make_clip(30)
    blurrer = FaceBlur(clip=clip, strength=5, method="haar")
    try:
        regions = blurrer.get_blur_regions()
        total = sum(len(v) for v in regions.values())
        print(f"  FaceBlur: {total} face regions to blur across {len(regions)} frames")
    except ImportError:
        print("  FaceBlur: skipped (requires opencv-python)")


# ─────────────────────────────────────────────────────────────────────
# 3. Optional-deps features — try/except with clear error messages
# ─────────────────────────────────────────────────────────────────────


def demo_ai_effects() -> None:
    """Try applying AI effects (need external packages)."""
    from pymotion.clip.base import RenderContext, Resolution, TimeRange

    frame = np.random.default_rng(42).integers(0, 255, (64, 64, 4), dtype=np.uint8)
    ctx = RenderContext(
        frame=0,
        fps=30,
        resolution=Resolution(64, 64),
        time_range=TimeRange(0, 30),
        local_frame=0,
        progress=0.0,
    )

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:30, 10:30] = 255
    mock_bg = ColorClip(color="#003366")
    mock_bg.set_duration(30)

    effects = [
        ("RemoveBackground", RemoveBackground(model="u2net")),
        ("ReplaceBackground", ReplaceBackground(new_bg=mock_bg, model="u2net")),
        ("ObjectSegmentation", ObjectSegmentation(prompt="red object")),
        ("RemoveObject", RemoveObject(mask=mask)),
        ("ExtendFrame", ExtendFrame(direction="right", amount=20)),
        ("Upscale", Upscale(factor=2)),
        ("Denoise", Denoise(strength=0.5)),
        ("Deblur", Deblur(strength=0.5)),
    ]

    for name, effect in effects:
        try:
            result = effect.apply(frame.copy(), ctx)
            print(f"  {name}: applied! output shape={result.shape}")
        except ImportError as e:
            pkg = str(e).split(" is required")[0] if "is required" in str(e) else str(e)
            print(f"  {name}: skipped ({pkg})")


def demo_ai_audio() -> None:
    """Try AI audio generation (needs torch + transformers)."""
    clip = _make_clip(30)
    generators = [
        (
            "VoiceConversion",
            lambda: VoiceConversion(
                clip=clip, target_voice_sample="voice.wav", strength=0.8
            ).convert(),
        ),
        (
            "MusicGeneration",
            lambda: MusicGeneration(prompt="ambient piano", duration=5.0, tempo=90).generate(),
        ),
        (
            "SoundFXGeneration",
            lambda: SoundFXGeneration(description="rain on window", duration=2.0).generate(),
        ),
    ]

    for name, gen_fn in generators:
        try:
            audio = gen_fn()
            print(f"  {name}: generated {audio.shape[0]} samples, shape={audio.shape}")
        except ImportError as e:
            pkg = str(e).split(" is required")[0] if "is required" in str(e) else str(e)
            print(f"  {name}: skipped ({pkg})")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # 1. Render showcase video
    demo_ai_showcase_video()

    # 2. No-deps helpers — these always work
    print("\n=== No-Deps AI Helpers (pure NumPy) ===")
    demo_scene_detection()
    demo_silence_removal()
    demo_highlight_detection()
    demo_content_aware_crop()
    demo_auto_color()
    demo_auto_edit()
    demo_face_detection()
    demo_face_tracking()
    demo_face_blur()

    # 3. Optional-deps — try each, report what's available
    print("\n=== Optional-Deps AI Effects ===")
    demo_ai_effects()

    print("\n=== Optional-Deps AI Audio ===")
    demo_ai_audio()

    print("\nDone! All no-deps features ran successfully.")
    print("Install optional AI packages for full functionality:")
    print('  pip install "pymotion-studio[ai]"')
