"""Tests for template/base.py — Template ABC, validation, type errors."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymotion.composition import Composition
from pymotion.template.base import Template, TemplateValidationError


class SimpleTemplate(Template):
    """Test template with basic fields."""

    name: str
    count: int
    ratio: float = 1.5
    enabled: bool = True

    def build(self) -> Composition:
        """Build a minimal composition."""
        return Composition(320, 240, 30, 30)


class PathTemplate(Template):
    """Test template with path field."""

    input_file: Path

    def build(self) -> Composition:
        """Build a minimal composition."""
        return Composition(320, 240, 30, 30)


class TestTemplateInit:
    def test_basic_fields(self) -> None:
        t = SimpleTemplate(name="test", count=5)
        assert t.name == "test"
        assert t.count == 5
        assert t.ratio == 1.5
        assert t.enabled is True

    def test_override_defaults(self) -> None:
        t = SimpleTemplate(name="test", count=5, ratio=2.0, enabled=False)
        assert t.ratio == 2.0
        assert t.enabled is False

    def test_missing_required(self) -> None:
        with pytest.raises(TemplateValidationError, match="required field"):
            SimpleTemplate(name="test")  # missing count

    def test_wrong_type_str(self) -> None:
        with pytest.raises(TemplateValidationError, match="expected str"):
            SimpleTemplate(name=123, count=5)  # type: ignore[arg-type]

    def test_wrong_type_int(self) -> None:
        with pytest.raises(TemplateValidationError, match="expected int"):
            SimpleTemplate(name="test", count="five")  # type: ignore[arg-type]

    def test_wrong_type_float(self) -> None:
        with pytest.raises(TemplateValidationError, match="expected float"):
            SimpleTemplate(name="test", count=5, ratio="bad")  # type: ignore[arg-type]

    def test_wrong_type_bool(self) -> None:
        with pytest.raises(TemplateValidationError, match="expected bool"):
            SimpleTemplate(name="test", count=5, enabled="yes")  # type: ignore[arg-type]

    def test_int_coerced_to_float(self) -> None:
        t = SimpleTemplate(name="test", count=5, ratio=2)
        assert t.ratio == 2.0
        assert isinstance(t.ratio, float)


class TestTemplatePath:
    def test_nonexistent_path(self, tmp_path: Path) -> None:
        with pytest.raises(TemplateValidationError, match="path does not exist"):
            PathTemplate(input_file=tmp_path / "nonexistent.mp4")

    def test_valid_path(self, tmp_path: Path) -> None:
        f = tmp_path / "input.mp4"
        f.write_text("fake")
        t = PathTemplate(input_file=f)
        assert t.input_file == f.resolve()


class TestTemplateBuild:
    def test_build_returns_composition(self) -> None:
        t = SimpleTemplate(name="test", count=5)
        comp = t.build()
        assert isinstance(comp, Composition)


class TestTemplateValidationError:
    def test_message(self) -> None:
        err = TemplateValidationError("foo", "must be positive")
        assert "foo" in str(err)
        assert "must be positive" in str(err)
        assert err.field == "foo"
