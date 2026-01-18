"""Tests for the MCP server module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSearchNotes:
    """Tests for the search_notes MCP tool."""

    def test_search_notes_returns_error_when_db_not_initialized(self):
        """search_notes should return error message when table is None."""
        with patch("obsidian.server.get_table", return_value=None):
            from obsidian.server import search_notes

            result = search_notes("test query")
            assert "Error" in result
            assert "not initialized" in result

    def test_search_notes_returns_no_matches_message(self):
        """search_notes should return appropriate message when no results found."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_search.limit.return_value.select.return_value.to_list.return_value = []
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            with patch("obsidian.server.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_model.encode.return_value.tolist.return_value = [0.1] * 768
                mock_get_model.return_value = mock_model

                from obsidian.server import search_notes

                result = search_notes("nonexistent topic")
                assert "No matching notes found" in result

    def test_search_notes_applies_query_prefix(self):
        """search_notes should apply 'search_query: ' prefix for Nomic."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_search.limit.return_value.select.return_value.to_list.return_value = []
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            with patch("obsidian.server.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_model.encode.return_value.tolist.return_value = [0.1] * 768
                mock_get_model.return_value = mock_model

                from obsidian.server import search_notes

                search_notes("my query")

                # Check that the query was prefixed
                mock_model.encode.assert_called_once()
                call_arg = mock_model.encode.call_args[0][0]
                assert call_arg == "search_query: my query"

    def test_search_notes_formats_results_correctly(self):
        """search_notes should format results with title, content, and metadata."""
        mock_results = [
            {
                "title": "Test Note",
                "content": "This is test content",
                "filename": "test.md",
                "relative_path": "notes/test.md",
                "created_date": "2024-01-15",
                "note_type": "general",
            }
        ]

        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_search.limit.return_value.select.return_value.to_list.return_value = mock_results
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            with patch("obsidian.server.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_model.encode.return_value.tolist.return_value = [0.1] * 768
                mock_get_model.return_value = mock_model

                from obsidian.server import search_notes

                result = search_notes("test")

                assert "Test Note" in result
                assert "test.md" in result
                assert "This is test content" in result
                assert "2024-01-15" in result

    def test_search_notes_respects_limit_parameter(self):
        """search_notes should pass limit parameter to the search."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_limit = MagicMock()
        mock_search.limit.return_value = mock_limit
        mock_limit.select.return_value.to_list.return_value = []
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            with patch("obsidian.server.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_model.encode.return_value.tolist.return_value = [0.1] * 768
                mock_get_model.return_value = mock_model

                from obsidian.server import search_notes

                search_notes("test", limit=10)

                mock_search.limit.assert_called_once_with(10)


class TestReadFullNote:
    """Tests for the read_full_note MCP tool."""

    def test_read_full_note_returns_error_when_db_not_initialized(self):
        """read_full_note should return error when table is None."""
        with patch("obsidian.server.get_table", return_value=None):
            from obsidian.server import read_full_note

            result = read_full_note("test.md")
            assert "Error" in result
            assert "not initialized" in result

    def test_read_full_note_prevents_directory_traversal(self):
        """read_full_note should sanitize filename to prevent directory traversal."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_where = MagicMock()
        mock_search.where.return_value = mock_where
        mock_where.limit.return_value.to_list.return_value = []
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            from obsidian.server import read_full_note

            # Try directory traversal attack
            result = read_full_note("../../../etc/passwd")

            # The query should use the sanitized filename (just "passwd")
            mock_search.where.assert_called()
            where_arg = mock_search.where.call_args[0][0]
            assert "../" not in where_arg
            assert "passwd" in where_arg

    def test_read_full_note_returns_error_for_not_found_file(self):
        """read_full_note should return error when file not in index."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_where = MagicMock()
        mock_search.where.return_value = mock_where
        mock_where.limit.return_value.to_list.return_value = []
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            from obsidian.server import read_full_note

            result = read_full_note("nonexistent.md")
            assert "Error" in result
            assert "not found" in result

    def test_read_full_note_reads_file_content(self):
        """read_full_note should return the full file content."""
        # Create a temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_content = "# Test Note\n\nThis is the full content."
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text(test_content)

            mock_table = MagicMock()
            mock_search = MagicMock()
            mock_where = MagicMock()
            mock_search.where.return_value = mock_where
            mock_where.limit.return_value.to_list.return_value = [
                {"relative_path": "test.md"}
            ]
            mock_table.search.return_value = mock_search

            with patch("obsidian.server.get_table", return_value=mock_table):
                with patch("obsidian.server.VAULT_PATH", tmpdir):
                    from obsidian.server import read_full_note

                    result = read_full_note("test.md")
                    assert "# Test Note" in result
                    assert "This is the full content" in result

    def test_read_full_note_handles_file_read_errors(self):
        """read_full_note should handle file read errors gracefully."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_where = MagicMock()
        mock_search.where.return_value = mock_where
        mock_where.limit.return_value.to_list.return_value = [
            {"relative_path": "nonexistent/path.md"}
        ]
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_table", return_value=mock_table):
            with patch("obsidian.server.VAULT_PATH", "/nonexistent/vault"):
                from obsidian.server import read_full_note

                result = read_full_note("path.md")
                assert "Error" in result


class TestMCPServerSetup:
    """Tests for MCP server configuration."""

    def test_mcp_server_is_named_correctly(self):
        """MCP server should have the correct name."""
        from obsidian.server import mcp

        assert mcp.name == "Obsidian-Vault"

    def test_mcp_tools_are_registered(self):
        """Both search_notes and read_full_note should be registered as tools."""
        from obsidian.server import read_full_note, search_notes

        # The functions should exist and be callable
        assert callable(search_notes)
        assert callable(read_full_note)
