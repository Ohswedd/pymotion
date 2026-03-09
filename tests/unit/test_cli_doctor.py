"""Tests for the CLI doctor command."""

from __future__ import annotations

from click.testing import CliRunner

from pymotion.cli.commands import main


class TestDoctorCommand:
    """Tests for the pymotion doctor command."""

    def test_doctor_runs(self) -> None:
        """Doctor command runs and produces output."""
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert "PyMotion Doctor" in result.output
        assert "Python" in result.output
        assert "ffmpeg" in result.output

    def test_doctor_checks_numpy(self) -> None:
        """Doctor command checks for numpy."""
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert "numpy" in result.output

    def test_doctor_checks_optional_deps(self) -> None:
        """Doctor command lists optional dependencies."""
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert "Optional dependencies:" in result.output
