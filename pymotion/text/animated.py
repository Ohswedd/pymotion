"""Animated text presets — factory functions that produce TextClip sequences.

Each preset creates one or more TextClip instances with per-character or
per-word animation configured via render_frame overrides.

Architecture
------------
Text-reveal presets (Typewriter, WordByWord, LetterByLetter) use a
**reveal-mask** approach for flicker-free animation:

1. The FULL final text is rendered once (cached) to a BGRA image.
2. Each frame, a horizontal alpha mask smoothly reveals the text
   left-to-right with a soft gradient edge.
3. Already-revealed pixels are bit-for-bit identical every frame
   because they come from the same cached image.
4. The soft edge (configurable, default ~10 px) provides a
   professional fade-in instead of an abrupt character pop.

CountUp / CountDown use an ease-out timing curve so numbers
decelerate smoothly toward the final value.
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


# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------
_text_render_cache: dict[tuple[str, float, tuple[int, int, int, int], str], np.ndarray] = {}
_char_positions_cache: dict[tuple[str, float, str], list[int]] = {}


def _measure_char_positions(
    text: str,
    font_size: float,
    font: str = "Arial",
) -> list[int]:
    """Return the cumulative x-advance after each character.

    ``result[i]`` is the pixel x position of the right edge of
    character ``text[i]``.  Used to compute the reveal-mask boundary.

    Args:
        text: The text to measure.
        font_size: Font size in points.
        font: Font name or path.

    Returns:
        List of cumulative pixel widths (length == len(text)).
    """
    key = (text, font_size, font)
    cached = _char_positions_cache.get(key)
    if cached is not None:
        return cached

    renderer = _get_renderer()
    face = renderer._font_loader.load(font, font_size)
    positions: list[int] = []
    pen_x = 0
    for ch in text:
        face.load_char(ch)
        pen_x += face.glyph.advance.x >> 6
        positions.append(pen_x)

    if len(_char_positions_cache) > 200:
        _char_positions_cache.clear()
    _char_positions_cache[key] = positions
    return positions


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

    Uses a glyph cache keyed on (text, font_size, color, font) to avoid
    redundant FreeType calls for identical text across frames.

    Args:
        text: Text to render.
        width: Frame width.
        height: Frame height.
        font_size: Font size in points.
        color: BGRA color tuple.
        position: Text position (x, y).
        font: Font name or path.

    Returns:
        BGRA numpy array.
    """
    frame = np.zeros((height, width, 4), dtype=np.uint8)
    if not text.strip():
        return frame

    cache_key = (text, font_size, color, font)
    text_img = _text_render_cache.get(cache_key)

    if text_img is None:
        b, g, r, a = color
        text_color = Color(r / 255.0, g / 255.0, b / 255.0, a / 255.0)
        renderer = _get_renderer()
        text_img = renderer.render_text(text, font, font_size, text_color)
        if len(_text_render_cache) > 500:
            _text_render_cache.clear()
        _text_render_cache[cache_key] = text_img

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

    return frame


# ---------------------------------------------------------------------------
# Reveal-mask helper
# ---------------------------------------------------------------------------

# Default soft-edge width for the reveal gradient (pixels).
_REVEAL_FADE_PX = 10


def _apply_reveal_mask(
    frame: np.ndarray,
    reveal_x: int,
    position_x: int,
    fade_px: int = _REVEAL_FADE_PX,
) -> np.ndarray:
    """Zero-out alpha past *reveal_x* with a soft gradient edge.

    Pixels to the left of ``reveal_x - fade_px`` are untouched.
    Pixels in the gradient zone fade linearly from full to zero alpha.
    Pixels to the right of ``reveal_x`` are fully transparent.

    Operates in-place on *frame* and returns it.

    Args:
        frame: BGRA frame (H, W, 4) uint8 — modified in place.
        reveal_x: Absolute x position (in frame coords) where text
            is fully visible up to.
        position_x: The x position where the text starts.
        fade_px: Width of the soft gradient edge in pixels.

    Returns:
        The same *frame* array (modified in place).
    """
    w = frame.shape[1]
    # Clamp to valid range
    reveal_x = max(position_x, min(reveal_x, w))
    fade_start = max(position_x, reveal_x - fade_px)

    # Everything right of reveal_x → transparent
    if reveal_x < w:
        frame[:, reveal_x:, 3] = 0

    # Gradient zone
    if fade_start < reveal_x:
        n = reveal_x - fade_start
        gradient = np.linspace(1.0, 0.0, n, dtype=np.float32)
        alpha_region = frame[:, fade_start:reveal_x, 3].astype(np.float32)
        alpha_region *= gradient[np.newaxis, :]
        frame[:, fade_start:reveal_x, 3] = alpha_region.astype(np.uint8)

    return frame


