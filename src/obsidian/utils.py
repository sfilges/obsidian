"""
Utility functions for obsidian package.

Provides helper functions for frontmatter generation and metadata extraction.
"""

import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import yaml

from obsidian.config import TEMPLATE_PATH

logger = logging.getLogger(__name__)

FRONTMATTER_DELIMITER_COUNT = 3


def generate_frontmatter(
    doc,
    source_path: str,
    note_type: str = "general",
    status: str = "draft",
    tags: list | None = None,
    authors: list | None = None,
    summary: str = "",
) -> tuple[str, str]:
    """
    Creates Obsidian-friendly YAML frontmatter.

    Args:
        doc: Document object with optional .name attribute
        source_path: Path to the source file
        note_type: Type of note (e.g., 'general', 'paper', 'concept')
        status: Document status ('draft', 'active', 'pending', 'archived', 'deleted')
        tags: List of tags for the document
        authors: List of author names (for papers/articles)
        summary: Brief summary or abstract of the document

    Returns:
        Tuple of (frontmatter_string, title)
    """
    # Attempt to extract title, defaulting to filename if extraction fails
    title = doc.name if doc.name else Path(source_path).stem

    frontmatter_dict = {
        "id": str(uuid.uuid4()),
        "title": title,
        "authors": authors or [],
        "summary": summary,
        "type": note_type,
        "status": status,
        "created": time.strftime("%Y-%m-%d"),
        "tags": tags or [],
        "source": str(source_path),
    }

    frontmatter = "---\n"
    frontmatter += yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
    frontmatter += "---\n\n"

    return frontmatter, title


def get_frontmatter(doc, source_path):
    """
    Loads the YAML template and fills in the placeholders.
    """
    # Prepare data for placeholders
    title = doc.name if doc.name else Path(source_path).stem
    date_added = time.strftime("%Y-%m-%d")
    clean_source = str(source_path)

    # Define the default fallback in case template is missing
    default_template = '---\ntitle: "{title}"\nadded: {date}\n---\n\n'

    try:
        if TEMPLATE_PATH.exists():
            with open(TEMPLATE_PATH, encoding="utf-8") as f:
                template_content = f.read()
        else:
            logger.warning("⚠️ Warning: Template not found at %s. Using default.", TEMPLATE_PATH)
            template_content = default_template

        # Fill placeholders
        # We use .format() so your yaml can contain {title}, {date}, {source}
        formatted_frontmatter = template_content.format(title=title, date=date_added, source=clean_source)
        return formatted_frontmatter, title

    except KeyError as e:
        logger.error("❌ Template Error: Your YAML contains a placeholder %s that the script doesn't provide.", e)
        return default_template.format(title=title, date=date_added), title
    except Exception as e:
        logger.error("❌ Error loading template: %s", e)
        return default_template.format(title=title, date=date_added), title


def parse_frontmatter(file_content: str):
    """Parse YAML frontmatter from markdown file content."""
    if file_content.startswith("---"):
        try:
            parts = file_content.split("---", FRONTMATTER_DELIMITER_COUNT)
            if len(parts) >= FRONTMATTER_DELIMITER_COUNT:
                frontmatter = yaml.safe_load(parts[1])
                content = parts[2].strip()
                return frontmatter, content
        except yaml.YAMLError:
            pass
    return {}, file_content


def get_file_metadata(filepath: str, frontmatter: dict):
    """Extract metadata from file stats and frontmatter."""
    stats = os.stat(filepath)
    filename = os.path.basename(filepath)
    return {
        "title": frontmatter.get("title", filename.replace(".md", "")),
        "note_type": frontmatter.get("type", "general"),
        "status": frontmatter.get("status", "active"),
        "created": str(frontmatter.get("created", datetime.fromtimestamp(stats.st_ctime).date())),
        "tags": ",".join(frontmatter.get("tags", [])),
        "last_modified": stats.st_mtime,
    }
