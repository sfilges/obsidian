# Obsidian Vault

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

Obsidian vault allows you to import an Obsidian/Markdown vault into a local LanceDB database and exposes it via MCP for Chatbot (e.g. Claude) access.

## Installation

Clone the repository and install dependencies:

```bash
pip install -e .
```

or with uv:

```bash
uv pip install .
```

## Initial configuration

Run `obsidian config` to set up your initial configuration by following the interactive wizard.

## File ingestion

To ingest your vault into a LanceDB database, run `obsidian lance`.

## Logging

The application automatically logs to `~/.obsidian/obsidian_rag.log` with the following features:

- **Rotation**: Logs rotate at 10MB, keeping 5 backup files
- **Levels**: DEBUG (default), INFO, WARNING, ERROR, CRITICAL
- **Output**: Both file and console for visibility

### Viewing Logs

```bash
# View logs in real-time
tail -f ~/.obsidian/obsidian_rag.log

# Search for errors
grep ERROR ~/.obsidian/obsidian_rag.log

# Filter by module
grep obsidian.ingest ~/.obsidian/obsidian_rag.log
```

### Configuration

```bash
# Set log level (temporary)
LOG_LEVEL=INFO obsidian lance

# Set log level (persistent)
export LOG_LEVEL=WARNING

# Custom log directory
LOG_DIR=/custom/path obsidian serve
```

### Environment Variables

| Variable | Description | Default |
| ----------- | ----------- | ----------- |
| `LOG_LEVEL` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) | `DEBUG` |
| `LOG_DIR` | Directory for log files | `~/.obsidian` |
| `LOG_MAX_BYTES` | Max size before rotation (bytes) | `10485760` (10MB) |
| `LOG_BACKUP_COUNT` | Number of backup files to keep | `5` |

## Connect to Claude Desktop

Now you must tell Claude Desktop where to find this server. Open your Claude config file:

- Mac: ~/Library/Application Support/Claude/claude_desktop_config.json
- Windows: %APPDATA%\Claude\claude_desktop_config.json

Add your server definition. You must use the absolute path to your Python executable (the one where you installed mcp and lancedb).

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "/path/to/your/python/bin/python3",
      "args": [
        "/path/to/your/project/server.py"
      ]
    }
  }
}
```

1. Restart the Claude Desktop app.
2. Look for the 🔌 (Plug icon) in the top right. It should be green.
3. Type: "What do my notes say about [Project X]?" You should see Claude show a little "Using Tool" animation, and then answer using the chunks retrieved from LanceDB.
