"""Animated text presets — factory functions that produce TextClip sequences.

Each preset creates one or more TextClip instances with per-character or
per-word animation configured via render_frame overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from pymotion.clip.base import Clip, RenderContext
from pymotion.security.validation import sanitize_text
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger
from pymotion.utils.math import Vec2

if TYPE_CHECKING:
    from pymotion.text.renderer import GlyphRenderer

logger = get_logger(__name__)

_cached_renderer: GlyphRenderer | None = None


def _get_renderer() -> GlyphRenderer:
    """Get or create a shared GlyphRenderer for animated text."""
    global _cached_renderer  # noqa: PLW0603
    if _cached_renderer is None:
        from pymotion.text.renderer import (
            FontLoader,  # noqa: PLC0415
            GlyphRenderer,  # noqa: PLC0415
        )

        _cached_renderer = GlyphRenderer(FontLoader())
    return _cached_renderer


def _render_text_simple(
    text: str,
    width: int,
    height: int,
    font_size: float,
    color: tuple[int, int, int, int],
    position: Vec2,
    font: str = "Arial",
) -> np.ndarray:
    """Render text to a BGRA frame using FreeType via GlyphRenderer.

    Args:
        text: Text to render.
        width: Frame width.
        height: Frame height.
        font_size: Font size in points.
        color: BGRA color tuple (ignored, color comes from Color object).
        position: Text position (x, y).
        font: Font name or path.

    Returns:
        BGRA numpy array.
    """
    frame = np.zeros((height, width, 4), dtype=np.uint8)
    if not text.strip():
        return frame

    # Convert BGRA uint8 tuple back to Color
    b, g, r, a = color
    text_color = Color(r / 255.0, g / 255.0, b / 255.0, a / 255.0)

    try:
        renderer = _get_renderer()
        text_img = renderer.render_text(
            text,
            font,
            font_size,
            text_color,
        )

        # Composite text image onto frame at position
        th, tw = text_img.shape[:2]
        px = int(position.x)
        py = int(position.y)

        src_y0 = max(0, -py)
        src_x0 = max(0, -px)
        dst_y0 = max(0, py)
        dst_x0 = max(0, px)
        copy_h = min(th - src_y0, height - dst_y0)
        copy_w = min(tw - src_x0, width - dst_x0)

        if copy_h > 0 and copy_w > 0:
            frame[dst_y0 : dst_y0 + copy_h, dst_x0 : dst_x0 + copy_w] = text_img[
                src_y0 : src_y0 + copy_h, src_x0 : src_x0 + copy_w
            ]
    except (FileNotFoundError, OSError):
        # Fallback: draw block characters if font not available
        logger.debug("animated_text_font_fallback", font=font)
        char_w = max(1, int(font_size * 0.6))
        char_h = max(1, int(font_size))
        x = int(position.x)
        y = int(position.y)
        for ch in text:
            if ch == "\n":
                x = int(position.x)
                y += char_h + 2
                continue
            if ch == " ":
                x += char_w
                continue
            x0 = max(0, x)
            y0 = max(0, y)
            x1 = min(width, x + char_w)
            y1 = min(height, y + char_h)
            if x0 < x1 and y0 < y1:
                frame[y0:y1, x0:x1] = color
            x += char_w + 1

    return frame


@dataclass
class Typewriter(Clip):
    """Typewriter animated text — characters appear one by one.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        chars_per_frame: How many characters appear per frame.
        cursor: Whether to show a blinking cursor.
        position: Text position.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    chars_per_frame: float = 0.5
    cursor: bool = True
    position: Vec2 = Vec2(50.0, 50.0)

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render typewriter animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        n_chars = min(len(self.text), int(ctx.local_frame * self.chars_per_frame))
        visible = self.text[:n_chars]

        # Add blinking cursor
        if self.cursor and ctx.local_frame % 30 < 15:
            visible += "|"

        b, g, r, a = self.color.to_bgra_uint8()
        return _render_text_simple(
            visible,
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )


