"""
Ingestion module for obsidian package.

Provides functions to process and index Obsidian vault notes into LanceDB.
"""

import logging
import os

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from obsidian.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EXTRACTOR_BACKEND,
    INGEST_AUTO_EXTRACT,
    INGEST_AUTO_REPAIR,
    VAULT_PATH,
)
from obsidian.core import SCHEMA_VERSION, NoteChunk, get_db, get_model
from obsidian.utils import get_file_metadata, parse_frontmatter

logger = logging.getLogger(__name__)

# Required frontmatter fields for a complete/valid frontmatter
REQUIRED_FRONTMATTER_FIELDS = {"id", "title", "status", "created", "type"}


def is_frontmatter_complete(frontmatter: dict) -> bool:
    """Check if frontmatter has all required fields with non-empty values."""
    for field in REQUIRED_FRONTMATTER_FIELDS:
        if field not in frontmatter or not frontmatter[field]:
            return False
    return True


def repair_frontmatter(filepath: str, frontmatter: dict, content: str) -> dict:
    """
    Repair incomplete frontmatter by filling in missing fields.

    If auto-extract is enabled and backend is configured, uses LLM to extract
    metadata. Otherwise, uses sensible defaults.

    Args:
        filepath: Path to the file
        frontmatter: Existing frontmatter dict
        content: File content (without frontmatter)

    Returns:
        Updated frontmatter dict with all required fields
    """
    from pathlib import Path

    updated = frontmatter.copy()
    filename = os.path.basename(filepath)

    # Extract metadata using LLM if enabled
    extracted_title = ""
    extracted_summary = ""
    extracted_tags = []
    extracted_authors = []

    if INGEST_AUTO_EXTRACT and EXTRACTOR_BACKEND.lower() != "none":
        try:
            from obsidian.extract import extract_metadata

            logger.info("Auto-extracting metadata for %s...", filename)
            metadata = extract_metadata(content)
            extracted_title = metadata.title
            extracted_summary = metadata.summary
            extracted_tags = metadata.tags
            extracted_authors = metadata.authors
        except Exception as e:
            logger.warning("Failed to extract metadata for %s: %s", filename, e)

    # Fill in missing required fields
    if "id" not in updated or not updated["id"]:
        import uuid

        updated["id"] = str(uuid.uuid4())

    if "title" not in updated or not updated["title"]:
        updated["title"] = extracted_title or Path(filepath).stem

    if "status" not in updated or not updated["status"]:
        updated["status"] = "active"

    if "created" not in updated or not updated["created"]:
        import time

        updated["created"] = time.strftime("%Y-%m-%d")

    if "type" not in updated or not updated["type"]:
        updated["type"] = "general"

    # Fill optional fields if extracted
    if extracted_summary and ("summary" not in updated or not updated["summary"]):
        updated["summary"] = extracted_summary

    if extracted_tags and ("tags" not in updated or not updated["tags"]):
        updated["tags"] = extracted_tags

    if extracted_authors and ("authors" not in updated or not updated["authors"]):
        updated["authors"] = extracted_authors

    return updated


def write_repaired_frontmatter(filepath: str, frontmatter: dict, content: str) -> None:
    """Write the repaired frontmatter back to the file."""
    import yaml

    frontmatter_str = "---\n"
    frontmatter_str += yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    frontmatter_str += "---\n\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter_str + content)

    logger.info("Repaired frontmatter for %s", os.path.basename(filepath))


# --- NOTES ---
# Nomic requires the v1.5 specific model ID
# When we build the MCP Server (retrieval tool), we must remember
# to prefix the user's question differently.
# Ingestion: search_document: The API uses OAuth2...
# Retrieval: search_query: How does the API handle auth?
# If you mix these up (or forget them), the vector space won't align, and
# your results will be garbage.
#  two prefixes are used for retrieval tasks: where
# search_query is used for the question and search_document is used for the response.
# classification is used for STS-related tasks like rephrasals. clustering is used
# for tasks where the objective is to group semantically similar texts close together.


