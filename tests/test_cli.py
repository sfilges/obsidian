"""Tests for obsidian.cli module."""

from unittest.mock import MagicMock, patch

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

    def test_import_command_exists(self):
        """Import command should be registered."""
        result = runner.invoke(app, ["--help"])

        assert "import" in result.stdout


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_help(self):
        """Config command should have help text."""
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "configuration" in result.stdout.lower() or "config" in result.stdout.lower()


class TestImportCommand:
    """Tests for the import command ensuring it wraps core functions."""

    @patch("obsidian.import_doc.import_file")
    @patch("obsidian.cli.get_current_config")
    def test_import_file(self, mock_config, mock_import_file, tmp_path):
        """Test importing a single file delegates to import_file."""
        # Setup
        mock_conf = MagicMock()
        mock_conf.vault_path = tmp_path / "vault"
        mock_config.return_value = mock_conf

        # Create a dummy file to import
        input_file = tmp_path / "test.pdf"
        input_file.touch()

        # Run command
        result = runner.invoke(app, ["import", str(input_file)])

        # Verify
        assert result.exit_code == 0
        assert "Importing from" in result.stdout

        # Check delegation
        mock_import_file.assert_called_once()
        args, kwargs = mock_import_file.call_args
        assert args[0] == input_file.resolve()
        assert kwargs["extract"] is False

    @patch("obsidian.import_doc.bulk_import")
    @patch("obsidian.cli.get_current_config")
    def test_import_directory(self, mock_config, mock_bulk_import, tmp_path):
        """Test importing a directory delegates to bulk_import."""
        # Setup
        mock_conf = MagicMock()
        mock_conf.vault_path = tmp_path / "vault"
        mock_config.return_value = mock_conf

        # Create a dummy directory
        input_dir = tmp_path / "docs"
        input_dir.mkdir()

        # Run command
        result = runner.invoke(app, ["import", str(input_dir)])

        # Verify
        assert result.exit_code == 0

        # Check delegation
        mock_bulk_import.assert_called_once()
        args, kwargs = mock_bulk_import.call_args
        assert args[0] == input_dir.resolve()
        assert kwargs["extract"] is False

    @patch("obsidian.import_doc.import_file")
    @patch("obsidian.cli.get_current_config")
    def test_import_url(self, mock_config, mock_import_file, tmp_path):
        """Test importing a URL delegates to import_file."""
        # Setup
        mock_conf = MagicMock()
        mock_conf.vault_path = tmp_path / "vault"
        mock_config.return_value = mock_conf

        url = "https://example.com/article"

        # Run command
        result = runner.invoke(app, ["import", url])

        # Verify
        assert result.exit_code == 0

        # Check delegation
        mock_import_file.assert_called_once()
        args, kwargs = mock_import_file.call_args
        assert args[0] == url
        assert kwargs["extract"] is False

    @patch("obsidian.import_doc.import_file")
    @patch("obsidian.cli.get_current_config")
    def test_import_with_extract(self, mock_config, mock_import_file, tmp_path):
        """Test import with --extract flag passes extract=True."""
        # Setup
        mock_conf = MagicMock()
        mock_conf.vault_path = tmp_path / "vault"
        mock_config.return_value = mock_conf

        input_file = tmp_path / "test.docx"
        input_file.touch()

        # Run command
        result = runner.invoke(app, ["import", str(input_file), "--extract"])

        # Verify
        assert result.exit_code == 0
        assert "Metadata extraction enabled" in result.stdout

        # Check delegation
        mock_import_file.assert_called_once()
        args, kwargs = mock_import_file.call_args
        assert kwargs["extract"] is True