@dataclass
class WordByWord(Clip):
    """Word-by-word animated text — each word fades in sequentially.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        frames_per_word: Frames between each word appearing.
        position: Text position.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    frames_per_word: int = 10
    position: Vec2 = Vec2(50.0, 50.0)

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render word-by-word animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        words = self.text.split()
        n_words = min(len(words), ctx.local_frame // max(self.frames_per_word, 1) + 1)
        visible = " ".join(words[:n_words])

        b, g, r, a = self.color.to_bgra_uint8()
        return _render_text_simple(
            visible,
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )


@dataclass
class LetterByLetter(Clip):
    """Letter-by-letter animated text — each letter has independent animation.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        frames_per_letter: Frames between each letter appearing.
        position: Text position.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    frames_per_letter: int = 3
    position: Vec2 = Vec2(50.0, 50.0)

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render letter-by-letter animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        n_chars = min(len(self.text), ctx.local_frame // max(self.frames_per_letter, 1) + 1)
        visible = self.text[:n_chars]

        b, g, r, a = self.color.to_bgra_uint8()
        return _render_text_simple(
            visible,
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )


@dataclass
class Scramble(Clip):
    """Scramble animated text — characters cycle through random values before settling.

    Args:
        text: The final text.
        font_size: Font size in pixels.
        color: Text color.
        scramble_frames: Frames of scrambling before each character settles.
        position: Text position.
        seed: Random seed for reproducibility.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    scramble_frames: int = 5
    position: Vec2 = Vec2(50.0, 50.0)
    seed: int = 42

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render scramble animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        rng = np.random.default_rng(self.seed + ctx.local_frame)
        chars = list(self.text)
        result_chars: list[str] = []

        for i, ch in enumerate(chars):
            settle_frame = i * self.scramble_frames
            if ctx.local_frame >= settle_frame:
                result_chars.append(ch)
            else:
                # Random character
                result_chars.append(chr(rng.integers(33, 127)))

        b, g, r, a = self.color.to_bgra_uint8()
        return _render_text_simple(
            "".join(result_chars),
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )


@dataclass
class KineticText(Clip):
    """Kinetic text — each word animated with position and scale keyframes.

    Words bounce in from the side with slight rotation feel.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        frames_per_word: Frames between each word animating in.
        position: Starting position.
    """

    text: str = ""
    font_size: float = 32.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    frames_per_word: int = 15
    position: Vec2 = Vec2(50.0, 50.0)

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render kinetic text animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        frame = np.zeros((ctx.resolution.height, ctx.resolution.width, 4), dtype=np.uint8)
        words = self.text.split()
        b, g, r, a = self.color.to_bgra_uint8()
        char_w = max(1, int(self.font_size * 0.6))

        x_offset = int(self.position.x)
        for i, word in enumerate(words):
            word_start = i * self.frames_per_word
            if ctx.local_frame < word_start:
                break

            # Ease in: slide from right
            progress = min(1.0, (ctx.local_frame - word_start) / max(self.frames_per_word, 1))
            ease = 1.0 - (1.0 - progress) ** 3  # Cubic ease-out

            word_x = int(x_offset + (1.0 - ease) * ctx.resolution.width * 0.3)
            word_frame = _render_text_simple(
                word,
                ctx.resolution.width,
                ctx.resolution.height,
                self.font_size,
                (b, g, r, int(a * ease)),
                Vec2(float(word_x), self.position.y),
            )

            # Additive composite
            frame = np.maximum(frame, word_frame)
            x_offset += len(word) * (char_w + 1) + char_w

        return frame


@dataclass
class SplitReveal(Clip):
    """Split reveal — text split into top/bottom halves that slide together.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        reveal_frames: Frames for the reveal animation.
        position: Text position.
    """

    text: str = ""
    font_size: float = 32.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    reveal_frames: int = 20
    position: Vec2 = Vec2(50.0, 50.0)

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render split reveal animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        w, h = ctx.resolution.width, ctx.resolution.height
        b, g, r, a = self.color.to_bgra_uint8()

        full = _render_text_simple(
            self.text,
            w,
            h,
            self.font_size,
            (b, g, r, a),
            self.position,
        )

        progress = min(1.0, ctx.local_frame / max(self.reveal_frames, 1))
        ease = 1.0 - (1.0 - progress) ** 2  # Quadratic ease-out

        # Split at text center height
        mid_y = int(self.position.y + self.font_size / 2)
        offset = int((1.0 - ease) * self.font_size)

        result = np.zeros_like(full)
        # Top half slides down from above
        if mid_y > 0:
            top_src_start = max(0, -offset)
            top_dst_start = max(0, mid_y - offset - (mid_y - top_src_start))
            copy_h = min(mid_y, mid_y - offset) - top_src_start
            if copy_h > 0 and top_dst_start + copy_h <= h:
                result[max(0, mid_y - offset - copy_h) : max(0, mid_y - offset), :] = full[
                    top_src_start : top_src_start + copy_h, :
                ]
        # Bottom half slides up from below
        if mid_y < h:
            bot_start = min(h, mid_y + offset)
            bot_copy = min(h - mid_y, h - bot_start)
            if bot_copy > 0 and bot_start + bot_copy <= h:
                result[bot_start : bot_start + bot_copy, :] = full[mid_y : mid_y + bot_copy, :]

        return result


@dataclass
class CountUp(Clip):
    """Count-up animated number — animates from start_value to end_value.

    Args:
        start_value: Starting number.
        end_value: Ending number.
        font_size: Font size in pixels.
        color: Text color.
        prefix: Text prefix before the number.
        suffix: Text suffix after the number.
        decimals: Decimal places to show.
        position: Text position.
    """

    start_value: float = 0.0
    end_value: float = 100.0
    font_size: float = 32.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    prefix: str = ""
    suffix: str = ""
    decimals: int = 0
    position: Vec2 = Vec2(50.0, 50.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render count-up animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        t = ctx.progress
        current = self.start_value + (self.end_value - self.start_value) * t

        if self.decimals == 0:
            text = f"{self.prefix}{int(current)}{self.suffix}"
        else:
            text = f"{self.prefix}{current:.{self.decimals}f}{self.suffix}"

        b, g, r, a = self.color.to_bgra_uint8()
        return _render_text_simple(
            text,
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )


@dataclass
class CountDown(Clip):
    """Count-down animated number — animates from start_value down to end_value.

    Args:
        start_value: Starting number.
        end_value: Ending number.
        font_size: Font size in pixels.
        color: Text color.
        prefix: Text prefix.
        suffix: Text suffix.
        decimals: Decimal places to show.
        position: Text position.
    """

    start_value: float = 100.0
    end_value: float = 0.0
    font_size: float = 32.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    prefix: str = ""
    suffix: str = ""
    decimals: int = 0
    position: Vec2 = Vec2(50.0, 50.0)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render count-down animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        t = ctx.progress
        current = self.start_value + (self.end_value - self.start_value) * t

        if self.decimals == 0:
            text = f"{self.prefix}{int(current)}{self.suffix}"
        else:
            text = f"{self.prefix}{current:.{self.decimals}f}{self.suffix}"

        b, g, r, a = self.color.to_bgra_uint8()
        return _render_text_simple(
            text,
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )


@dataclass
class GlitchText(Clip):
    """Glitch text — randomized character replacement with chromatic offset.

    Args:
        text: The text to display.
        font_size: Font size in pixels.
        color: Text color.
        glitch_intensity: Probability of character replacement per frame (0-1).
        position: Text position.
        seed: Random seed.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    glitch_intensity: float = 0.3
    position: Vec2 = Vec2(50.0, 50.0)
    seed: int = 42

    def __post_init__(self) -> None:
        """Sanitize text input."""
        self.text = sanitize_text(self.text)

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render glitch text animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        rng = np.random.default_rng(self.seed + ctx.local_frame)
        chars = list(self.text)
        result_chars: list[str] = []

        for ch in chars:
            if ch != " " and rng.random() < self.glitch_intensity:
                result_chars.append(chr(rng.integers(33, 127)))
            else:
                result_chars.append(ch)

        b, g, r, a = self.color.to_bgra_uint8()
        frame = _render_text_simple(
            "".join(result_chars),
            ctx.resolution.width,
            ctx.resolution.height,
            self.font_size,
            (b, g, r, a),
            self.position,
        )

        # Add chromatic offset on glitch frames
        if rng.random() < self.glitch_intensity:
            offset = rng.integers(1, 4)
            frame_shifted = frame.copy()
            frame_shifted[:, :, 2] = np.roll(frame[:, :, 2], offset, axis=1)  # R shift
            frame_shifted[:, :, 0] = np.roll(frame[:, :, 0], -offset, axis=1)  # B shift
            return frame_shifted

        return frame
