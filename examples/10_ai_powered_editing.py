"""Example 10 — AI-Powered Editing Showcase.

Demonstrates v2.0 AI features: background removal, upscaling,
denoising, scene detection, face detection, auto color correction,
AI music generation, and sound effect synthesis.

All AI features require optional dependencies:
    pip install "pymotion-studio[ai]"

This example uses mocked/synthetic data so it runs without AI
dependencies installed — it demonstrates the API surface and
integration patterns.

Niche: AI-assisted post-production workflows
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pymotion import (
    AutoColor,
    ColorClip,
    Composition,
    ContentAwareCrop,
    Deblur,
    Denoise,
    ExtendFrame,
    FaceBlur,
    FaceDetector,
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


def demo_ai_effects_showcase() -> None:
    """Render a composition showcasing AI effect labels."""
    comp = Composition(1920, 1080, fps=30, duration=150)

    bg_track = Track(name="bg")
    bg = ColorClip(color="#0D1117").set_duration(150)
    bg_track.add(bg)

    # Title
    title_track = Track(name="title")
    title = TextClip(
        "AI-Powered Effects",
        font="Arial",
        size=64.0,
        color="#FFFFFF",
    )
    title.set_duration(150).set_position(560.0, 40.0)
    title_track.add(title)

    # Effect cards — two columns of labels
    cards_track = Track(name="cards")
    effects_left = [
        "RemoveBackground",
        "ReplaceBackground",
        "ObjectSegmentation",
        "RemoveObject",
        "ExtendFrame",
    ]
    effects_right = [
        "Upscale (2×/4×)",
        "Denoise",
        "Deblur",
        "FrameInterpolation",
        "ColorizeClip",
    ]

    for i, name in enumerate(effects_left):
        label = TextClip(f"• {name}", font="Arial", size=32.0, color="#58A6FF")
        label.set_duration(120).at(15).set_position(200.0, 180.0 + i * 60.0)
        cards_track.add(label)

    for i, name in enumerate(effects_right):
        label = TextClip(f"• {name}", font="Arial", size=32.0, color="#7EE787")
        label.set_duration(120).at(15).set_position(1000.0, 180.0 + i * 60.0)
        cards_track.add(label)

    # Lower third
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

    # Helper labels
    helpers_track = Track(name="helpers")
    helpers = [
        "SceneDetector",
        "SilenceRemover",
        "HighlightDetector",
        "ContentAwareCrop",
        "AutoColor / AutoEdit",
        "FaceDetector / FaceTracker / FaceBlur",
        "VoiceConversion",
        "MusicGeneration / SoundFXGeneration",
    ]
    for i, name in enumerate(helpers):
        label = TextClip(f"→ {name}", font="Arial", size=26.0, color="#D2A8FF")
        label.set_duration(100).at(30).set_position(200.0, 540.0 + i * 48.0)
        helpers_track.add(label)

    comp.add_track(bg_track)
    comp.add_track(title_track)
    comp.add_track(cards_track)
    comp.add_track(lt_track)
    comp.add_track(helpers_track)
    comp.render(str(OUTPUT_DIR / "10a_ai_showcase.mp4"), preset="h264_1080p")


def demo_effect_api_patterns() -> None:
    """Show how AI effects are instantiated (no AI deps required)."""
    # --- Background & Object Manipulation ---
    print("=== AI Effect Instantiation ===")

    bg_removal = RemoveBackground(model="u2net")
    print(f"RemoveBackground: model={bg_removal.model}")

    from pymotion import ColorClip as _ColorClip

    mock_bg = _ColorClip(color="#0000FF")
    mock_bg.set_duration(30)
    bg_replace = ReplaceBackground(new_bg=mock_bg, model="u2net")
    print(f"ReplaceBackground: model={bg_replace.model}")

    obj_seg = ObjectSegmentation(prompt="the red car")
    print(f"ObjectSegmentation: prompt={obj_seg.prompt!r}")

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[10:30, 10:30] = 255
    obj_remove = RemoveObject(mask=mask)
    print(f"RemoveObject: mask_shape={obj_remove.mask.shape}")

    extend = ExtendFrame(direction="right", amount=100)
    print(f"ExtendFrame: direction={extend.direction}, amount={extend.amount}")

    # --- Enhancement & Restoration ---
    upscale = Upscale(factor=2)
    print(f"Upscale: factor={upscale.factor}")

    denoise = Denoise(strength=0.5)
    print(f"Denoise: strength={denoise.strength}")

    deblur = Deblur(strength=0.5)
    print(f"Deblur: strength={deblur.strength}")


def demo_helper_api_patterns() -> None:
    """Show how AI helpers are instantiated with mock clips."""
    from unittest.mock import MagicMock

    print("\n=== AI Helper Instantiation ===")

    # Create a mock clip for demonstration
    mock_clip = MagicMock()
    mock_clip.start = 0
    mock_clip.end = 150
    mock_clip.width = 1920
    mock_clip.height = 1080
    mock_clip.fps = 30

    rng = np.random.default_rng(42)
    mock_clip.render_frame = MagicMock(
        return_value=rng.integers(0, 255, (1080, 1920, 4), dtype=np.uint8)
    )

    # Scene detection
    scene_det = SceneDetector(clip=mock_clip, threshold=0.3)
    print(f"SceneDetector: threshold={scene_det.threshold}")

    # Silence removal
    silence_rem = SilenceRemover(clip=mock_clip, threshold_db=-40.0, min_silence_sec=0.5)
    print(f"SilenceRemover: threshold_db={silence_rem.threshold_db}")

    # Highlight detection
    highlight_det = HighlightDetector(clip=mock_clip, criteria="motion", top_n=5)
    print(f"HighlightDetector: criteria={highlight_det.criteria}, top_n={highlight_det.top_n}")

    # Content-aware crop
    crop = ContentAwareCrop(clip=mock_clip, target_ratio="9:16", smoothing=10)
    print(f"ContentAwareCrop: target_ratio={crop.target_ratio}")

    # Auto color
    auto_color = AutoColor(clip=mock_clip, strength=0.8)
    print(f"AutoColor: strength={auto_color.strength}")

    # Face detection
    face_det = FaceDetector(clip=mock_clip, min_confidence=0.7)
    print(f"FaceDetector: min_confidence={face_det.min_confidence}")

    # Face blur
    face_blur = FaceBlur(clip=mock_clip, strength=5)
    print(f"FaceBlur: strength={face_blur.strength}")

    # Voice conversion
    voice_conv = VoiceConversion(clip=mock_clip, target_voice_sample="voice.wav", strength=0.8)
    print(f"VoiceConversion: strength={voice_conv.strength}")

    # Music generation
    music_gen = MusicGeneration(prompt="ambient electronic", duration=10.0, tempo=120)
    print(f"MusicGeneration: prompt={music_gen.prompt!r}, duration={music_gen.duration}s")

    # Sound FX generation
    sfx_gen = SoundFXGeneration(description="thunder rumble", duration=3.0)
    print(f"SoundFXGeneration: description={sfx_gen.description!r}, duration={sfx_gen.duration}s")


if __name__ == "__main__":
    demo_ai_effects_showcase()
    demo_effect_api_patterns()
    demo_helper_api_patterns()
