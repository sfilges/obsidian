"""
Ingestion module for obsidian package.

Provides functions to process and index Obsidian vault notes into LanceDB.
"""

import logging
import os

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from obsidian.config import CHUNK_OVERLAP, CHUNK_SIZE, VAULT_PATH
from obsidian.core import NoteChunk, get_db, get_model
from obsidian.utils import get_file_metadata, parse_frontmatter

logger = logging.getLogger(__name__)

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
