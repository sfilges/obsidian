"""
Core module for obsidian package.

Provides shared resources used across the package:
- Embedding model singleton (SentenceTransformer)
- LanceDB connection and table access
- Database schema (NoteChunk)
"""

import lancedb
from typing import List
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from obsidian.config import LANCE_DB_PATH, EMBEDDING_MODEL_NAME


# --- DATABASE SCHEMA ---
class NoteChunk(BaseModel):
    """Schema for indexed note chunks in LanceDB."""
    id: str
    filename: str
    relative_path: str
    title: str
    content: str
    vector: List[float]
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
        print(f"Loading {EMBEDDING_MODEL_NAME}...")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME, trust_remote_code=True)
    return _model


def get_db() -> lancedb.DBConnection:
    """Get the LanceDB connection singleton."""
    global _db
    if _db is None:
        print(f"Connecting to LanceDB at {LANCE_DB_PATH}...")
        _db = lancedb.connect(LANCE_DB_PATH)
    return _db


def get_table():
    """
    Get the notes table from LanceDB.
    
    Creates the table if it doesn't exist.
    """
    global _table
    if _table is None:
        db = get_db()
        _table = db.open_table("notes")
    return _table
