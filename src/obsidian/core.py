"""
Core module for obsidian package.

Provides shared resources used across the package:
- Embedding model singleton (SentenceTransformer)
- LanceDB connection and table access
- Database schema (NoteChunk)
"""

import logging

import lancedb
from lancedb.pydantic import LanceModel, Vector
from sentence_transformers import SentenceTransformer

from obsidian.config import EMBEDDING_MODEL_NAME, LANCE_DB_PATH

logger = logging.getLogger(__name__)


# --- DATABASE SCHEMA ---
class NoteChunk(LanceModel):
    """Schema for indexed note chunks in LanceDB."""

    id: str
    filename: str
    relative_path: str
    title: str
    content: str
    vector: Vector(768)  # Nomic v1.5 output dimension
    note_type: str
    created_date: str
    status: str
    tags: str
    last_modified: float


# --- SINGLETONS ---
_model = None
_db = None
_table = None


def get_model() -> SentenceTransformer:
    """
    Get the embedding model singleton.

    Uses Nomic v1.5 which requires specific prefixes for asymmetric search:
    - Ingestion: "search_document: <text>"
    - Retrieval: "search_query: <text>"
    """
    global _model
    if _model is None:
        logger.info("Loading %s...", EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME, trust_remote_code=True)
    return _model


def get_db() -> lancedb.DBConnection:
    """Get the LanceDB connection singleton."""
    global _db
    if _db is None:
        logger.info("Connecting to LanceDB at %s...", LANCE_DB_PATH)
        _db = lancedb.connect(LANCE_DB_PATH)
    return _db


def get_table():
    """
    Get the notes table from LanceDB.
    Returns None if the table does not exist.
    """
    global _table
    if _table is None:
        db = get_db()
        try:
            _table = db.open_table("notes")
        except Exception:
            # Table might not exist yet if 'obsidian lance' hasn't been run
            return None
    return _table
