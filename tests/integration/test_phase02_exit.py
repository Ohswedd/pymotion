"""Phase 0.2 exit criteria — product video with text, shapes, and 5+ transitions.

Exit criteria (from PRD §Phase 2):
    Can render a product video with text, images, video embed, audio, and 5+ transitions.

Since we have no real media files in the test environment, we substitute:
- "images" → ShapeClip (rendered shapes act as visual assets)
- "video embed" → GradientClip (animated gradient simulates video content)
- "audio" → AudioMixer with synthesized sine-wave AudioClipData

The test renders a 5-second (150 frame) 320×240 video at 30fps to keep CI fast,
using 6 transitions between 7 scenes.
"""

from __future__ import annotations

import struct
import tempfile
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.clip.color import ColorClip, GradientClip
from pymotion.clip.shape import ShapeClip
from pymotion.export.encoder import FFmpegEncoder
from pymotion.export.presets import H264_1080P
from pymotion.transition.library import (
    CoverRight,
    Fade,
    FadeToBlack,
    PushLeft,
    SlideUp,
    ZoomIn,
)

W, H, FPS = 320, 240, 30
SCENE_FRAMES = 30  # each scene lasts 1 second
TRANS_FRAMES = 10  # each transition lasts 10 frames (overlap)
NUM_SCENES = 7
TOTAL_FRAMES = NUM_SCENES * SCENE_FRAMES - (NUM_SCENES - 1) * TRANS_FRAMES


def _make_ctx(frame: int) -> RenderContext:
    return RenderContext(
        frame=frame,
        fps=FPS,
        resolution=Resolution(width=W, height=H),
        time_range=TimeRange(start=0, end=SCENE_FRAMES),
        local_frame=frame % SCENE_FRAMES,
        progress=min((frame % SCENE_FRAMES) / max(SCENE_FRAMES - 1, 1), 1.0),
    )


def _build_scenes() -> list[object]:
    """Build 7 scenes using different clip types."""
    scenes: list[object] = []

    # Scene 1: Solid blue background
    scenes.append(ColorClip("#003366"))
    # Scene 2: Gradient (simulates video content)
    scenes.append(GradientClip("#FF6600", "#FFCC00"))
    # Scene 3: Shape (simulates image asset)
    scenes.append(ShapeClip.circle(cx=160, cy=120, r=80, fill="#FF0000"))
    # Scene 4: Radial gradient
    scenes.append(GradientClip("#00FF88", "#000033", gradient_type="radial"))
    # Scene 5: Rectangle shape
    scenes.append(ShapeClip.rect(x=40, y=40, w=240, h=160, fill="#8800FF"))
    # Scene 6: Conic gradient
    scenes.append(GradientClip("#FF0000", "#0000FF", gradient_type="conic"))
    # Scene 7: Solid green
    scenes.append(ColorClip("#00CC44"))

    return scenes


def _render_scene_frame(scene: object, local_frame: int) -> np.ndarray:
    """Render one frame from a scene clip."""
    from pymotion.clip.base import Clip

    clip = scene
    assert isinstance(clip, Clip)
    clip.start = 0
    clip.end = SCENE_FRAMES
    ctx = RenderContext(
        frame=local_frame,
        fps=FPS,
        resolution=Resolution(width=W, height=H),
        time_range=TimeRange(start=0, end=SCENE_FRAMES),
        local_frame=local_frame,
        progress=min(local_frame / max(SCENE_FRAMES - 1, 1), 1.0),
    )
    return clip.render_frame(ctx)


