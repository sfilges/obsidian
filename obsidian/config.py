import os
from pathlib import Path

# --- PATHS ---
# Base directory of the scripts (assumes config.py is in the same dir as scripts)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Obsidian Vault Path
# Try to get from env var, otherwise default to a common location or raise error eventually
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "~/Nextcloud/Notes/Obsidian")).expanduser()

# Template Path
TEMPLATE_PATH = (SCRIPT_DIR / "../templates/header.yaml").resolve()

# LanceDB Path
LANCE_DB_PATH = Path(os.environ.get("LANCE_DB_PATH", "./lancedb_data")).resolve()

# --- SETTINGS ---
# Embedding Model
EMBEDDING_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

# RAG / Chunking settings
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
