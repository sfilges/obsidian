"""Tests for the core module."""

from unittest.mock import MagicMock, patch


class TestNoteChunk:
    """Tests for the NoteChunk schema."""

    def test_notechunk_has_required_fields(self):
        """NoteChunk should have all required fields per schema."""
        from obsidian.core import NoteChunk

        # Get the model fields
        fields = NoteChunk.model_fields
        required_fields = {
            "id",
            "filename",
            "relative_path",
            "title",
            "content",
            "vector",
            "note_type",
            "created_date",
            "status",
            "tags",
            "last_modified",
        }
        assert required_fields.issubset(set(fields.keys()))

    def test_notechunk_has_schema_version(self):
        """NoteChunk should have a schema_version field for migrations."""
        from obsidian.core import NoteChunk

        fields = NoteChunk.model_fields
        assert "schema_version" in fields, "NoteChunk should have schema_version field"

    def test_notechunk_to_arrow_schema(self):
        """NoteChunk should be convertible to Arrow schema."""
        from obsidian.core import NoteChunk

        schema = NoteChunk.to_arrow_schema()
        assert schema is not None
        # Check that expected fields exist in schema
        field_names = [field.name for field in schema]
        assert "id" in field_names
        assert "vector" in field_names
        assert "content" in field_names


class TestGetModel:
    """Tests for the get_model singleton function."""

    def test_get_model_returns_same_instance(self):
        """get_model should return the same instance on repeated calls."""
        # We need to reset the singleton first
        import obsidian.core

        obsidian.core._model = None

        with patch("obsidian.core.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model

            from obsidian.core import get_model

            model1 = get_model()
            model2 = get_model()

            # Should only create one instance
            assert mock_st.call_count == 1
            assert model1 is model2

    def test_get_model_uses_configured_embedding_model(self):
        """get_model should use the configured embedding model name."""
        import obsidian.core

        obsidian.core._model = None

        with patch("obsidian.core.SentenceTransformer") as mock_st:
            with patch("obsidian.core.EMBEDDING_MODEL_NAME", "test-model"):
                from obsidian.core import get_model

                get_model()
                mock_st.assert_called_once_with("test-model", trust_remote_code=True)


class TestGetDb:
    """Tests for the get_db singleton function."""

    def test_get_db_returns_same_instance(self):
        """get_db should return the same instance on repeated calls."""
        import obsidian.core

        obsidian.core._db = None

        with patch("obsidian.core.lancedb") as mock_lancedb:
            mock_db = MagicMock()
            mock_lancedb.connect.return_value = mock_db

            from obsidian.core import get_db

            db1 = get_db()
            db2 = get_db()

            # Should only connect once
            assert mock_lancedb.connect.call_count == 1
            assert db1 is db2

    def test_get_db_uses_configured_path(self):
        """get_db should use the configured LanceDB path."""
        import obsidian.core

        obsidian.core._db = None

        with patch("obsidian.core.lancedb") as mock_lancedb, patch("obsidian.core.LANCE_DB_PATH", "/test/path"):
            from obsidian.core import get_db

            get_db()
            mock_lancedb.connect.assert_called_once_with("/test/path")


class TestGetTable:
    """Tests for the get_table function."""

    def test_get_table_returns_none_when_table_not_exists(self):
        """get_table should return None if table doesn't exist."""
        import obsidian.core

        obsidian.core._table = None
        obsidian.core._db = None

        with patch("obsidian.core.lancedb") as mock_lancedb:
            mock_db = MagicMock()
            mock_db.open_table.side_effect = Exception("Table not found")
            mock_lancedb.connect.return_value = mock_db

            from obsidian.core import get_table

            result = get_table()
            assert result is None

    def test_get_table_returns_table_when_exists(self):
        """get_table should return table if it exists."""
        import obsidian.core

        obsidian.core._table = None
        obsidian.core._db = None

        with patch("obsidian.core.lancedb") as mock_lancedb:
            mock_table = MagicMock()
            mock_db = MagicMock()
            mock_db.open_table.return_value = mock_table
            mock_lancedb.connect.return_value = mock_db

            from obsidian.core import get_table

            result = get_table()
            assert result is mock_table

    def test_get_table_caches_result(self):
        """get_table should cache the table on subsequent calls."""
        import obsidian.core

        obsidian.core._table = None
        obsidian.core._db = None

        with patch("obsidian.core.lancedb") as mock_lancedb:
            mock_table = MagicMock()
            mock_db = MagicMock()
            mock_db.open_table.return_value = mock_table
            mock_lancedb.connect.return_value = mock_db

            from obsidian.core import get_table

            result1 = get_table()
            result2 = get_table()

            # Should only open table once
            assert mock_db.open_table.call_count == 1
            assert result1 is result2


class TestResetSingletons:
    """Tests for singleton reset functionality."""

    def test_reset_model_singleton(self):
        """Resetting _model should allow new instance creation."""
        import obsidian.core

        # Set a mock model
        mock_model = MagicMock()
        obsidian.core._model = mock_model

        # Reset it
        obsidian.core._model = None

        with patch("obsidian.core.SentenceTransformer") as mock_st:
            new_mock_model = MagicMock()
            mock_st.return_value = new_mock_model

            from obsidian.core import get_model

            result = get_model()
            assert result is new_mock_model
            assert result is not mock_model

    def test_reset_db_singleton(self):
        """Resetting _db should allow new connection."""
        import obsidian.core

        # Set a mock db
        mock_db = MagicMock()
        obsidian.core._db = mock_db

        # Reset it
        obsidian.core._db = None

        with patch("obsidian.core.lancedb") as mock_lancedb:
            new_mock_db = MagicMock()
            mock_lancedb.connect.return_value = new_mock_db

            from obsidian.core import get_db

            result = get_db()
            assert result is new_mock_db
            assert result is not mock_db
