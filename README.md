# Obsidian Vault

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

Obsidian vault allows you to import an Obsidian/Markdown vault into a local LanceDB database and exposes it via MCP for Chatbot (e.g. Claude) access.

## File ingestion

To ingest your vault, run `python ingest.py`.

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
