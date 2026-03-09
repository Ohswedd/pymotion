"""Unit tests for pymotion.security.validation — all 4 validators."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pymotion.security.validation import (
    sanitize_text,
    validate_asset_magic,
    validate_color,
    validate_path,
)
from pymotion.utils.color import Color


class TestValidatePath:
    """Test path validation and traversal prevention."""

    def test_valid_path(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = validate_path(str(f), [tmp_path])
        assert result == f.resolve()

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="outside allowed"):
            validate_path("/etc/passwd", [tmp_path])

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_path(str(tmp_path / "nonexistent.txt"), [tmp_path])

    def test_symlink_outside_base(self, tmp_path: Path) -> None:
        # Create a symlink pointing outside the base directory
        target = Path(tempfile.gettempdir()) / "outside_target.txt"
        target.write_text("secret")
        link = tmp_path / "sneaky_link"
        link.symlink_to(target)
        try:
            with pytest.raises(ValueError, match="outside allowed"):
                validate_path(str(link), [tmp_path])
        finally:
            target.unlink()
            link.unlink(missing_ok=True)


class TestValidateColor:
    """Test color validation."""

    def test_valid_hex(self) -> None:
        c = validate_color("#FF0000")
        assert isinstance(c, Color)
        assert c.r == 1.0

    def test_valid_name(self) -> None:
        c = validate_color("red")
        assert c.r == 1.0

    def test_invalid_color(self) -> None:
        with pytest.raises(ValueError):
            validate_color("notacolor")


class TestValidateAssetMagic:
    """Test file magic byte validation."""

    def test_png_magic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.png"
        # Write PNG magic bytes
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        validate_asset_magic(f, ["image"])

    def test_jpeg_magic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        validate_asset_magic(f, ["image"])

    def test_wrong_type(self, tmp_path: Path) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"\x00\x01\x02\x03" + b"\x00" * 100)
        with pytest.raises(ValueError, match="does not match"):
            validate_asset_magic(f, ["image"])

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_asset_magic(tmp_path / "nope.png", ["image"])


class TestSanitizeText:
    """Test text sanitization."""

    def test_normal_text(self) -> None:
        result = sanitize_text("Hello World")
        assert result == "Hello World"

    def test_strips_null_bytes(self) -> None:
        result = sanitize_text("Hello\x00World")
        assert result == "HelloWorld"

    def test_strips_control_chars(self) -> None:
        result = sanitize_text("Hello\x01\x02World")
        assert result == "HelloWorld"

    def test_preserves_newlines(self) -> None:
        result = sanitize_text("Hello\nWorld")
        assert result == "Hello\nWorld"

    def test_preserves_tabs(self) -> None:
        result = sanitize_text("Hello\tWorld")
        assert result == "Hello\tWorld"

    def test_max_length_exceeded(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum"):
            sanitize_text("x" * 200, max_length=100)

    def test_max_length_ok(self) -> None:
        result = sanitize_text("x" * 100, max_length=100)
        assert len(result) == 100
