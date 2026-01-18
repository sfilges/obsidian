"""Tests for the import_doc module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestGetConverter:
    """Tests for the get_converter function."""

    def test_get_converter_returns_document_converter(self):
        """get_converter should return a DocumentConverter instance."""
        from obsidian.import_doc import get_converter

        converter = get_converter()
        assert converter is not None

    def test_get_converter_configures_pdf_pipeline(self):
        """get_converter should configure PDF pipeline options."""
        with patch("obsidian.import_doc.DocumentConverter") as mock_dc:
            from obsidian.import_doc import get_converter

            get_converter()

            # Should be called with format_options containing PDF config
            mock_dc.assert_called_once()
            call_kwargs = mock_dc.call_args[1]
            assert "format_options" in call_kwargs


class TestImportFile:
    """Tests for the import_file function."""

    def test_import_file_creates_markdown_output(self):
        """import_file should create a markdown file in the vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            # Mock the converter and document
            mock_doc = MagicMock()
            mock_doc.name = "Test Document"
            mock_doc.export_to_markdown.return_value = "# Test Content\n\nSome text here."

            mock_result = MagicMock()
            mock_result.document = mock_doc

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                with patch("obsidian.import_doc.EXTRACTOR_BACKEND", "none"):
                    from obsidian.import_doc import import_file

                    import_file("/fake/source.pdf", vault_path)

            # Check that a markdown file was created
            md_files = list(vault_path.glob("*.md"))
            assert len(md_files) == 1
            assert "Test Document" in md_files[0].name

    def test_import_file_adds_frontmatter(self):
        """import_file should add YAML frontmatter to the output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            mock_doc = MagicMock()
            mock_doc.name = "Test Doc"
            mock_doc.export_to_markdown.return_value = "Content here"

            mock_result = MagicMock()
            mock_result.document = mock_doc

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                with patch("obsidian.import_doc.EXTRACTOR_BACKEND", "none"):
                    from obsidian.import_doc import import_file

                    import_file("/fake/source.pdf", vault_path)

            md_files = list(vault_path.glob("*.md"))
            content = md_files[0].read_text()

            # Check frontmatter markers
            assert content.startswith("---\n")
            assert "---\n\n" in content
            # Check status is pending by default
            assert "status: pending" in content

    def test_import_file_with_extract_sets_active_status(self):
        """import_file with extract=True should set status to active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            mock_doc = MagicMock()
            mock_doc.name = "Test Doc"
            mock_doc.export_to_markdown.return_value = "Content here"

            mock_result = MagicMock()
            mock_result.document = mock_doc

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            # Mock the extraction
            mock_metadata = MagicMock()
            mock_metadata.title = "Extracted Title"
            mock_metadata.authors = ["John Doe"]
            mock_metadata.summary = "A brief summary"
            mock_metadata.tags = ["test", "document"]

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                with patch("obsidian.import_doc.EXTRACTOR_BACKEND", "ollama"):
                    with patch("obsidian.import_doc.extract_metadata", return_value=mock_metadata):
                        from obsidian.import_doc import import_file

                        import_file("/fake/source.pdf", vault_path, extract=True)

            md_files = list(vault_path.glob("*.md"))
            content = md_files[0].read_text()

            # Check status is active after extraction
            assert "status: active" in content

    def test_import_file_handles_url_source(self):
        """import_file should handle URL sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            mock_doc = MagicMock()
            mock_doc.name = "Web Article"
            mock_doc.export_to_markdown.return_value = "Web content"

            mock_result = MagicMock()
            mock_result.document = mock_doc

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                with patch("obsidian.import_doc.EXTRACTOR_BACKEND", "none"):
                    from obsidian.import_doc import import_file

                    import_file("https://example.com/article", vault_path)

            md_files = list(vault_path.glob("*.md"))
            content = md_files[0].read_text()

            # Should have web-clip tag
            assert "web-clip" in content

    def test_import_file_sanitizes_filename(self):
        """import_file should sanitize filename to remove illegal characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            mock_doc = MagicMock()
            mock_doc.name = "Test/Doc:With*Illegal?Chars"
            mock_doc.export_to_markdown.return_value = "Content"

            mock_result = MagicMock()
            mock_result.document = mock_doc

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                with patch("obsidian.import_doc.EXTRACTOR_BACKEND", "none"):
                    from obsidian.import_doc import import_file

                    import_file("/fake/source.pdf", vault_path)

            md_files = list(vault_path.glob("*.md"))
            # Filename should not contain illegal characters
            filename = md_files[0].name
            assert "/" not in filename
            assert ":" not in filename
            assert "*" not in filename
            assert "?" not in filename

    def test_import_file_handles_conversion_error(self):
        """import_file should handle conversion errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            mock_converter = MagicMock()
            mock_converter.convert.side_effect = Exception("Conversion failed")

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                from obsidian.import_doc import import_file

                # Should not raise, just log the error
                import_file("/fake/source.pdf", vault_path)

            # No files should be created
            md_files = list(vault_path.glob("*.md"))
            assert len(md_files) == 0


class TestBulkImport:
    """Tests for the bulk_import function."""

    def test_bulk_import_processes_all_supported_files(self):
        """bulk_import should process all supported file types in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create test files
            (input_dir / "doc1.pdf").touch()
            (input_dir / "doc2.docx").touch()
            (input_dir / "doc3.txt").touch()  # Not supported

            mock_doc = MagicMock()
            mock_doc.name = "Test"
            mock_doc.export_to_markdown.return_value = "Content"

            mock_result = MagicMock()
            mock_result.document = mock_doc

            mock_converter = MagicMock()
            mock_converter.convert.return_value = mock_result

            with patch("obsidian.import_doc.get_converter", return_value=mock_converter):
                with patch("obsidian.import_doc.EXTRACTOR_BACKEND", "none"):
                    from obsidian.import_doc import bulk_import

                    bulk_import(input_dir, output_dir)

            # Should have called convert for pdf and docx (not txt)
            assert mock_converter.convert.call_count == 2

    def test_bulk_import_handles_nonexistent_directory(self):
        """bulk_import should handle nonexistent input directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            from obsidian.import_doc import bulk_import

            # Should not raise, just log error
            bulk_import(Path("/nonexistent/path"), output_dir)

    def test_bulk_import_handles_empty_directory(self):
        """bulk_import should handle directory with no supported files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            from obsidian.import_doc import bulk_import

            # Should not raise
            bulk_import(input_dir, output_dir)


class TestSupportedExtensions:
    """Tests for supported file extensions."""

    def test_supported_extensions_includes_common_formats(self):
        """SUPPORTED_EXTENSIONS should include common document formats."""
        from obsidian.import_doc import SUPPORTED_EXTENSIONS

        expected = {".pdf", ".docx", ".html", ".htm"}
        assert expected.issubset(SUPPORTED_EXTENSIONS)
