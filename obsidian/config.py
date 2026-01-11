import os
from pathlib import Path

# --- PATHS ---
# Base directory of the scripts (assumes config.py is in the same dir as scripts)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Obsidian Vault Path
# Try to get from env var, otherwise default to a common location or raise error eventually
# For now, we keep the default from convert.py but verify it exists in the scripts that use it
OBSIDIAN_VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "~/Nextcloud/Notes/Obsidian")).expanduser()
# Only for compatibility if 'VAULT_PATH' was used in ingest.py
VAULT_PATH = OBSIDIAN_VAULT_PATH 

# Template Path
TEMPLATE_PATH = (SCRIPT_DIR / "../templates/header.yaml").resolve()

# LanceDB Path
LANCE_DB_PATH = Path(os.environ.get("LANCE_DB_PATH", "./lancedb_data")).resolve()

# --- SETTINGS ---
# Target folder for converted papers
TARGET_FOLDER = "Research/Bioinformatics"

# Embedding Model
EMBEDDING_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

# RAG / Chunking settings
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
