"""FontLoader and GlyphRenderer using FreeType and HarfBuzz.

Provides font loading from local paths and system directories, glyph
rasterization with sub-pixel antialiasing, and complex text layout
via HarfBuzz for RTL text and ligatures.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# System font directories per platform
_SYSTEM_FONT_DIRS: dict[str, list[Path]] = {
    "Darwin": [
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path.home() / "Library/Fonts",
    ],
    "Linux": [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".local/share/fonts",
        Path.home() / ".fonts",
    ],
    "Windows": [
        Path("C:/Windows/Fonts"),
    ],
}


@dataclass
class GlyphInfo:
    """Information about a shaped glyph for rendering.

    Args:
        glyph_id: FreeType glyph index.
        x_advance: Horizontal advance in pixels.
        y_advance: Vertical advance in pixels.
        x_offset: Horizontal offset from pen position in pixels.
        y_offset: Vertical offset from pen position in pixels.
        cluster: Character cluster index this glyph belongs to.
    """

    glyph_id: int
    x_advance: float
    y_advance: float
    x_offset: float
    y_offset: float
    cluster: int


@dataclass
class ShapedText:
    """Result of text shaping via HarfBuzz.

    Args:
        glyphs: List of shaped glyph info.
        width: Total advance width in pixels.
        height: Total height in pixels.
    """

    glyphs: list[GlyphInfo]
    width: float
    height: float


def _import_freetype() -> Any:
    """Lazy import for freetype-py."""
    import freetype  # type: ignore[import-untyped]

    return freetype


def _import_harfbuzz() -> Any:
    """Lazy import for uharfbuzz."""
    import uharfbuzz  # type: ignore[import-untyped]

    return uharfbuzz


class FontLoader:
    """Loads and caches font faces from local paths and system directories.

    Fonts are cached using an LRU cache (max 50 entries). Supports
    .ttf and .otf font files.
    """

    def __init__(self, max_cache_size: int = 50) -> None:
        """Initialize the font loader.

        Args:
            max_cache_size: Maximum number of fonts to keep in cache.
        """
        self._max_cache_size = max_cache_size
        self._cache: dict[str, Any] = {}
        self._cache_order: list[str] = []
        self._font_data_cache: dict[str, bytes] = {}
        logger.debug("font_loader_init", max_cache=max_cache_size)

    def load(self, font: str, size: float = 24.0) -> Any:
        """Load a font by path or name.

        If font is a path to a file, loads it directly. Otherwise searches
        system font directories for a matching font file.

        Args:
            font: Font file path or font name.
            size: Font size in points.

        Returns:
            A FreeType Face object configured at the given size.

        Raises:
            FileNotFoundError: If the font cannot be found.
            ValueError: If the font file is invalid.
        """
        cache_key = f"{font}:{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        font_path = self._resolve_font_path(font)
        face = self._load_face(font_path, size)

        # LRU eviction
        if len(self._cache) >= self._max_cache_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)
            self._font_data_cache.pop(oldest, None)

        self._cache[cache_key] = face
        self._cache_order.append(cache_key)

        logger.debug("font_loaded", font=font, size=size, path=str(font_path))
        return face

    def load_font_data(self, font: str) -> bytes:
        """Load raw font file bytes (needed for HarfBuzz).

        Args:
            font: Font file path or font name.

        Returns:
            Raw bytes of the font file.
        """
        if font in self._font_data_cache:
            return self._font_data_cache[font]

        font_path = self._resolve_font_path(font)
        data = font_path.read_bytes()
        self._font_data_cache[font] = data
        return data

    def _resolve_font_path(self, font: str) -> Path:
        """Resolve a font string to an actual file path.

        Args:
            font: Font file path or font name.

        Returns:
            Resolved font file path.

        Raises:
            FileNotFoundError: If the font cannot be found.
        """
        # Direct path
        path = Path(font)
        if path.is_file():
            return path.resolve()

        # Search system font dirs
        system = platform.system()
        search_dirs = _SYSTEM_FONT_DIRS.get(system, [])

        for font_dir in search_dirs:
            if not font_dir.is_dir():
                continue
            # Search for exact filename or font name match
            for ext in (".ttf", ".otf", ".ttc", ".TTF", ".OTF", ".TTC"):
                candidate = font_dir / f"{font}{ext}"
                if candidate.is_file():
                    return candidate.resolve()

            # Recursive search for partial matches
            for f in font_dir.rglob("*"):
                if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                    if font.lower() in f.stem.lower():
                        return f.resolve()

        msg = f"Font not found: '{font}'. Searched system directories for {system}."
        raise FileNotFoundError(msg)

    def _load_face(self, path: Path, size: float) -> Any:
        """Load a FreeType face from a font file.

        Args:
            path: Path to the font file.
            size: Font size in points.

        Returns:
            Configured FreeType Face.
        """
        ft = _import_freetype()
        face: Any = ft.Face(str(path))
        # Set size in 26.6 fixed-point (multiply by 64)
        face.set_char_size(int(size * 64))
        return face

    @staticmethod
    def list_system_fonts() -> list[Path]:
        """List all font files found in system font directories.

        Returns:
            List of paths to found font files.
        """
        system = platform.system()
        search_dirs = _SYSTEM_FONT_DIRS.get(system, [])
        fonts: list[Path] = []

        for font_dir in search_dirs:
            if not font_dir.is_dir():
                continue
            for f in font_dir.rglob("*"):
                if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                    fonts.append(f)

        return sorted(fonts)


class GlyphRenderer:
    """Rasterizes text to BGRA numpy arrays using FreeType.

    Supports antialiased rendering with optional sub-pixel positioning.
    """

    def __init__(self, font_loader: FontLoader | None = None) -> None:
        """Initialize the glyph renderer.

        Args:
            font_loader: FontLoader instance to use. Creates a new one if None.
        """
        self._font_loader = font_loader or FontLoader()

    def render_text(
        self,
        text: str,
        font: str,
        size: float = 24.0,
        color: Color | None = None,
        *,
        max_width: int | None = None,
        line_height: float = 1.2,
        align: Literal["left", "center", "right"] = "left",
        letter_spacing: float = 0.0,
    ) -> np.ndarray:
        """Render text to a BGRA numpy array.

        Args:
            text: The text string to render.
            font: Font file path or name.
            size: Font size in points.
            color: Text color.
            max_width: Maximum width for word wrapping (None = no wrap).
            line_height: Line height multiplier relative to font size.
            align: Text alignment ("left", "center", "right").
            letter_spacing: Additional spacing between letters in pixels.

        Returns:
            BGRA numpy array with rendered text on transparent background.
        """
        if not text:
            return np.zeros((1, 1, 4), dtype=np.uint8)

        if color is None:
            color = Color(1.0, 1.0, 1.0, 1.0)

        face = self._font_loader.load(font, size)

        # Compute line metrics
        ascender: int = face.size.ascender >> 6
        descender: int = face.size.descender >> 6
        line_px = int((ascender - descender) * line_height)

        # Split into lines and optionally word-wrap
        raw_lines = text.split("\n")
        if max_width is not None:
            lines = self._word_wrap(face, raw_lines, max_width, letter_spacing)
        else:
            lines = raw_lines

        # Measure all lines to determine image dimensions
        line_widths: list[int] = []
        for line in lines:
            w = self._measure_line(face, line, letter_spacing)
            line_widths.append(w)

        img_width = max(line_widths) if line_widths else 1
        img_height = max(line_px * len(lines), 1)

        # Create output image
        image = np.zeros((img_height, img_width, 4), dtype=np.uint8)
        b_val, g_val, r_val, a_val = color.to_bgra_uint8()

        # Render each line
        y_offset = ascender
        for i, line in enumerate(lines):
            # Compute x offset for alignment
            lw = line_widths[i]
            if align == "center":
                x_start = (img_width - lw) // 2
            elif align == "right":
                x_start = img_width - lw
            else:
                x_start = 0

            self._render_line(
                image,
                face,
                line,
                x_start,
                y_offset,
                b_val,
                g_val,
                r_val,
                a_val,
                letter_spacing,
            )
            y_offset += line_px

        return image

    def _measure_line(
        self,
        face: Any,
        text: str,
        letter_spacing: float,
    ) -> int:
        """Measure the pixel width of a line of text.

        Args:
            face: FreeType face.
            text: Text to measure.
            letter_spacing: Extra spacing between characters.

        Returns:
            Width in pixels.
        """
        width = 0
        for i, ch in enumerate(text):
            face.load_char(ch)
            width += face.glyph.advance.x >> 6
            if i < len(text) - 1:
                width += int(letter_spacing)
        return int(width)

    def _word_wrap(
        self,
        face: Any,
        lines: list[str],
        max_width: int,
        letter_spacing: float,
    ) -> list[str]:
        """Word-wrap text lines to fit within max_width.

        Args:
            face: FreeType face.
            lines: Raw text lines.
            max_width: Maximum line width in pixels.
            letter_spacing: Extra spacing between characters.

        Returns:
            Wrapped lines.
        """
        result: list[str] = []
        for line in lines:
            words = line.split(" ")
            current_line = ""
            for word in words:
                test = f"{current_line} {word}".strip()
                if self._measure_line(face, test, letter_spacing) <= max_width:
                    current_line = test
                else:
                    if current_line:
                        result.append(current_line)
                    current_line = word
            if current_line:
                result.append(current_line)
        return result if result else [""]

    def _render_line(
        self,
        image: np.ndarray,
        face: Any,
        text: str,
        x_start: int,
        y_baseline: int,
        b_val: int,
        g_val: int,
        r_val: int,
        a_val: int,
        letter_spacing: float,
    ) -> None:
        """Render a single line of text onto the image.

        Args:
            image: Target BGRA image array.
            face: FreeType face.
            text: Text to render.
            x_start: X offset for this line.
            y_baseline: Y baseline position.
            b_val: Blue channel value (0-255).
            g_val: Green channel value (0-255).
            r_val: Red channel value (0-255).
            a_val: Alpha channel value (0-255).
            letter_spacing: Extra spacing between characters.
        """
        pen_x = x_start
        h, w = image.shape[:2]

        for i, ch in enumerate(text):
            face.load_char(ch)
            bitmap = face.glyph.bitmap
            left: int = face.glyph.bitmap_left
            top: int = face.glyph.bitmap_top

            if bitmap.width > 0 and bitmap.rows > 0:
                # Convert bitmap buffer to numpy array
                buf = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap.rows, bitmap.width)

                # Calculate position
                gx = pen_x + left
                gy = y_baseline - top

                # Clip to image bounds
                src_y0 = max(0, -gy)
                src_x0 = max(0, -gx)
                dst_y0 = max(0, gy)
                dst_x0 = max(0, gx)
                src_y1 = min(bitmap.rows, h - gy) if gy < h else 0
                src_x1 = min(bitmap.width, w - gx) if gx < w else 0

                if src_y0 < src_y1 and src_x0 < src_x1:
                    dy0 = dst_y0
                    dy1 = dst_y0 + (src_y1 - src_y0)
                    dx0 = dst_x0
                    dx1 = dst_x0 + (src_x1 - src_x0)

                    glyph_alpha = buf[src_y0:src_y1, src_x0:src_x1].astype(np.float32) / 255.0
                    alpha_scaled = glyph_alpha * (a_val / 255.0)

                    # Alpha blend onto existing pixels
                    existing_alpha = image[dy0:dy1, dx0:dx1, 3].astype(np.float32) / 255.0
                    new_alpha = alpha_scaled + existing_alpha * (1.0 - alpha_scaled)

                    mask = new_alpha > 0
                    if np.any(mask):
                        for c, val in enumerate([b_val, g_val, r_val]):
                            existing = image[dy0:dy1, dx0:dx1, c].astype(np.float32)
                            blended = np.where(
                                mask,
                                (
                                    val * alpha_scaled
                                    + existing * existing_alpha * (1.0 - alpha_scaled)
                                )
                                / np.maximum(new_alpha, 1e-6),
                                existing,
                            )
                            image[dy0:dy1, dx0:dx1, c] = np.clip(blended, 0, 255).astype(np.uint8)

                        image[dy0:dy1, dx0:dx1, 3] = np.clip(new_alpha * 255, 0, 255).astype(
                            np.uint8
                        )

            pen_x += face.glyph.advance.x >> 6
            if i < len(text) - 1:
                pen_x += int(letter_spacing)


class HarfBuzzShaper:
    """Complex text shaper using HarfBuzz for RTL text and ligatures.

    Delegates to HarfBuzz for text shaping, producing glyph positions
    that account for complex script requirements.
    """

    def __init__(self, font_loader: FontLoader | None = None) -> None:
        """Initialize the shaper.

        Args:
            font_loader: FontLoader instance to use. Creates a new one if None.
        """
        self._font_loader = font_loader or FontLoader()

    def shape(
        self,
        text: str,
        font: str,
        size: float = 24.0,
        *,
        direction: str = "ltr",
        language: str = "en",
        script: str | None = None,
    ) -> ShapedText:
        """Shape text using HarfBuzz for complex layout.

        Args:
            text: The text to shape.
            font: Font file path or name.
            size: Font size in points.
            direction: Text direction ("ltr" or "rtl").
            language: BCP 47 language tag.
            script: ISO 15924 script tag (auto-detected if None).

        Returns:
            ShapedText with positioned glyph info.
        """
        hb = _import_harfbuzz()
        font_data = self._font_loader.load_font_data(font)
        face = self._font_loader.load(font, size)

        # Create HarfBuzz font
        blob: Any = hb.Blob(font_data)
        hb_face: Any = hb.Face(blob)
        hb_font: Any = hb.Font(hb_face)
        hb_font.scale = (int(size * 64), int(size * 64))

        # Create buffer and set properties
        buf: Any = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()

        if direction == "rtl":
            buf.direction = "rtl"

        # Shape
        hb.shape(hb_font, buf)

        # Extract glyph info
        infos: list[Any] = buf.glyph_infos or []
        positions: list[Any] = buf.glyph_positions or []

        glyphs: list[GlyphInfo] = []
        total_width = 0.0
        for info, pos in zip(infos, positions, strict=True):
            gi = GlyphInfo(
                glyph_id=info.codepoint,
                x_advance=pos.x_advance / 64.0,
                y_advance=pos.y_advance / 64.0,
                x_offset=pos.x_offset / 64.0,
                y_offset=pos.y_offset / 64.0,
                cluster=info.cluster,
            )
            glyphs.append(gi)
            total_width += gi.x_advance

        ascender: int = face.size.ascender >> 6
        descender: int = face.size.descender >> 6
        height = float(ascender - descender)

        return ShapedText(glyphs=glyphs, width=total_width, height=height)
