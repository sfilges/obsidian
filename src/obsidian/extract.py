"""
LLM-based metadata extraction module for obsidian package.

Provides extractors for automatically extracting metadata (title, authors, summary, tags)
from document content using local (Ollama) or cloud (Claude, Gemini) LLMs.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from obsidian.config import (
    ANTHROPIC_API_KEY,
    EXTRACTOR_BACKEND,
    GOOGLE_API_KEY,
    OLLAMA_HOST,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)

# Content truncation limits to avoid context length issues
OLLAMA_MAX_CONTENT_LENGTH = 4000
API_MAX_CONTENT_LENGTH = 8000


class ExtractedMetadata(BaseModel):
    """Extracted metadata from a document."""

    title: str = Field(default="", description="Document title")
    authors: list[str] = Field(default_factory=list, description="List of author names")
    summary: str = Field(default="", description="Brief summary or abstract")
    tags: list[str] = Field(default_factory=list, description="Suggested tags/keywords")


EXTRACTION_PROMPT = """Analyze the following document and extract metadata.
Return a JSON object with these fields:
- title: The document's title (string)
- authors: List of author names if present (array of strings, empty if none found)
- summary: A brief 1-2 sentence summary of the content (string)
- tags: 3-5 relevant topic tags/keywords (array of strings)

Only return valid JSON, no other text.

