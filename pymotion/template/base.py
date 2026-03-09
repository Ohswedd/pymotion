"""Template abstract base class for batch video generation.

Templates declare typed fields that are validated at instantiation time.
Subclasses implement build() to produce a Composition.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, get_type_hints

from pymotion.composition import Composition
from pymotion.security.validation import validate_path
from pymotion.utils.color import Color
from pymotion.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateValidationError(ValueError):
    """Raised when template field validation fails.

    Args:
        field: Name of the invalid field.
        message: Description of the validation failure.
    """

    def __init__(self, field: str, message: str) -> None:
        """Initialize validation error.

        Args:
            field: Field name.
            message: Error description.
        """
        self.field = field
        super().__init__(f"Template field '{field}': {message}")


class Template(ABC):
    """Abstract base class for reusable video templates.

    Subclasses declare expected parameters as class-level type annotations.
    Fields are validated during __init__ and must match their declared types.

    Example::

        class ProductTemplate(Template):
            product_name: str
            price: float
            brand_color: str = "#FF0000"

            def build(self) -> Composition:
                comp = Composition(1920, 1080, 30, 150)
                # ... add clips ...
                return comp
    """

    # Fields to exclude from validation (internal / class-level only)
    _EXCLUDED_FIELDS: ClassVar[set[str]] = {"_EXCLUDED_FIELDS"}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize template with validated field values.

        Args:
            **kwargs: Field values matching class annotations.

        Raises:
            TemplateValidationError: If a field value is invalid.
        """
        hints = get_type_hints(type(self))

        # Set defaults from class attributes
        for name, hint in hints.items():
            if name.startswith("_"):
                continue
            if name in kwargs:
                value = kwargs[name]
            elif hasattr(type(self), name):
                value = getattr(type(self), name)
            else:
                raise TemplateValidationError(name, "required field not provided")

            # Validate and set
            validated = self._validate_field(name, value, hint)
            setattr(self, name, validated)

        # Check for unexpected kwargs
        for key in kwargs:
            if key not in hints:
                logger.warning("unknown_template_field", field=key)

    def _validate_field(self, name: str, value: Any, hint: Any) -> Any:
        """Validate a single field value against its type hint.

        Args:
            name: Field name.
            value: Field value.
            hint: Expected type hint.

        Returns:
            The validated (possibly coerced) value.

        Raises:
            TemplateValidationError: If validation fails.
        """
        # Handle Path fields — validate existence
        if hint is Path or (isinstance(hint, type) and issubclass(hint, Path)):
            if not isinstance(value, (str, Path)):
                raise TemplateValidationError(
                    name, f"expected Path or str, got {type(value).__name__}"
                )
            path = Path(value).resolve()
            if not path.exists():
                raise TemplateValidationError(name, f"path does not exist: {path}")
            validate_path(path, [path.parent])
            return path

        # Handle numeric fields — must be the right type
        if hint is float:
            if not isinstance(value, (int, float)):
                raise TemplateValidationError(name, f"expected float, got {type(value).__name__}")
            return float(value)

        if hint is int:
            if not isinstance(value, int):
                raise TemplateValidationError(name, f"expected int, got {type(value).__name__}")
            return value

        # Handle str fields
        if hint is str:
            if not isinstance(value, str):
                raise TemplateValidationError(name, f"expected str, got {type(value).__name__}")
            return value

        # Handle bool fields
        if hint is bool:
            if not isinstance(value, bool):
                raise TemplateValidationError(name, f"expected bool, got {type(value).__name__}")
            return value

        # Handle Color fields
        if hint is Color or (isinstance(hint, type) and issubclass(hint, Color)):
            return Color.parse(value)

        # For other types, basic isinstance check if hint is a type
        if isinstance(hint, type) and not isinstance(value, hint):
            raise TemplateValidationError(
                name, f"expected {hint.__name__}, got {type(value).__name__}"
            )

        return value

    @abstractmethod
    def build(self) -> Composition:
        """Build and return the Composition for this template instance.

        Returns:
            A fully configured Composition ready to render.
        """
        ...

    def render(self, output: str | Path, preset: str = "h264_1080p", **kwargs: Any) -> Path:
        """Convenience method: build() then render to file.

        Args:
            output: Output file path.
            preset: Export preset name.
            **kwargs: Additional render keyword arguments.

        Returns:
            Path to the rendered file.
        """
        comp = self.build()
        return comp.render(output, preset=preset, **kwargs)
