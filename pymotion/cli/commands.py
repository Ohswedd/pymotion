"""CLI command definitions — render, export-frame, preview, benchmark, validate, new.

Provides the main CLI entry point using Click.
"""

from __future__ import annotations

import importlib.util
import sys
import time
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


@main.command()
@click.argument("file")
@click.option("--port", "-p", default=4321, type=int, help="Preview server port.")
@click.option("--frame", "-f", default=0, type=int, help="Frame to preview.")
@click.option("--output", "-o", default="preview.png", help="Output preview image.")
def preview(file: str, port: int, frame: int, output: str) -> None:
    """Preview a composition frame (basic, no hot-reload).

    Renders a single frame and saves it as a PNG for quick visual
    inspection. A full hot-reload preview server will be added later.
    """
    from pymotion.composition import Composition

    comp = _load_composition(file)
    if not isinstance(comp, Composition):
        msg = f"'comp' must be a Composition instance, got {type(comp).__name__}"
        raise click.ClickException(msg)

    result = comp.export_frame(frame, output)
    click.echo(f"Preview frame {frame} saved to: {result}")
    click.echo(f"(Full preview server on port {port} will be available in a future release)")


@main.command()
@click.argument("file")
@click.option("--frames", "-n", default=30, type=int, help="Number of frames to benchmark.")
def benchmark(file: str, frames: int) -> None:
    """Profile render performance for a composition."""
    from pymotion.composition import Composition

    comp = _load_composition(file)
    if not isinstance(comp, Composition):
        msg = f"'comp' must be a Composition instance, got {type(comp).__name__}"
        raise click.ClickException(msg)

    click.echo(f"Benchmarking {frames} frames...")
    start = time.perf_counter()

    for i in range(frames):
        comp._render_frame(i)  # noqa: SLF001

    elapsed = time.perf_counter() - start
    fps = frames / elapsed if elapsed > 0 else 0
    ms_per_frame = (elapsed / frames * 1000) if frames > 0 else 0

    click.echo(f"Rendered {frames} frames in {elapsed:.2f}s")
    click.echo(f"  {fps:.1f} fps | {ms_per_frame:.1f} ms/frame")


@main.command()
@click.argument("file")
def validate(file: str) -> None:
    """Validate a composition without rendering."""
    from pymotion.composition import Composition

    comp = _load_composition(file)
    if not isinstance(comp, Composition):
        msg = f"'comp' must be a Composition instance, got {type(comp).__name__}"
        raise click.ClickException(msg)

    # Basic validation checks
    errors: list[str] = []

    if comp.duration <= 0:
        errors.append("Composition duration must be > 0")

    w = comp.resolution.width
    h = comp.resolution.height
    if w <= 0 or h <= 0:
        errors.append(f"Invalid resolution: {w}x{h}")

    if comp.fps <= 0:
        errors.append(f"Invalid FPS: {comp.fps}")

    if not comp.tracks:
        errors.append("Composition has no tracks")

    if errors:
        for err in errors:
            click.echo(f"  ERROR: {err}", err=True)
        raise click.ClickException(f"Validation failed with {len(errors)} error(s)")

    click.echo(f"Composition valid: {w}x{h} @ {comp.fps}fps, {comp.duration} frames")
    click.echo(f"  Tracks: {len(comp.tracks)}")


@main.command()
def doctor() -> None:
    """Check system dependencies and environment health."""
    import shutil

    all_ok = True

    def _check(name: str, found: bool, detail: str = "") -> None:
        nonlocal all_ok
        status = "OK" if found else "MISSING"
        if not found:
            all_ok = False
        msg = f"  [{status}] {name}"
        if detail:
            msg += f" — {detail}"
        click.echo(msg)

    click.echo("PyMotion Doctor")
    click.echo("=" * 40)

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    _check(f"Python {py_ver}", py_ok, "requires >= 3.11" if not py_ok else "")

    # FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    _check("ffmpeg", ffmpeg_path is not None, str(ffmpeg_path or ""))

    # pkg-config
    pkgconfig_path = shutil.which("pkg-config")
    _check("pkg-config", pkgconfig_path is not None)

    # Core Python deps
    core_deps = ["numpy", "PIL", "cairo", "structlog", "click"]
    for dep in core_deps:
        try:
            __import__(dep)
            _check(dep, found=True)
        except ImportError:
            _check(dep, found=False)

    # Optional deps
    click.echo("\nOptional dependencies:")
    optional_deps = [
        ("freetype", "Text rendering"),
        ("uharfbuzz", "Complex text layout"),
        ("moderngl", "3D rendering"),
        ("librosa", "Audio analysis"),
        ("pedalboard", "Audio effects"),
        ("httpx", "Google Fonts download"),
    ]
    for dep, desc in optional_deps:
        try:
            __import__(dep)
            _check(f"{dep} ({desc})", found=True)
        except ImportError:
            _check(f"{dep} ({desc})", found=False)

    click.echo()
    if all_ok:
        click.echo("All checks passed!")
    else:
        click.echo("Some checks failed. Install missing dependencies.")
        raise SystemExit(1)


@main.command()
@click.argument("directory")
def new(directory: str) -> None:
    """Scaffold a new PyMotion project."""
    project_dir = Path(directory).resolve()

    if project_dir.exists():
        msg = f"Directory already exists: {project_dir}"
        raise click.ClickException(msg)

    project_dir.mkdir(parents=True)
    (project_dir / "assets").mkdir()

    comp_file = project_dir / "comp.py"
    comp_file.write_text(
        '"""PyMotion composition."""\n'
        "\n"
        "from pymotion import Composition, ColorClip, Resolution, Color\n"
        "\n"
        "comp = Composition(\n"
        "    width=1920,\n"
        "    height=1080,\n"
        "    fps=30,\n"
        "    duration=90,\n"
        ")\n"
        "\n"
        'bg = ColorClip(color=Color.parse("#1a1a2e"))\n'
        "comp.add_clip(bg, track=0)\n"
    )

    click.echo(f"Created new project at: {project_dir}")
    click.echo(f"  Edit {comp_file.name} and run: pymotion render {comp_file.name}")
