"""CLI command definitions — render and export-frame for Phase 0.1.

Provides the main CLI entry point using Click.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import click

from pymotion.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _load_composition(file_path: str) -> object:
    """Load a composition from a Python file.

    The file must define a variable named 'comp' that is a Composition.

    Args:
        file_path: Path to the Python file.

    Returns:
        The Composition object.

    Raises:
        click.ClickException: If the file cannot be loaded.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        msg = f"File not found: {path}"
        raise click.ClickException(msg)

    spec = importlib.util.spec_from_file_location("user_comp", str(path))
    if spec is None or spec.loader is None:
        msg = f"Cannot load module from: {path}"
        raise click.ClickException(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules["user_comp"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr,unused-ignore]

    comp = getattr(module, "comp", None)
    if comp is None:
        msg = f"No 'comp' variable found in {path}. Define a Composition named 'comp'."
        raise click.ClickException(msg)

    return comp


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging.")
def main(debug: bool) -> None:
    """PyMotion — code-first video generation framework."""
    configure_logging(debug=debug)


@main.command()
@click.argument("file")
@click.option("--output", "-o", default="output.mp4", help="Output file path.")
@click.option("--preset", "-p", default="h264_1080p", help="Output preset name.")
@click.option("--start", default=0, type=int, help="Start frame.")
@click.option("--end", default=None, type=int, help="End frame.")
def render(file: str, output: str, preset: str, start: int, end: int | None) -> None:
    """Render a composition to video."""
    from pymotion.composition import Composition

    comp = _load_composition(file)
    if not isinstance(comp, Composition):
        msg = f"'comp' must be a Composition instance, got {type(comp).__name__}"
        raise click.ClickException(msg)

    result = comp.render(output, preset=preset, start=start, end=end)
    click.echo(f"Rendered to: {result}")


@main.command(name="export-frame")
@click.argument("file")
@click.option("--frame", "-f", default=0, type=int, help="Frame number to export.")
@click.option("--output", "-o", default="frame.png", help="Output PNG path.")
def export_frame(file: str, frame: int, output: str) -> None:
    """Export a single frame as PNG."""
    from pymotion.composition import Composition

    comp = _load_composition(file)
    if not isinstance(comp, Composition):
        msg = f"'comp' must be a Composition instance, got {type(comp).__name__}"
        raise click.ClickException(msg)

    result = comp.export_frame(frame, output)
    click.echo(f"Exported frame {frame} to: {result}")
