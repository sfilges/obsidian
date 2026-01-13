"""Tests for obsidian.cli module."""

from typer.testing import CliRunner

from obsidian.cli import app

runner = CliRunner()


class TestCLIBasics:
    """Basic CLI functionality tests."""

    def test_help_command(self):
        """CLI should display help without errors."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Obsidian RAG CLI" in result.stdout

    def test_config_command_exists(self):
        """Config command should be registered."""
        result = runner.invoke(app, ["--help"])

        assert "config" in result.stdout

    def test_lance_command_exists(self):
        """Lance command should be registered."""
        result = runner.invoke(app, ["--help"])

        assert "lance" in result.stdout

    def test_serve_command_exists(self):
        """Serve command should be registered."""
        result = runner.invoke(app, ["--help"])

        assert "serve" in result.stdout


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_help(self):
        """Config command should have help text."""
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "configuration" in result.stdout.lower() or "config" in result.stdout.lower()
