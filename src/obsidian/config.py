import os
from pathlib import Path

# --- CONFIGURATION LOAD ---
import yaml

CONFIG_FILE = Path.home() / ".obsidian_rag_config.yaml"
user_config = {}

if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r") as f:
            user_config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Could not load config file {CONFIG_FILE}: {e}")

# --- PATHS ---
# Base directory of the scripts (assumes config.py is in the same dir as scripts)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Obsidian Vault Path
# Priority: Env Var > User Config > Default
VAULT_PATH = Path(
    os.environ.get("VAULT_PATH") or 
    user_config.get("vault_path") or 
    "~/Nextcloud/Notes/Obsidian"
).expanduser()

# Template Path
TEMPLATE_PATH = (SCRIPT_DIR / "../templates/header.yaml").resolve()

# LanceDB Path
# Priority: Env Var > User Config > Default
LANCE_DB_PATH = Path(
    os.environ.get("LANCE_DB_PATH") or 
    user_config.get("lancedb_path") or 
    "./lancedb_data"
).resolve()

# --- SETTINGS ---
# Embedding Model
EMBEDDING_MODEL_NAME = user_config.get("embedding_model", "nomic-ai/nomic-embed-text-v1.5")

# RAG / Chunking settings
CHUNK_SIZE = int(user_config.get("chunk_size", 2000))
CHUNK_OVERLAP = int(user_config.get("chunk_overlap", 200))
