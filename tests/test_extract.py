"""Tests for the extract module."""


from obsidian.extract import (
    ExtractedMetadata,
    NoOpExtractor,
    get_extractor,
)


class TestExtractedMetadata:
    """Tests for the ExtractedMetadata model."""

    def test_default_values(self):
        """ExtractedMetadata should have sensible defaults."""
        metadata = ExtractedMetadata()
        assert metadata.title == ""
        assert metadata.authors == []
        assert metadata.summary == ""
        assert metadata.tags == []

    def test_with_values(self):
        """ExtractedMetadata should accept provided values."""
        metadata = ExtractedMetadata(
            title="Test Paper",
            authors=["Alice", "Bob"],
            summary="A test summary",
            tags=["test", "example"],
        )
        assert metadata.title == "Test Paper"
        assert metadata.authors == ["Alice", "Bob"]
        assert metadata.summary == "A test summary"
        assert metadata.tags == ["test", "example"]


class TestNoOpExtractor:
    """Tests for the NoOpExtractor."""

    def test_returns_empty_metadata(self):
        """NoOpExtractor should return empty metadata."""
        extractor = NoOpExtractor()
        result = extractor.extract("Some content here")
        assert isinstance(result, ExtractedMetadata)
        assert result.title == ""
        assert result.authors == []
        assert result.summary == ""
        assert result.tags == []

    def test_handles_any_content(self):
        """NoOpExtractor should handle any content without error."""
        extractor = NoOpExtractor()

        # Empty content
        result = extractor.extract("")
        assert isinstance(result, ExtractedMetadata)

        # Long content
        result = extractor.extract("x" * 10000)
        assert isinstance(result, ExtractedMetadata)

        # Unicode content
        result = extractor.extract("Unicode: \u00e9\u00e8\u00ea \u4e2d\u6587 \u0440\u0443\u0441\u0441\u043a\u0438\u0439")
        assert isinstance(result, ExtractedMetadata)


class TestGetExtractor:
    """Tests for the get_extractor factory function."""

    def test_returns_extractor_instance(self, monkeypatch):
        """get_extractor should return a valid extractor."""
        # Reset singleton
        import obsidian.extract

        obsidian.extract._extractor = None

        # Set backend to none
        monkeypatch.setattr("obsidian.extract.EXTRACTOR_BACKEND", "none")

        extractor = get_extractor()
        assert extractor is not None
        assert isinstance(extractor, NoOpExtractor)

    def test_singleton_pattern(self, monkeypatch):
        """get_extractor should return the same instance on repeated calls."""
        import obsidian.extract

        obsidian.extract._extractor = None
        monkeypatch.setattr("obsidian.extract.EXTRACTOR_BACKEND", "none")

        extractor1 = get_extractor()
        extractor2 = get_extractor()
        assert extractor1 is extractor2

    def test_unknown_backend_returns_noop(self, monkeypatch):
        """Unknown backend should default to NoOpExtractor."""
        import obsidian.extract

        obsidian.extract._extractor = None
        monkeypatch.setattr("obsidian.extract.EXTRACTOR_BACKEND", "unknown_backend")

        extractor = get_extractor()
        assert isinstance(extractor, NoOpExtractor)
