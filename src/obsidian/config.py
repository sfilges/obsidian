"""
Configuration module for obsidian package.
Handles loading, validation, and saving of application settings.
"""

import logging
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- CONFIGURATION LOAD ---
CONFIG_FILE = Path.home() / ".obsidian_rag_config.yaml"

# --- PATHS ---
SCRIPT_DIR = Path(__file__).parent.resolve()
TEMPLATE_PATH = (SCRIPT_DIR / "../templates/header.yaml").resolve()

# --- LOGGING CONFIGURATION ---
LOG_DIR = Path(os.environ.get("LOG_DIR", "~/.obsidian")).expanduser()
LOG_FILE = LOG_DIR / "obsidian_rag.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", "10485760"))  # 10MB default
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))


class ObsidianConfig(BaseModel):
    """
    Pydantic model for application configuration.
    Validates types and provides defaults.
    """

    vault_path: Path = Field(default_factory=lambda: Path("~/Nextcloud/Notes/Obsidian").expanduser())
    lancedb_path: Path = Field(default_factory=lambda: Path("./lancedb_data").resolve())
    embedding_model: str = Field(default="nomic-ai/nomic-embed-text-v1.5")
    chunk_size: int = Field(default=2000)
    chunk_overlap: int = Field(default=200)
    extractor_backend: str = Field(default="ollama")
    ollama_host: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2")
    ollama_num_ctx: int | None = Field(default=None, description="Override Ollama context window size")
    ollama_max_content_length: int = Field(default=12000, description="Max content chars for Ollama extraction")
    api_max_content_length: int = Field(default=64000, description="Max content chars for API extraction")
    anthropic_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)

    def to_dict(self) -> dict:
        """Convert config to dictionary suitable for saving."""
        return {
            "vault_path": str(self.vault_path),
            "lancedb_path": str(self.lancedb_path),
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "extractor_backend": self.extractor_backend,
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model,
            "ollama_num_ctx": self.ollama_num_ctx,
            "ollama_max_content_length": self.ollama_max_content_length,
            "api_max_content_length": self.api_max_content_length,
        }


def load_config() -> ObsidianConfig:
    """
    Load configuration from YAML file and override with environment variables.
    """
    file_config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                file_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Could not load config file %s: %s", CONFIG_FILE, e)

    config_dict = {}

    # Helper to merge: Env > File
    def merge(key, env_var):
        val = os.environ.get(env_var) or file_config.get(key)
        if val is not None:
            config_dict[key] = val

    # Helper for file only
    def file_only(key):
        val = file_config.get(key)
        if val is not None:
            config_dict[key] = val

    merge("vault_path", "VAULT_PATH")
    merge("lancedb_path", "LANCE_DB_PATH")
    file_only("embedding_model")
    file_only("chunk_size")
    file_only("chunk_overlap")
    merge("extractor_backend", "EXTRACTOR_BACKEND")
    merge("ollama_host", "OLLAMA_HOST")
    merge("ollama_model", "OLLAMA_MODEL")
    merge("ollama_num_ctx", "OLLAMA_NUM_CTX")
    file_only("ollama_max_content_length")
    file_only("api_max_content_length")

    merge("anthropic_api_key", "ANTHROPIC_API_KEY")
    merge("google_api_key", "GOOGLE_API_KEY")

    # Convert string to int for num_ctx if loaded from env
    if "ollama_num_ctx" in config_dict and config_dict["ollama_num_ctx"] is not None:
        config_dict["ollama_num_ctx"] = int(config_dict["ollama_num_ctx"])

    return ObsidianConfig(**config_dict)


def setup_logging() -> None:
    """Configure logging for the application."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    root_logger.handlers.clear()

    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
    file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)


setup_logging()
CURRENT_CONFIG = load_config()

# --- EXPORTS (Backward Compatibility) ---
VAULT_PATH = CURRENT_CONFIG.vault_path
LANCE_DB_PATH = CURRENT_CONFIG.lancedb_path
EMBEDDING_MODEL_NAME = CURRENT_CONFIG.embedding_model
CHUNK_SIZE = CURRENT_CONFIG.chunk_size
CHUNK_OVERLAP = CURRENT_CONFIG.chunk_overlap
EXTRACTOR_BACKEND = CURRENT_CONFIG.extractor_backend
OLLAMA_HOST = CURRENT_CONFIG.ollama_host
OLLAMA_MODEL = CURRENT_CONFIG.ollama_model
OLLAMA_NUM_CTX = CURRENT_CONFIG.ollama_num_ctx
OLLAMA_MAX_CONTENT_LENGTH = CURRENT_CONFIG.ollama_max_content_length
API_MAX_CONTENT_LENGTH = CURRENT_CONFIG.api_max_content_length
ANTHROPIC_API_KEY = CURRENT_CONFIG.anthropic_api_key
GOOGLE_API_KEY = CURRENT_CONFIG.google_api_key


def get_current_config() -> ObsidianConfig:
    """Return the current configuration object."""
    return CURRENT_CONFIG


def save_config(config_data: dict | ObsidianConfig) -> Path:
    """
    Save configuration to YAML file.
    Args:
        config_data: Dictionary or ObsidianConfig object to save.
    """
    data = config_data.to_dict() if isinstance(config_data, ObsidianConfig) else config_data

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f)

    return CONFIG_FILE


def set_vault_path(path: str | Path) -> None:
    """
    Programmatically set the vault path.
    Updates the config file and the current runtime config.
    """
    global VAULT_PATH
    new_path = Path(path).expanduser().resolve()
    CURRENT_CONFIG.vault_path = new_path

    save_config(CURRENT_CONFIG)
    VAULT_PATH = new_path
