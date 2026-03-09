"""Tests for animated text presets."""

from __future__ import annotations

import numpy as np

from pymotion.clip.base import RenderContext, Resolution, TimeRange
from pymotion.text.animated import (
    CountDown,
    CountUp,
    GlitchText,
    KineticText,
    LetterByLetter,
    Scramble,
    SplitReveal,
    Typewriter,
    WordByWord,
)

_W, _H = 120, 60


def _ctx(local_frame: int = 10, progress: float = 0.5) -> RenderContext:
    return RenderContext(
        frame=local_frame,
        fps=30,
        resolution=Resolution(_W, _H),
        time_range=TimeRange(0, 60),
        local_frame=local_frame,
        progress=progress,
    )


def _valid(frame: np.ndarray) -> None:
    assert frame.shape == (_H, _W, 4)
    assert frame.dtype == np.uint8


class TestTypewriter:
    def test_renders(self) -> None:
        clip = Typewriter(text="Hello World")
        _valid(clip.render_frame(_ctx()))

    def test_no_text_at_start(self) -> None:
        clip = Typewriter(text="Hello", chars_per_frame=0.5)
        result = clip.render_frame(_ctx(local_frame=0))
        _valid(result)

    def test_cursor_blinks(self) -> None:
        clip = Typewriter(text="Hi", cursor=True)
        r1 = clip.render_frame(_ctx(local_frame=5))
        r2 = clip.render_frame(_ctx(local_frame=20))
        _valid(r1)
        _valid(r2)


class TestWordByWord:
    def test_renders(self) -> None:
        clip = WordByWord(text="Hello beautiful world")
        _valid(clip.render_frame(_ctx()))

    def test_first_frame_one_word(self) -> None:
        clip = WordByWord(text="Hello World", frames_per_word=10)
        result = clip.render_frame(_ctx(local_frame=0))
        _valid(result)


class TestLetterByLetter:
    def test_renders(self) -> None:
        clip = LetterByLetter(text="ABC", frames_per_letter=2)
        _valid(clip.render_frame(_ctx()))


class TestScramble:
    def test_renders(self) -> None:
        clip = Scramble(text="Hello")
        _valid(clip.render_frame(_ctx()))

    def test_deterministic(self) -> None:
        clip = Scramble(text="Hello", seed=99)
        r1 = clip.render_frame(_ctx(local_frame=3))
        r2 = clip.render_frame(_ctx(local_frame=3))
        np.testing.assert_array_equal(r1, r2)


class TestKineticText:
    def test_renders(self) -> None:
        clip = KineticText(text="Big Bold Text")
        _valid(clip.render_frame(_ctx()))


class TestSplitReveal:
    def test_renders(self) -> None:
        clip = SplitReveal(text="REVEAL")
        _valid(clip.render_frame(_ctx()))

    def test_at_start(self) -> None:
        clip = SplitReveal(text="REVEAL", reveal_frames=20)
        _valid(clip.render_frame(_ctx(local_frame=0)))


class TestCountUp:
    def test_renders(self) -> None:
        clip = CountUp(start_value=0, end_value=100)
        _valid(clip.render_frame(_ctx(progress=0.5)))

    def test_with_decimals(self) -> None:
        clip = CountUp(start_value=0, end_value=1, decimals=2, prefix="$")
        _valid(clip.render_frame(_ctx(progress=0.5)))

    def test_at_end(self) -> None:
        clip = CountUp(start_value=0, end_value=999, suffix="%")
        _valid(clip.render_frame(_ctx(progress=1.0)))


class TestCountDown:
    def test_renders(self) -> None:
        clip = CountDown(start_value=10, end_value=0)
        _valid(clip.render_frame(_ctx(progress=0.5)))


class TestGlitchText:
    def test_renders(self) -> None:
        clip = GlitchText(text="GLITCH")
        _valid(clip.render_frame(_ctx()))

    def test_deterministic(self) -> None:
        clip = GlitchText(text="GLITCH", seed=42)
        r1 = clip.render_frame(_ctx(local_frame=5))
        r2 = clip.render_frame(_ctx(local_frame=5))
        np.testing.assert_array_equal(r1, r2)