# ---------------------------------------------------------------------------
# Ease-out helper for CountUp / CountDown
# ---------------------------------------------------------------------------


def _ease_out_quint(t: float) -> float:
    """Quintic ease-out: fast start, smooth deceleration.

    Stronger than cubic — the counter reaches ~97% by halfway through,
    so it spends the second half barely changing (settling effect).

    Args:
        t: Linear progress in [0, 1].

    Returns:
        Eased progress in [0, 1].
    """
    return 1.0 - (1.0 - t) ** 5


# ═══════════════════════════════════════════════════════════════
# TEXT-REVEAL PRESETS
# ═══════════════════════════════════════════════════════════════


@dataclass
class Typewriter(Clip):
    """Typewriter animated text — characters revealed with a smooth wipe.

    Renders the full text once and reveals it left-to-right using a
    soft horizontal mask.  Each new character fades in over a few
    pixels rather than popping in at full opacity.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        chars_per_frame: How many characters are revealed per frame.
        cursor: Whether to show a blinking cursor at the reveal edge.
        position: Text position.
        fade_px: Width of the soft reveal edge in pixels.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    chars_per_frame: float = 0.5
    cursor: bool = True
    position: Vec2 = Vec2(50.0, 50.0)
    fade_px: int = _REVEAL_FADE_PX

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
        b, g, r, a = self.color.to_bgra_uint8()
        w = ctx.resolution.width
        h = ctx.resolution.height
        px = int(self.position.x)

        # How far we've revealed (fractional characters)
        reveal_chars = min(float(len(self.text)), ctx.local_frame * self.chars_per_frame)
        n_full = int(reveal_chars)

        if n_full >= len(self.text):
            # Fully revealed — return cached full text (no mask needed)
            frame = _render_text_simple(
                self.text,
                w,
                h,
                self.font_size,
                (b, g, r, a),
                self.position,
            )
            if self.cursor and ctx.local_frame % 30 < 15:
                cursor_frame = _render_text_simple(
                    "|",
                    w,
                    h,
                    self.font_size,
                    (b, g, r, a),
                    Vec2(self.position.x + self._text_width(), self.position.y),
                )
                np.maximum(frame, cursor_frame, out=frame)
            return frame

        if reveal_chars <= 0.0:
            return np.zeros((h, w, 4), dtype=np.uint8)

        # Render full text
        frame = _render_text_simple(
            self.text,
            w,
            h,
            self.font_size,
            (b, g, r, a),
            self.position,
        )

        # Compute reveal boundary from character positions
        positions = _measure_char_positions(self.text, self.font_size)
        # Interpolate between character boundaries for sub-character reveal
        frac = reveal_chars - n_full
        left_edge = positions[n_full - 1] if n_full > 0 else 0
        right_edge = positions[n_full] if n_full < len(positions) else left_edge
        reveal_px = int(left_edge + (right_edge - left_edge) * frac)

        _apply_reveal_mask(frame, px + reveal_px, px, self.fade_px)

        # Blinking cursor at reveal edge
        if self.cursor and ctx.local_frame % 30 < 15:
            cursor_frame = _render_text_simple(
                "|",
                w,
                h,
                self.font_size,
                (b, g, r, a),
                Vec2(float(px + reveal_px), self.position.y),
            )
            np.maximum(frame, cursor_frame, out=frame)

        return frame

    def _text_width(self) -> float:
        """Get the full text width in pixels."""
        positions = _measure_char_positions(self.text, self.font_size)
        return float(positions[-1]) if positions else 0.0


@dataclass
class WordByWord(Clip):
    """Word-by-word animated text — each word revealed with a smooth wipe.

    Renders the full text once and reveals it word-by-word using a
    soft horizontal mask.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        frames_per_word: Frames between each word appearing.
        position: Text position.
        fade_px: Width of the soft reveal edge in pixels.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    frames_per_word: int = 10
    position: Vec2 = Vec2(50.0, 50.0)
    fade_px: int = _REVEAL_FADE_PX

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
        b, g, r, a = self.color.to_bgra_uint8()
        w = ctx.resolution.width
        h = ctx.resolution.height
        px = int(self.position.x)

        words = self.text.split()
        n_words = min(len(words), ctx.local_frame // max(self.frames_per_word, 1) + 1)

        if n_words >= len(words):
            return _render_text_simple(
                self.text,
                w,
                h,
                self.font_size,
                (b, g, r, a),
                self.position,
            )

        if n_words <= 0:
            return np.zeros((h, w, 4), dtype=np.uint8)

        # Render full text
        frame = _render_text_simple(
            self.text,
            w,
            h,
            self.font_size,
            (b, g, r, a),
            self.position,
        )

        # Find the character index at the end of the n-th word
        visible = " ".join(words[:n_words])
        char_idx = len(visible)

        # Compute reveal boundary
        positions = _measure_char_positions(self.text, self.font_size)

        # Fractional word progress for smooth transition
        word_local = ctx.local_frame % max(self.frames_per_word, 1)
        word_frac = word_local / max(self.frames_per_word, 1)

        # Reveal up to end of current word plus fractional progress into next
        reveal_px = positions[min(char_idx - 1, len(positions) - 1)] if char_idx > 0 else 0
        if char_idx < len(positions):
            next_px = positions[min(char_idx, len(positions) - 1)]
            reveal_px = int(reveal_px + (next_px - reveal_px) * word_frac)

        _apply_reveal_mask(frame, px + reveal_px, px, self.fade_px)
        return frame


@dataclass
class LetterByLetter(Clip):
    """Letter-by-letter animated text — each letter revealed with a smooth wipe.

    Renders the full text once and reveals it character-by-character
    using a soft horizontal mask.

    Args:
        text: The text to animate.
        font_size: Font size in pixels.
        color: Text color.
        frames_per_letter: Frames between each letter appearing.
        position: Text position.
        fade_px: Width of the soft reveal edge in pixels.
    """

    text: str = ""
    font_size: float = 24.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    frames_per_letter: int = 3
    position: Vec2 = Vec2(50.0, 50.0)
    fade_px: int = _REVEAL_FADE_PX

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
        b, g, r, a = self.color.to_bgra_uint8()
        w = ctx.resolution.width
        h = ctx.resolution.height
        px = int(self.position.x)

        fpl = max(self.frames_per_letter, 1)
        # Fractional character reveal for smooth sub-character wipe
        reveal_chars = min(float(len(self.text)), (ctx.local_frame + 1) / fpl)
        n_full = int(reveal_chars)

        if n_full >= len(self.text):
            return _render_text_simple(
                self.text,
                w,
                h,
                self.font_size,
                (b, g, r, a),
                self.position,
            )

        if reveal_chars <= 0.0:
            return np.zeros((h, w, 4), dtype=np.uint8)

        frame = _render_text_simple(
            self.text,
            w,
            h,
            self.font_size,
            (b, g, r, a),
            self.position,
        )

        positions = _measure_char_positions(self.text, self.font_size)
        frac = reveal_chars - n_full
        left_edge = positions[n_full - 1] if n_full > 0 else 0
        right_edge = positions[n_full] if n_full < len(positions) else left_edge
        reveal_px = int(left_edge + (right_edge - left_edge) * frac)

        _apply_reveal_mask(frame, px + reveal_px, px, self.fade_px)
        return frame


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

            np.maximum(frame, word_frame, out=frame)
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
        ease = 1.0 - (1.0 - progress) ** 2

        mid_y = int(self.position.y + self.font_size / 2)
        offset = int((1.0 - ease) * self.font_size)

        result = np.zeros_like(full)
        if mid_y > 0:
            top_src_start = max(0, -offset)
            top_dst_start = max(0, mid_y - offset - (mid_y - top_src_start))
            copy_h = min(mid_y, mid_y - offset) - top_src_start
            if copy_h > 0 and top_dst_start + copy_h <= h:
                result[max(0, mid_y - offset - copy_h) : max(0, mid_y - offset), :] = full[
                    top_src_start : top_src_start + copy_h, :
                ]
        if mid_y < h:
            bot_start = min(h, mid_y + offset)
            bot_copy = min(h - mid_y, h - bot_start)
            if bot_copy > 0 and bot_start + bot_copy <= h:
                result[bot_start : bot_start + bot_copy, :] = full[mid_y : mid_y + bot_copy, :]

        return result


# ═══════════════════════════════════════════════════════════════
# COUNTER PRESETS
# ═══════════════════════════════════════════════════════════════


@dataclass
class CountUp(Clip):
    """Count-up animated number — animates from start_value to end_value.

    Uses a quintic ease-out curve (reaches ~97% at halfway) and
    frame-stepping so the displayed number only changes every
    *step_frames* frames.  This prevents the rapid-digit-change
    flicker of updating 30 times per second.

    Args:
        start_value: Starting number.
        end_value: Ending number.
        font_size: Font size in pixels.
        color: Text color.
        prefix: Text prefix before the number.
        suffix: Text suffix after the number.
        decimals: Decimal places to show.
        position: Text position.
        step_frames: The displayed value updates once every this many
            frames.  Higher = fewer visual changes = smoother.
    """

    start_value: float = 0.0
    end_value: float = 100.0
    font_size: float = 32.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    prefix: str = ""
    suffix: str = ""
    decimals: int = 0
    position: Vec2 = Vec2(50.0, 50.0)
    step_frames: int = 3

    def _format(self, value: float) -> str:
        """Format the counter value as display text."""
        if self.decimals == 0:
            return f"{self.prefix}{int(value)}{self.suffix}"
        return f"{self.prefix}{value:.{self.decimals}f}{self.suffix}"

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render count-up animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        # Snap local_frame to step grid so the number holds for
        # *step_frames* consecutive frames.
        step = max(self.step_frames, 1)
        snapped = (ctx.local_frame // step) * step
        clip_len = max(ctx.time_range.end - ctx.time_range.start - 1, 1)
        t = _ease_out_quint(snapped / clip_len)
        current = self.start_value + (self.end_value - self.start_value) * min(t, 1.0)

        text = self._format(current)

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

    Uses a quintic ease-out curve and frame-stepping for smooth,
    flicker-free counting.

    Args:
        start_value: Starting number.
        end_value: Ending number.
        font_size: Font size in pixels.
        color: Text color.
        prefix: Text prefix.
        suffix: Text suffix.
        decimals: Decimal places to show.
        position: Text position.
        step_frames: The displayed value updates once every this many frames.
    """

    start_value: float = 100.0
    end_value: float = 0.0
    font_size: float = 32.0
    color: Color = Color(1.0, 1.0, 1.0, 1.0)
    prefix: str = ""
    suffix: str = ""
    decimals: int = 0
    position: Vec2 = Vec2(50.0, 50.0)
    step_frames: int = 3

    def _format(self, value: float) -> str:
        """Format the counter value as display text."""
        if self.decimals == 0:
            return f"{self.prefix}{int(value)}{self.suffix}"
        return f"{self.prefix}{value:.{self.decimals}f}{self.suffix}"

    def render_frame(self, ctx: RenderContext) -> np.ndarray:
        """Render count-down animation frame.

        Args:
            ctx: Render context.

        Returns:
            BGRA frame.
        """
        step = max(self.step_frames, 1)
        snapped = (ctx.local_frame // step) * step
        clip_len = max(ctx.time_range.end - ctx.time_range.start - 1, 1)
        t = _ease_out_quint(snapped / clip_len)
        current = self.start_value + (self.end_value - self.start_value) * min(t, 1.0)

        text = self._format(current)

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

        if rng.random() < self.glitch_intensity:
            offset = rng.integers(1, 4)
            frame_shifted = frame.copy()
            frame_shifted[:, :, 2] = np.roll(frame[:, :, 2], offset, axis=1)
            frame_shifted[:, :, 0] = np.roll(frame[:, :, 0], -offset, axis=1)
            return frame_shifted

        return frame
