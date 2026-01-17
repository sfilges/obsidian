# Obsidian Vault RAG

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

**Obsidian Vault RAG** allows you to import your Obsidian markdown vault into a local LanceDB vector database and expose it via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for AI agents like Claude.

## Features
- **Local RAG**: No data leaves your machine; embeddings are stored locally in LanceDB.
- **Smart Ingestion**: Splits notes into chunks and generates embeddings.
- **PDF Support**: Converts research papers and PDFs to Markdown using [Docling](https://github.com/DS4SD/docling).
- **Claude Integration**: Connect your vault directly to Claude Desktop.

## Installation

Clone the repository and install the package:

```bash
# Using pip
pip install -e .

# OR using uv (recommended for speed)
uv pip install .
```

## Quick Start

1.  **Configure**: Run the setup wizard to link your vault.
    ```bash
    obsidian config
    ```
2.  **Ingest**: Index your notes into the database.
    ```bash
    obsidian lance
    ```
3.  **Serve**: Start the MCP server (or connect Claude, see below).
    ```bash
    obsidian serve
    ```

## Manual File Creation

To manually add files to your vault, you can use an [Obsidian Template](https://help.obsidian.md/Plugins/Templates) to automatically insert the required metadata.

Create a template file in your Obsidian templates folder with the following content:

```yaml
---
id: {{date:YYYYMMDDHHmm}}
title: {{title}}
authors: []
type: note
status: active
created: {{date:YYYY-MM-DD}} 
tags: []
source: "personal"
---

# {{title}}

Your content here...
```

## Documentation

- [**Usage Guide**](docs/usage.md): Detailed commands for ingestion, PDF conversion, and serving.
- [**Configuration**](docs/configuration.md): Settings, environment variables, and logging.

## Connect to Claude Desktop

To chat with your notes in Claude Desktop, add the server to your configuration file:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following entry (replace `/path/to/your/python` with your actual Python executable path):

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "/absolute/path/to/project/.venv/bin/python3",
      "args": [
        "-m",
        "obsidian.cli",
        "serve"
      ]
    }
  }
}
```

> **Tip:** You can find your python path by running `which python` (Mac/Linux) or `where python` (Windows) inside your project environment.

## License

MIT