Document:
{content}"""


class BaseExtractor(ABC):
    """Abstract base class for metadata extractors."""

    @abstractmethod
    def extract(self, content: str) -> ExtractedMetadata:
        """Extract metadata from document content."""


class NoOpExtractor(BaseExtractor):
    """Extractor that returns empty metadata (when extraction is disabled)."""

    def extract(self, content: str) -> ExtractedMetadata:
        return ExtractedMetadata()


class OllamaExtractor(BaseExtractor):
    """Extractor using local Ollama LLM."""

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host = host.rstrip("/")
        self.model = model

    def extract(self, content: str) -> ExtractedMetadata:
        # Truncate content to avoid context length issues
        truncated = content[:OLLAMA_MAX_CONTENT_LENGTH] if len(content) > OLLAMA_MAX_CONTENT_LENGTH else content
        prompt = EXTRACTION_PROMPT.format(content=truncated)

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                result = response.json()
                raw_response = result.get("response", "{}")

                # Parse JSON response
                data = json.loads(raw_response)
                return ExtractedMetadata(**data)

        except httpx.HTTPError as e:
            logger.warning("Ollama request failed: %s", e)
            return ExtractedMetadata()
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Ollama response as JSON: %s", e)
            return ExtractedMetadata()
        except Exception as e:
            logger.warning("Ollama extraction failed: %s", e)
            return ExtractedMetadata()


class ClaudeExtractor(BaseExtractor):
    """Extractor using Anthropic Claude API."""

    def __init__(self, api_key: str | None = ANTHROPIC_API_KEY):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude extractor")
        self.api_key = api_key

    def extract(self, content: str) -> ExtractedMetadata:
        # Truncate content to avoid token limits
        truncated = content[:API_MAX_CONTENT_LENGTH] if len(content) > API_MAX_CONTENT_LENGTH else content
        prompt = EXTRACTION_PROMPT.format(content=truncated)

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                result = response.json()

                # Extract text from Claude response
                text_content = result.get("content", [{}])[0].get("text", "{}")
                data = json.loads(text_content)
                return ExtractedMetadata(**data)

        except httpx.HTTPError as e:
            logger.warning("Claude API request failed: %s", e)
            return ExtractedMetadata()
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Claude response as JSON: %s", e)
            return ExtractedMetadata()
        except Exception as e:
            logger.warning("Claude extraction failed: %s", e)
            return ExtractedMetadata()


class GeminiExtractor(BaseExtractor):
    """Extractor using Google Gemini API."""

    def __init__(self, api_key: str | None = GOOGLE_API_KEY):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini extractor")
        self.api_key = api_key

    def extract(self, content: str) -> ExtractedMetadata:
        # Truncate content to avoid token limits
        truncated = content[:API_MAX_CONTENT_LENGTH] if len(content) > API_MAX_CONTENT_LENGTH else content
        prompt = EXTRACTION_PROMPT.format(content=truncated)

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}",
                    headers={"content-type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"responseMimeType": "application/json"},
                    },
                )
                response.raise_for_status()
                result = response.json()

                # Extract text from Gemini response
                text_content = (
                    result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                )
                data = json.loads(text_content)
                return ExtractedMetadata(**data)

        except httpx.HTTPError as e:
            logger.warning("Gemini API request failed: %s", e)
            return ExtractedMetadata()
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Gemini response as JSON: %s", e)
            return ExtractedMetadata()
        except Exception as e:
            logger.warning("Gemini extraction failed: %s", e)
            return ExtractedMetadata()


# Singleton extractor instance
_extractor: BaseExtractor | None = None


def get_extractor() -> BaseExtractor:
    """
    Get the configured metadata extractor.

    Returns extractor based on EXTRACTOR_BACKEND config:
    - "ollama": Local Ollama LLM
    - "claude": Anthropic Claude API
    - "gemini": Google Gemini API
    - "none" or other: NoOp extractor (returns empty metadata)
    """
    global _extractor

    if _extractor is None:
        backend = EXTRACTOR_BACKEND.lower()

        if backend == "ollama":
            logger.info("Using Ollama extractor with model %s", OLLAMA_MODEL)
            _extractor = OllamaExtractor()
        elif backend == "claude":
            logger.info("Using Claude extractor")
            _extractor = ClaudeExtractor()
        elif backend == "gemini":
            logger.info("Using Gemini extractor")
            _extractor = GeminiExtractor()
        else:
            logger.debug("Metadata extraction disabled (backend=%s)", backend)
            _extractor = NoOpExtractor()

    return _extractor


def extract_metadata(content: str) -> ExtractedMetadata:
    """
    Extract metadata from document content using the configured extractor.

    Args:
        content: Document text content

    Returns:
        ExtractedMetadata with title, authors, summary, and tags
    """
    extractor = get_extractor()
    metadata = extractor.extract(content)
    # Normalize tags: lower case and kebab-case
    if metadata.tags:
        metadata.tags = [
            t.strip().lower().replace(" ", "-").replace("_", "-")
            for t in metadata.tags
            if t.strip()
        ]
    return metadata


def extract_and_update_file(file_path: Path, update: bool = False, activate: bool = False) -> ExtractedMetadata:
    """
    Extract metadata from a markdown file and optionally update its frontmatter.

    Args:
        file_path: Path to markdown file (must be absolute/resolved)
        update: If True, update the file's frontmatter in-place
        activate: If True (and update=True), set status to "active"

    Returns:
        ExtractedMetadata with extracted title, authors, summary, tags

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not markdown or no backend configured
    """
    from obsidian.config import EXTRACTOR_BACKEND
    from obsidian.utils import generate_frontmatter, parse_frontmatter

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix != ".md":
        raise ValueError("Only markdown files are supported")

    if EXTRACTOR_BACKEND.lower() == "none":
        raise ValueError(
            "No extractor backend configured. "
            "Set EXTRACTOR_BACKEND to 'ollama', 'claude', or 'gemini' in config or env."
        )

    # Read file content
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Parse existing frontmatter
    existing_frontmatter, body = parse_frontmatter(content)

    # Extract metadata using LLM
    metadata = extract_metadata(body)

    if update:
        # Create a simple doc-like object for generate_frontmatter
        class DocStub:
            name = metadata.title or existing_frontmatter.get("title", file_path.stem)

        # Determine status: use "active" if activate=True, otherwise preserve existing
        new_status = "active" if activate else existing_frontmatter.get("status", "pending")

        new_frontmatter, _ = generate_frontmatter(
            DocStub(),
            str(file_path),
            note_type=existing_frontmatter.get("type", "general"),
            status=new_status,
            tags=metadata.tags or existing_frontmatter.get("tags", []),
            authors=metadata.authors,
            summary=metadata.summary,
        )

        # Write updated file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_frontmatter + body)

    return metadata
