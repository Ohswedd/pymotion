"""Color parsing, conversion, and gradient utilities.

Provides the Color dataclass used throughout PyMotion for representing
colors internally as float RGBA values (0.0-1.0).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

# CSS named colors (subset of most common ones)
_CSS_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "pink": (255, 192, 203),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "gold": (255, 215, 0),
    "navy": (0, 0, 128),
    "teal": (0, 128, 128),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "lime": (0, 255, 0),
    "aqua": (0, 255, 255),
    "transparent": (0, 0, 0),  # alpha handled separately
}

_HEX6_RE = re.compile(r"^#([0-9a-fA-F]{6})$")
_HEX8_RE = re.compile(r"^#([0-9a-fA-F]{8})$")
_HEX3_RE = re.compile(r"^#([0-9a-fA-F]{3})$")

ColorInput = Union["Color", str, tuple[int, int, int], tuple[int, int, int, int]]


@dataclass(frozen=True)
class Color:
    """Immutable RGBA color with float components in range [0.0, 1.0].

    Args:
        r: Red channel (0.0-1.0).
        g: Green channel (0.0-1.0).
        b: Blue channel (0.0-1.0).
        a: Alpha channel (0.0-1.0), defaults to 1.0.
    """

    r: float
    g: float
    b: float
    a: float = 1.0

    def __post_init__(self) -> None:
        """Validate color component ranges."""
        for name, val in [("r", self.r), ("g", self.g), ("b", self.b), ("a", self.a)]:
            if not 0.0 <= val <= 1.0:
                msg = f"Color component '{name}' must be between 0.0 and 1.0, got {val}"
                raise ValueError(msg)

    def to_uint8(self) -> tuple[int, int, int, int]:
        """Convert to 8-bit RGBA tuple (0-255).

        Returns:
            Tuple of (r, g, b, a) as integers in range [0, 255].
        """
        return (
            round(self.r * 255),
            round(self.g * 255),
            round(self.b * 255),
            round(self.a * 255),
        )

    def to_bgra_uint8(self) -> tuple[int, int, int, int]:
        """Convert to 8-bit BGRA tuple (0-255) for internal frame format.

        Returns:
            Tuple of (b, g, r, a) as integers in range [0, 255].
        """
        return (
            round(self.b * 255),
            round(self.g * 255),
            round(self.r * 255),
            round(self.a * 255),
        )

    def to_hex(self) -> str:
        """Convert to hex string (#RRGGBB or #RRGGBBAA if alpha < 1.0).

        Returns:
            Hex color string.
        """
        r, g, b, a = self.to_uint8()
        if a == 255:
            return f"#{r:02X}{g:02X}{b:02X}"
        return f"#{r:02X}{g:02X}{b:02X}{a:02X}"

    @staticmethod
    def from_hex(hex_str: str) -> Color:
        """Parse a hex color string.

        Args:
            hex_str: Color string in #RGB, #RRGGBB, or #RRGGBBAA format.

        Returns:
            Parsed Color instance.

        Raises:
            ValueError: If the hex string is invalid.
        """
        match3 = _HEX3_RE.match(hex_str)
        if match3:
            h = match3.group(1)
            r = int(h[0] * 2, 16)
            g = int(h[1] * 2, 16)
            b = int(h[2] * 2, 16)
            return Color(r / 255, g / 255, b / 255)

        match6 = _HEX6_RE.match(hex_str)
        if match6:
            h = match6.group(1)
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return Color(r / 255, g / 255, b / 255)

        match8 = _HEX8_RE.match(hex_str)
        if match8:
            h = match8.group(1)
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            a = int(h[6:8], 16)
            return Color(r / 255, g / 255, b / 255, a / 255)

        msg = f"Invalid hex color string: '{hex_str}'"
        raise ValueError(msg)

    @staticmethod
    def from_name(name: str) -> Color:
        """Parse a CSS color name.

        Args:
            name: CSS color name (case-insensitive).

        Returns:
            Parsed Color instance.

        Raises:
            ValueError: If the color name is not recognized.
        """
        lower = name.lower().strip()
        if lower not in _CSS_COLORS:
            msg = f"Unknown color name: '{name}'"
            raise ValueError(msg)
        r, g, b = _CSS_COLORS[lower]
        alpha = 0.0 if lower == "transparent" else 1.0
        return Color(r / 255, g / 255, b / 255, alpha)

    @staticmethod
    def parse(value: ColorInput) -> Color:
        """Parse a color from various input formats.

        Accepts:
            - Color instance (returned as-is)
            - Hex string: "#RRGGBB", "#RRGGBBAA", "#RGB"
            - CSS color name: "red", "blue", etc.
            - RGB tuple: (r, g, b) with values 0-255
            - RGBA tuple: (r, g, b, a) with values 0-255

        Args:
            value: Color in any supported format.

        Returns:
            Parsed Color instance.

        Raises:
            ValueError: If the value cannot be parsed as a color.
        """
        if isinstance(value, Color):
            return value
        if isinstance(value, str):
            if value.startswith("#"):
                return Color.from_hex(value)
            return Color.from_name(value)
        if isinstance(value, tuple):
            if len(value) == 3:
                r, g, b = value
                return Color(r / 255, g / 255, b / 255)
            if len(value) == 4:
                r, g, b, a = value
                return Color(r / 255, g / 255, b / 255, a / 255)
        msg = f"Cannot parse color from: {value!r}"
        raise ValueError(msg)
