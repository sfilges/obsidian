# Configuration

Obsidian Vault RAG is configured via a YAML file and environment variables.

## Configuration File

The primary configuration is stored in `~/.obsidian_rag_config.yaml`. You can generate this file using the interactive wizard:

```bash
obsidian config
```

### Options

| Key | Description | Default |
| --- | --- | --- |
| `vault_path` | Absolute path to your Obsidian vault root directory. | - |
| `lancedb_path` | Directory where the LanceDB vector database will be stored. | `~/.obsidian/lancedb` |
| `embedding_model` | Hugging Face model name for embeddings. | `all-MiniLM-L6-v2` |
| `chunk_size` | Size of text chunks for RAG (tokens/characters). | `1000` |
| `chunk_overlap` | Overlap between chunks to preserve context. | `200` |

Example `~/.obsidian_rag_config.yaml`:

```yaml
vault_path: /Users/username/Documents/MyVault
lancedb_path: /Users/username/.obsidian/lancedb
embedding_model: sentence-transformers/all-MiniLM-L6-v2
chunk_size: 1000
chunk_overlap: 200
```

## Environment Variables

These variables control logging and application behavior:

| Variable | Description | Default |
| --- | --- | --- |
| `LOG_LEVEL` | Logging verbosity (DEBUG/INFO/WARNING/ERROR). | `DEBUG` |
| `LOG_DIR` | Directory for log files. | `~/.obsidian` |
| `LOG_MAX_BYTES` | Max log file size before rotation. | `10485760` (10MB) |
| `LOG_BACKUP_COUNT` | Number of rotated log files to keep. | `5` |

### Example Usage

```bash
# Run ingestion with less verbose logging
LOG_LEVEL=WARNING obsidian lance

# Store logs in a custom directory
LOG_DIR=/tmp/obsidian-logs obsidian serve
```
