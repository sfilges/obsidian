# Usage Guide

This guide covers the core commands available in the `obsidian` CLI.

## 1. Setup

Before using the tool, run the configuration wizard to link your vault:

```bash
obsidian config
```
Follow the prompts to set your vault path and database location.

## 2. Document Conversion (PDF to Markdown)

If you have research papers or documents in PDF format, you can convert them to Obsidian-friendly Markdown before ingestion. This uses [Docling](https://github.com/DS4SD/docling) for high-quality extraction, including tables and OCR.

```bash
# Convert all PDFs in a directory to your configured Vault path
obsidian convert /path/to/pdf/folder

# Convert to a specific output directory
obsidian convert /path/to/pdf/folder --output-path /path/to/output
```

The converter will:
- Extract text and tables.
- Generate frontmatter with metadata (title, tags like `research-article`).
- Sanitize filenames.

## 3. Ingestion (RAG Indexing)

To make your notes searchable by the AI, you must ingest them into the local vector database (LanceDB).

```bash
obsidian lance
```

This command:
1. Scans your `vault_path` for Markdown files.
2. Splits content into chunks (based on `chunk_size` config).
3. Generates embeddings using the configured model.
4. Stores them in LanceDB.

> **Note:** You should run this command whenever you add significant new content to your vault to keep the AI up-to-date.

## 4. MCP Server (Chat with Claude)

To use your vault with Claude Desktop, start the Model Context Protocol (MCP) server.

```bash
obsidian serve
```

This runs a stdio-based server that Claude Desktop connects to. See the [README](../README.md#connect-to-claude-desktop) for Claude configuration instructions.

### Troubleshooting
If the server doesn't start or Claude can't connect, check the logs:
```bash
tail -f ~/.obsidian/obsidian_rag.log
```
