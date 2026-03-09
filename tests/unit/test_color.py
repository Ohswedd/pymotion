"""Unit tests for pymotion.utils.color — Color class, parsing, conversion."""

from __future__ import annotations

import pytest

from pymotion.utils.color import Color


class TestColorCreation:
    """Test Color dataclass creation and validation."""

    def test_default_alpha(self) -> None:
        c = Color(0.5, 0.5, 0.5)
        assert c.a == 1.0

    def test_explicit_alpha(self) -> None:
        c = Color(0.5, 0.5, 0.5, 0.5)
        assert c.a == 0.5

    def test_invalid_range(self) -> None:
        with pytest.raises(ValueError, match="Color component"):
            Color(1.5, 0.0, 0.0)

    def test_negative_value(self) -> None:
        with pytest.raises(ValueError, match="Color component"):
            Color(-0.1, 0.0, 0.0)

    def test_frozen(self) -> None:
        c = Color(0.0, 0.0, 0.0)
        with pytest.raises(AttributeError):
            c.r = 1.0  # type: ignore[misc]


class TestColorConversion:
    """Test Color conversion methods."""

    def test_to_uint8(self) -> None:
        c = Color(1.0, 0.5, 0.0, 1.0)
        r, g, b, a = c.to_uint8()
        assert r == 255
        assert 127 <= g <= 128
        assert b == 0
        assert a == 255

    def test_to_bgra_uint8(self) -> None:
        c = Color(1.0, 0.0, 0.0, 1.0)  # Red
        b, g, r, a = c.to_bgra_uint8()
        assert r == 255
        assert g == 0
        assert b == 0
        assert a == 255

    def test_to_hex(self) -> None:
        c = Color(1.0, 0.0, 0.0)
        assert c.to_hex() == "#FF0000"

    def test_to_hex_with_alpha(self) -> None:
        c = Color(1.0, 0.0, 0.0, 0.5)
        hex_str = c.to_hex()
        assert hex_str.startswith("#FF0000")
        assert len(hex_str) == 9


class TestColorParsing:
    """Test Color parsing from various formats."""

    def test_parse_hex6(self) -> None:
        c = Color.from_hex("#FF0000")
        assert c.r == 1.0
        assert c.g == 0.0
        assert c.b == 0.0

    def test_parse_hex8(self) -> None:
        c = Color.from_hex("#FF000080")
        assert c.r == 1.0
        assert abs(c.a - 128 / 255) < 0.01

    def test_parse_hex3(self) -> None:
        c = Color.from_hex("#F00")
        assert c.r == 1.0
        assert c.g == 0.0

    def test_parse_invalid_hex(self) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            Color.from_hex("#ZZZZZZ")

    def test_parse_name(self) -> None:
        c = Color.from_name("red")
        assert c.r == 1.0
        assert c.g == 0.0
        assert c.b == 0.0

    def test_parse_name_case_insensitive(self) -> None:
        c = Color.from_name("RED")
        assert c.r == 1.0

    def test_parse_unknown_name(self) -> None:
        with pytest.raises(ValueError, match="Unknown color"):
            Color.from_name("unicorn")

    def test_parse_color_instance(self) -> None:
        original = Color(0.5, 0.5, 0.5)
        parsed = Color.parse(original)
        assert parsed is original

    def test_parse_tuple_rgb(self) -> None:
        c = Color.parse((255, 0, 0))
        assert c.r == 1.0

    def test_parse_tuple_rgba(self) -> None:
        c = Color.parse((255, 0, 0, 128))
        assert c.r == 1.0
        assert abs(c.a - 128 / 255) < 0.01

    def test_parse_hex_string(self) -> None:
        c = Color.parse("#00FF00")
        assert c.g == 1.0

    def test_parse_name_string(self) -> None:
        c = Color.parse("blue")
        assert c.b == 1.0

    def test_parse_invalid(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            Color.parse(12345)  # type: ignore[arg-type]
