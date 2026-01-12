"""Tests for obsidian.utils module."""

import os
import tempfile
from pathlib import Path

import pytest

from obsidian.utils import parse_frontmatter, get_file_metadata


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parse_valid_frontmatter(self):
        """Should correctly parse valid YAML frontmatter."""
        content = """---
title: "Test Note"
type: paper
status: active
tags:
  - research
  - python
---

# Main Content

This is the body of the note.
"""
        frontmatter, body = parse_frontmatter(content)
        
        assert frontmatter["title"] == "Test Note"
        assert frontmatter["type"] == "paper"
        assert frontmatter["status"] == "active"
        assert frontmatter["tags"] == ["research", "python"]
        assert "# Main Content" in body

    def test_parse_no_frontmatter(self):
        """Should return empty dict when no frontmatter present."""
        content = "# Just a heading\n\nSome content without frontmatter."
        
        frontmatter, body = parse_frontmatter(content)
        
        assert frontmatter == {}
        assert body == content

    def test_parse_empty_frontmatter(self):
        """Should handle empty frontmatter block."""
        content = """---
---

Content after empty frontmatter.
"""
        frontmatter, body = parse_frontmatter(content)
        
        assert frontmatter is None or frontmatter == {}
        assert "Content after empty frontmatter" in body

    def test_parse_invalid_yaml(self):
        """Should return empty dict for invalid YAML."""
        content = """---
title: [unclosed bracket
invalid: yaml: here
---

Content body.
"""
        frontmatter, body = parse_frontmatter(content)
        
        # Should gracefully handle invalid YAML
        assert frontmatter == {}


class TestGetFileMetadata:
    """Tests for get_file_metadata function."""

    def test_metadata_from_frontmatter(self):
        """Should extract metadata from frontmatter when present."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            frontmatter = {
                "title": "My Custom Title",
                "type": "journal",
                "status": "archived",
                "tags": ["daily", "notes"],
            }
            
            meta = get_file_metadata(temp_path, frontmatter)
            
            assert meta["title"] == "My Custom Title"
            assert meta["note_type"] == "journal"
            assert meta["status"] == "archived"
            assert meta["tags"] == "daily,notes"
        finally:
            os.unlink(temp_path)

    def test_metadata_defaults(self):
        """Should use sensible defaults when frontmatter is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            meta = get_file_metadata(temp_path, {})
            
            # Title should default to filename without .md
            assert meta["title"] == Path(temp_path).stem
            assert meta["note_type"] == "general"
            assert meta["status"] == "active"
            assert meta["tags"] == ""
            assert "last_modified" in meta
        finally:
            os.unlink(temp_path)

    def test_metadata_includes_timestamps(self):
        """Should include file timestamps in metadata."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            meta = get_file_metadata(temp_path, {})
            
            assert "last_modified" in meta
            assert isinstance(meta["last_modified"], float)
            assert "created" in meta
        finally:
            os.unlink(temp_path)
