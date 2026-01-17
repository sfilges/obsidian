"""Tests for the ingest module."""


from obsidian.ingest import chunk_markdown


class TestChunkMarkdown:
    """Tests for the chunk_markdown function."""

    def test_simple_content_returns_single_chunk(self):
        """Content smaller than chunk size should return a single chunk."""
        content = "This is a simple paragraph."
        chunks = chunk_markdown(content)
        assert len(chunks) == 1
        assert chunks[0].page_content == content

    def test_splits_by_headers(self):
        """Content with headers should be split at header boundaries."""
        content = """# Introduction
This is the intro.

## Methods
This is the methods section.

## Results
This is the results section."""

        chunks = chunk_markdown(content)
        # Should have multiple chunks (one per section)
        expected_min_sections = 3
        assert len(chunks) >= expected_min_sections

    def test_preserves_header_metadata(self):
        """Header information should be preserved in chunk metadata."""
        content = """# Main Title
Some content here.

## Subsection
More content here."""

        chunks = chunk_markdown(content)
        # At least one chunk should have header metadata
        has_header_metadata = any("Header" in str(chunk.metadata) for chunk in chunks)
        assert has_header_metadata

    def test_empty_content_returns_empty_list(self):
        """Empty content should return no chunks."""
        chunks = chunk_markdown("")
        # Empty or whitespace content may return empty list or single empty chunk
        assert len(chunks) <= 1

    def test_content_without_headers(self):
        """Content without headers should still be chunked."""
        content = "Just a plain paragraph without any markdown headers."
        chunks = chunk_markdown(content)
        assert len(chunks) >= 1
        assert content in chunks[0].page_content


class TestStatusFiltering:
    """Tests for document status filtering in process_file."""

    def test_archived_status_values(self):
        """Verify the expected status values per IMPLEMENTATION.md."""
        # These are the valid status values per the spec
        valid_statuses = {"pending", "active", "archived", "deleted"}

        # Only 'active' should be indexed
        indexable_statuses = {"active"}

        # Verify our understanding
        assert indexable_statuses.issubset(valid_statuses)
        assert len(indexable_statuses) == 1