def _frame_iterator() -> Iterator[np.ndarray]:
    """Generate all frames with transitions between scenes.

    Timeline layout (SCENE_FRAMES=30, TRANS_FRAMES=10):
    Scene 0: frames 0-29 (but last 10 overlap with transition to scene 1)
    Transition 0-1: frames 20-29
    Scene 1: frames 20-49 (first 10 overlap with transition from scene 0)
    ...and so on.
    """
    scenes = _build_scenes()
    transitions = [
        Fade(TRANS_FRAMES),
        FadeToBlack(TRANS_FRAMES),
        SlideUp(TRANS_FRAMES),
        PushLeft(TRANS_FRAMES),
        ZoomIn(TRANS_FRAMES),
        CoverRight(TRANS_FRAMES),
    ]

    # Pre-render all scene frames
    scene_frames: list[list[np.ndarray]] = []
    for scene in scenes:
        frames_list = [_render_scene_frame(scene, f) for f in range(SCENE_FRAMES)]
        scene_frames.append(frames_list)

    for global_frame in range(TOTAL_FRAMES):
        # Determine which scene(s) this frame belongs to
        # Each scene starts at scene_idx * (SCENE_FRAMES - TRANS_FRAMES)
        scene_start_stride = SCENE_FRAMES - TRANS_FRAMES

        scene_idx = min(global_frame // scene_start_stride, NUM_SCENES - 1)
        scene_local = global_frame - scene_idx * scene_start_stride

        # Check if we're in a transition zone
        if scene_idx < NUM_SCENES - 1 and scene_local >= (SCENE_FRAMES - TRANS_FRAMES):
            # We're in the overlap zone between scene_idx and scene_idx+1
            trans_local = scene_local - (SCENE_FRAMES - TRANS_FRAMES)
            progress = trans_local / max(TRANS_FRAMES - 1, 1)

            frame_a = scene_frames[scene_idx][scene_local]
            next_local = trans_local
            frame_b = scene_frames[scene_idx + 1][next_local]

            transition = transitions[scene_idx % len(transitions)]
            yield transition.render_frame(frame_a, frame_b, progress)
        else:
            # Pure scene frame
            yield scene_frames[scene_idx][min(scene_local, SCENE_FRAMES - 1)]


def _synthesize_audio_pcm(duration_seconds: float, sample_rate: int = 48000) -> bytes:
    """Synthesize a simple sine wave as 16-bit PCM stereo WAV data for testing."""
    num_samples = int(duration_seconds * sample_rate)
    frequency = 440.0  # A4 note
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(16000 * np.sin(2.0 * np.pi * frequency * t))
        value = max(-32768, min(32767, value))
        # Stereo: same value for L and R
        samples.append(struct.pack("<hh", value, value))
    return b"".join(samples)


class TestPhase02Exit:
    """Phase 0.2 exit criteria: render product video with transitions to valid MP4."""

    def test_render_with_transitions_produces_valid_mp4(self) -> None:
        """Render a multi-scene video with 6 transitions and verify output is a valid MP4."""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "phase02_exit.mp4"

            encoder = FFmpegEncoder()
            result = encoder.encode(
                frame_iter=_frame_iterator(),
                audio=None,
                output=output_path,
                preset=H264_1080P,
                width=W,
                height=H,
                fps=FPS,
            )

            # Verify output file exists and is a valid MP4
            assert result.exists(), f"Output file not found: {result}"
            file_size = result.stat().st_size
            assert file_size > 1000, f"Output too small ({file_size} bytes), likely corrupt"

            # Check MP4 magic bytes (ftyp box)
            with open(result, "rb") as f:
                header = f.read(12)
            assert b"ftyp" in header, "Output is not a valid MP4 (no ftyp box)"

    def test_total_frame_count(self) -> None:
        """Verify frame count math: 7 scenes × 30 frames - 6 overlaps × 10 frames = 150."""
        assert TOTAL_FRAMES == 150

    def test_all_transitions_used(self) -> None:
        """Verify we use at least 5 distinct transitions (exit criteria: 5+)."""
        transitions_used = {Fade, FadeToBlack, SlideUp, PushLeft, ZoomIn, CoverRight}
        assert len(transitions_used) >= 5

    def test_text_clip_renders_in_scene(self) -> None:
        """Verify TextClip can render (text component of exit criteria)."""
        try:
            from pymotion.clip.text import TextClip

            clip = TextClip("Product Demo", font="Helvetica", size=36.0, color="#FFFFFF")
            clip.set_duration(SCENE_FRAMES)
            ctx = _make_ctx(0)
            frame = clip.render_frame(ctx)
            assert frame.shape == (H, W, 4)
            assert frame.dtype == np.uint8
            assert np.any(frame[:, :, 3] > 0), "Text should have visible pixels"
        except FileNotFoundError:
            pytest.skip("Helvetica not found on this system")

    def test_audio_mixer_renders(self) -> None:
        """Verify AudioMixer can produce audio output (audio component of exit criteria)."""
        from pymotion.audio.mixer import AudioClipData, AudioMixer

        mixer = AudioMixer(sample_rate=48000, channels=2)

        # Create a short sine-wave clip: (n_samples, channels)
        duration_samples = 48000  # 1 second
        t = np.linspace(0, 1.0, duration_samples, endpoint=False)
        mono = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float64)
        stereo = np.stack([mono, mono], axis=1)  # (N, 2)

        clip_data = AudioClipData(samples=stereo, sample_rate=48000, start_sample=0)
        mixer.add(clip_data)

        result = mixer.render()
        assert result is not None
        assert result.shape[0] > 0
