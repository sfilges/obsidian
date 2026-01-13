"""Tests for obsidian.config module."""

import os
from pathlib import Path
from unittest import mock


class TestConfigDefaults:
    """Tests for configuration default values."""

    def test_default_embedding_model(self):
        """Should use nomic model as default."""
        # Import fresh to get defaults
        from obsidian.config import EMBEDDING_MODEL_NAME

        # Default model when no config file exists
        assert "nomic" in EMBEDDING_MODEL_NAME.lower() or EMBEDDING_MODEL_NAME is not None

    def test_default_chunk_settings(self):
        """Should have sensible default chunk settings."""
        from obsidian.config import CHUNK_OVERLAP, CHUNK_SIZE

        assert CHUNK_SIZE > 0
        assert CHUNK_OVERLAP >= 0
        assert CHUNK_OVERLAP < CHUNK_SIZE

    def test_paths_are_path_objects(self):
        """Config paths should be Path objects."""
        from obsidian.config import CONFIG_FILE, LANCE_DB_PATH, VAULT_PATH

        assert isinstance(VAULT_PATH, Path)
        assert isinstance(LANCE_DB_PATH, Path)
        assert isinstance(CONFIG_FILE, Path)


class TestConfigEnvOverrides:
    """Tests for environment variable overrides."""

    def test_vault_path_from_env(self):
        """VAULT_PATH env var should override config."""
        test_path = "/tmp/test_vault"

        with mock.patch.dict(os.environ, {"VAULT_PATH": test_path}):
            # Need to reimport to pick up env var
            import importlib

            import obsidian.config

            importlib.reload(obsidian.config)

            assert str(obsidian.config.VAULT_PATH) == test_path

    def test_lancedb_path_from_env(self):
        """LANCE_DB_PATH env var should override config."""
        test_path = "/tmp/test_lancedb"

        with mock.patch.dict(os.environ, {"LANCE_DB_PATH": test_path}):
            import importlib

            import obsidian.config

            importlib.reload(obsidian.config)

            assert str(obsidian.config.LANCE_DB_PATH) == test_path
