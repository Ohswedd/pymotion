"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from pymotion.cli.commands import main


class TestCLI:
    """Test CLI command definitions."""

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "PyMotion" in result.output

    def test_render_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["render", "--help"])
        assert result.exit_code == 0
        assert "--preset" in result.output

    def test_benchmark_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["benchmark", "--help"])
        assert result.exit_code == 0
        assert "--frames" in result.output

    def test_validate_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0

    def test_new_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["new", "--help"])
        assert result.exit_code == 0

    def test_export_frame_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["export-frame", "--help"])
        assert result.exit_code == 0

    def test_new_creates_project(self, tmp_path: Path) -> None:
        runner = CliRunner()
        project = tmp_path / "my_project"
        result = runner.invoke(main, ["new", str(project)])
        assert result.exit_code == 0
        assert project.exists()
        assert (project / "comp.py").exists()
        assert (project / "assets").is_dir()

    def test_new_existing_dir_fails(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["new", str(tmp_path)])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_render_missing_file(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["render", "/nonexistent.py"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_validate_missing_file(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "/nonexistent.py"])
        assert result.exit_code != 0
