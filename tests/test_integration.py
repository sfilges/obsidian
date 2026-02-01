"""Integration tests for the full RAG pipeline."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestIngestToSearchPipeline:
    """Integration tests for the ingestion to search pipeline."""

    def test_process_file_applies_nomic_prefix(self):
        """process_file should apply 'search_document: ' prefix to embeddings."""
        import numpy as np

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            test_file = vault_path / "test.md"
            test_file.write_text("""---
id: test-123
title: Test
status: active
created: 2024-01-01
type: general
---

Test content here.
""")

            mock_model = MagicMock()
            captured_texts = []

            def capture_encode(texts):
                captured_texts.extend(texts if isinstance(texts, list) else [texts])
                count = len(texts) if isinstance(texts, list) else 1
                return np.array([[0.1] * 768 for _ in range(count)])

            mock_model.encode = capture_encode

            mock_table = MagicMock()

            with patch("obsidian.ingest.VAULT_PATH", vault_path):
                with patch("obsidian.ingest.get_model", return_value=mock_model):
                    from obsidian.ingest import process_file

                    process_file(str(test_file), mock_table)

            # Check that all texts were prefixed
            assert len(captured_texts) > 0
            for text in captured_texts:
                assert text.startswith("search_document: "), f"Text not prefixed: {text[:50]}"

    def test_process_file_creates_notechunk_records(self):
        """process_file should create NoteChunk records and add to table."""
        import numpy as np

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            test_file = vault_path / "test.md"
            test_file.write_text("""---
id: test-123
title: My Test Note
status: active
created: 2024-01-01
type: general
---

# Heading

Some content here.
""")

            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[0.1] * 768])

            mock_table = MagicMock()

            with patch("obsidian.ingest.VAULT_PATH", vault_path):
                with patch("obsidian.ingest.get_model", return_value=mock_model):
                    from obsidian.ingest import process_file

                    process_file(str(test_file), mock_table)

            # Check table.add was called with records
            mock_table.add.assert_called_once()
            records = mock_table.add.call_args[0][0]
            assert len(records) >= 1
            assert records[0].title == "My Test Note"

    def test_process_file_skips_non_active_status(self):
        """process_file should skip files with non-active status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            test_file = vault_path / "pending.md"
            test_file.write_text("""---
id: test-123
title: Pending Note
status: pending
created: 2024-01-01
type: general
---

Content here.
""")

            mock_model = MagicMock()
            mock_table = MagicMock()

            with patch("obsidian.ingest.VAULT_PATH", vault_path):
                with patch("obsidian.ingest.get_model", return_value=mock_model):
                    from obsidian.ingest import process_file

                    process_file(str(test_file), mock_table)

            # Table should not have been modified
            mock_table.add.assert_not_called()
            mock_model.encode.assert_not_called()


class TestSearchPipeline:
    """Tests for the search functionality."""

    def test_search_applies_query_prefix(self):
        """Search should apply 'search_query: ' prefix to queries."""
        mock_model = MagicMock()
        captured_queries = []

        class MockEncodeResult:
            def __init__(self, query):
                captured_queries.append(query)

            def tolist(self):
                return [0.1] * 768

        mock_model.encode = lambda q: MockEncodeResult(q)

        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_search.limit.return_value.select.return_value.to_list.return_value = []
        mock_table.search.return_value = mock_search

        with patch("obsidian.server.get_model", return_value=mock_model):
            with patch("obsidian.server.get_table", return_value=mock_table):
                from obsidian.server import search_notes

                search_notes("what is machine learning")

        # Check query was prefixed
        assert len(captured_queries) == 1
        assert captured_queries[0] == "search_query: what is machine learning"


