import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# --- CONFIGURATION LOAD ---
CONFIG_FILE = Path.home() / ".obsidian_rag_config.yaml"
user_config = {}

if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE) as f:
            user_config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Could not load config file %s: %s", CONFIG_FILE, e)

# --- PATHS ---
# Base directory of the scripts (assumes config.py is in the same dir as scripts)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Obsidian Vault Path
# Priority: Env Var > User Config > Default
VAULT_PATH = Path(
    os.environ.get("VAULT_PATH") or user_config.get("vault_path") or "~/Nextcloud/Notes/Obsidian"
).expanduser()

# Template Path
TEMPLATE_PATH = (SCRIPT_DIR / "../templates/header.yaml").resolve()

# LanceDB Path
# Priority: Env Var > User Config > Default
LANCE_DB_PATH = Path(os.environ.get("LANCE_DB_PATH") or user_config.get("lancedb_path") or "./lancedb_data").resolve()

# --- SETTINGS ---
# Embedding Model
EMBEDDING_MODEL_NAME = user_config.get("embedding_model", "nomic-ai/nomic-embed-text-v1.5")

# RAG / Chunking settings
CHUNK_SIZE = int(user_config.get("chunk_size", 2000))
CHUNK_OVERLAP = int(user_config.get("chunk_overlap", 200))

# --- LLM EXTRACTION SETTINGS ---
# Backend for metadata extraction: "ollama", "claude", "gemini", or "none"
EXTRACTOR_BACKEND = os.environ.get("EXTRACTOR_BACKEND") or user_config.get("extractor_backend", "none")

# Ollama settings (for local LLM extraction)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or user_config.get("ollama_host", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL") or user_config.get("ollama_model", "llama3.2")

# API keys for cloud LLM providers (from env vars only for security)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# --- LOGGING CONFIGURATION ---
LOG_DIR = Path(os.environ.get("LOG_DIR", "~/.obsidian")).expanduser()
LOG_FILE = LOG_DIR / "obsidian_rag.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", "10485760"))  # 10MB default
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))


def setup_logging() -> None:
    """
    Configure logging for the application.

    Sets up rotating file handler and console handler with consistent formatting.
    Logs are written to ~/.obsidian/obsidian_rag.log and console.
    """
    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Define log format: timestamp - module_name - level - message
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Rotating file handler - main log output
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(file_handler)

    # Console handler - for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)


# Initialize logging when config module is loaded
setup_logging()


def get_current_config() -> dict:
    """
    Return current configuration as a dictionary.

    Returns all active configuration values (from env vars, config file, or defaults).
    """
    return {
        "vault_path": str(VAULT_PATH),
        "lancedb_path": str(LANCE_DB_PATH),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "extractor_backend": EXTRACTOR_BACKEND,
        "ollama_host": OLLAMA_HOST,
        "ollama_model": OLLAMA_MODEL,
    }


def save_config(config_data: dict) -> Path:
    """
    Save configuration to YAML file.

    Args:
        config_data: Dictionary of configuration values to save

    Returns:
        Path to the saved configuration file
    """
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f)
    return CONFIG_FILE