def chunk_markdown(content: str):
    """
    Hybrid Strategy:
    1. Try to split by Markdown Headers first (Logic preservation).
    2. If a header section is still massive (>8k tokens), recursively split it.
    """
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    # Stage 1: Structure-aware splitting
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    header_splits = md_splitter.split_text(content)

    # Stage 2: Size-aware splitting (for massive sections)
    # Nomic can handle large inputs, but we still want bite-sized retrieval results.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    final_chunks = []
    for split in header_splits:
        # If the section is small, keep it whole
        if len(split.page_content) < CHUNK_SIZE:
            final_chunks.append(split)
        else:
            # If large, sub-chunk it but keep header metadata
            sub_chunks = text_splitter.split_text(split.page_content)
            for sub in sub_chunks:
                # Reconstruct a chunk object with the same metadata
                final_chunks.append(Document(page_content=sub, metadata=split.metadata))

    return final_chunks


def process_file(filepath: str, table):
    """Process a single markdown file and add/update it in the database."""
    try:
        with open(filepath, encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        logger.warning("Skipping %s: %s", filepath, e)
        return

    frontmatter, content = parse_frontmatter(raw_text)

    # Check if frontmatter needs repair
    if INGEST_AUTO_REPAIR and not is_frontmatter_complete(frontmatter):
        logger.debug("Incomplete frontmatter in %s, repairing...", os.path.basename(filepath))
        frontmatter = repair_frontmatter(filepath, frontmatter, content)
        write_repaired_frontmatter(filepath, frontmatter, content)

    # Only index files with 'active' status (default for files without status)
    status = frontmatter.get("status", "active")
    if status != "active":
        logger.debug("Skipping %s (status=%s)", filepath, status)
        return

    meta = get_file_metadata(filepath, frontmatter)
    relative_path = os.path.relpath(filepath, VAULT_PATH)

    chunks = chunk_markdown(content)
    if not chunks:
        return

    records = []

    # --- CRITICAL NOMIC STEP: PREFIXING ---
    # Nomic requires "search_document: " prefix for indexing
    texts_to_embed = []
    for chunk in chunks:
        header_context = " > ".join([v for k, v in chunk.metadata.items() if k.startswith("Header")])
        full_text = f"{header_context}\n{chunk.page_content}".strip()

        # Store the clean text for display, but embed the prefixed text
        chunk.page_content = full_text
        texts_to_embed.append(f"search_document: {full_text}")

    # Generate Embeddings
    embeddings = get_model().encode(texts_to_embed)

    for i, chunk in enumerate(chunks):
        record = NoteChunk(
            id=f"{relative_path}#{i}",
            filename=os.path.basename(filepath),
            relative_path=relative_path,
            title=meta["title"],
            content=chunk.page_content,  # The clean text (without prefix)
            vector=embeddings[i].tolist(),
            note_type=meta["note_type"],
            created_date=meta["created"],
            status=meta["status"],
            tags=meta["tags"],
            last_modified=meta["last_modified"],
            schema_version=SCHEMA_VERSION,
        )
        records.append(record)

    table.delete(f"relative_path = '{relative_path}'")
    if records:
        table.add(records)


def main():
    """Main ingestion function - walks vault and indexes all markdown files."""
    database = get_db()
    table = database.create_table("notes", schema=NoteChunk.to_arrow_schema(), exist_ok=True)

    logger.info("Scanning %s...", VAULT_PATH)

    files_processed = 0
    for root, dirs, files in os.walk(VAULT_PATH):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.endswith(".md"):
                process_file(os.path.join(root, file), table)
                files_processed += 1
                if files_processed % 10 == 0:
                    logger.debug("Processed %d files...", files_processed)

    logger.info("Done! Indexed %d files.", files_processed)