class TestChatRAGPipeline:
    """Tests for the chat with RAG pipeline."""

    def test_chat_session_retrieves_context(self):
        """ChatSession should retrieve context when RAG is enabled."""
        mock_table = MagicMock()
        mock_results = [
            {
                "content": "Machine learning is a type of AI.",
                "title": "ML Basics",
                "filename": "ml.md",
                "relative_path": "notes/ml.md",
            }
        ]
        mock_table.search.return_value.limit.return_value.to_list.return_value = mock_results

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 768

        mock_client = MagicMock()
        mock_client.chat.return_value = "Machine learning is a subset of AI."

        with patch("obsidian.chat.get_table", return_value=mock_table):
            with patch("obsidian.chat.get_model", return_value=mock_model):
                from obsidian.chat import ChatSession

                session = ChatSession(client=mock_client, use_rag=True, context_limit=5)
                response, context = session.send("What is machine learning?")

                # Should have retrieved context
                assert len(context) == 1
                assert context[0]["title"] == "ML Basics"

                # Client should have been called
                mock_client.chat.assert_called_once()

    def test_chat_session_formats_rag_prompt(self):
        """ChatSession should format RAG context into system prompt."""
        mock_table = MagicMock()
        mock_results = [
            {
                "content": "ML is artificial intelligence.",
                "title": "ML Note",
                "filename": "ml.md",
                "relative_path": "ml.md",
            }
        ]
        mock_table.search.return_value.limit.return_value.to_list.return_value = mock_results

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 768

        mock_client = MagicMock()
        mock_client.chat.return_value = "Response"

        with patch("obsidian.chat.get_table", return_value=mock_table):
            with patch("obsidian.chat.get_model", return_value=mock_model):
                from obsidian.chat import ChatSession

                session = ChatSession(client=mock_client, use_rag=True)
                session.send("query")

                # Check that system_prompt was passed with context
                call_args = mock_client.chat.call_args
                system_prompt = call_args[1].get("system_prompt", "")
                assert "ML Note" in system_prompt or "Retrieved Context" in system_prompt

    def test_chat_session_works_without_rag(self):
        """ChatSession should work when RAG is disabled."""
        mock_client = MagicMock()
        mock_client.chat.return_value = "Direct response"

        from obsidian.chat import ChatSession

        session = ChatSession(client=mock_client, use_rag=False)
        response, context = session.send("Hello")

        assert response == "Direct response"
        assert context == []


class TestFrontmatterRepairPipeline:
    """Tests for frontmatter auto-repair during ingestion."""

    def test_incomplete_frontmatter_is_repaired(self):
        """Files with incomplete frontmatter should be repaired during ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            # Create file with incomplete frontmatter
            test_file = vault_path / "incomplete.md"
            test_file.write_text("""---
title: Just a Title
---

Some content here.
""")

            from obsidian.ingest import is_frontmatter_complete, repair_frontmatter
            from obsidian.utils import parse_frontmatter

            content = test_file.read_text()
            frontmatter, body = parse_frontmatter(content)

            # Should be incomplete
            assert not is_frontmatter_complete(frontmatter)

            # Repair it (without LLM extraction)
            with patch("obsidian.ingest.INGEST_AUTO_EXTRACT", False):
                repaired = repair_frontmatter(str(test_file), frontmatter, body)

            # Should now have all required fields
            assert is_frontmatter_complete(repaired)
            assert repaired["title"] == "Just a Title"  # Preserved
            assert "id" in repaired
            assert "status" in repaired
            assert "created" in repaired
            assert "type" in repaired

    def test_complete_frontmatter_not_modified(self):
        """Files with complete frontmatter should not be modified."""
        frontmatter = {
            "id": "test-123",
            "title": "Complete Note",
            "status": "active",
            "created": "2024-01-01",
            "type": "general",
        }

        from obsidian.ingest import is_frontmatter_complete

        assert is_frontmatter_complete(frontmatter)


class TestSchemaVersioning:
    """Tests for schema versioning in NoteChunk."""

    def test_notechunk_includes_schema_version(self):
        """NoteChunk records should include schema_version field."""
        from obsidian.core import SCHEMA_VERSION, NoteChunk

        # Create a mock record
        record = NoteChunk(
            id="test-1",
            filename="test.md",
            relative_path="test.md",
            title="Test",
            content="Content",
            vector=[0.1] * 768,
            note_type="general",
            created_date="2024-01-01",
            status="active",
            tags="test",
            last_modified=1234567890.0,
        )

        assert record.schema_version == SCHEMA_VERSION

    def test_schema_version_is_integer(self):
        """SCHEMA_VERSION should be an integer."""
        from obsidian.core import SCHEMA_VERSION

        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1
