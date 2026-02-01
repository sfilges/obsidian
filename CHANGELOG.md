# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-01

Initial beta release of Obsidian Vault RAG.

### Added

#### Core Features
- **Local RAG System**: Vector database using LanceDB with nomic-embed-text-v1.5 embeddings
- **MCP Server**: Model Context Protocol server for Claude Desktop integration
  - `search_notes` tool for semantic search
  - `read_full_note` tool for full note retrieval
- **CLI Interface**: Complete command-line interface with Typer and Rich
  - `obsidian config`: Interactive configuration wizard
  - `obsidian lance`: Vault ingestion with optional force rebuild
  - `obsidian import`: Document import (PDF, DOCX, URLs)
  - `obsidian extract`: LLM-based metadata extraction
  - `obsidian chat`: Interactive RAG chatbot
  - `obsidian serve`: MCP server
  - `obsidian --version`: Version display
  - Help shown by default when running `obsidian`

#### Document Processing
- **PDF Conversion**: Docling integration for PDF-to-Markdown conversion
- **Metadata Extraction**: Multi-backend LLM support for automatic metadata extraction
  - Ollama (local)
  - Anthropic Claude API
  - Google Gemini API
- **Frontmatter Auto-Repair**: Automatic repair of incomplete markdown frontmatter
- **Smart Chunking**: Hybrid chunking strategy
  - Header-aware splitting (H1-H3)
  - Recursive character splitting for large sections
  - Configurable chunk size (default 2000 chars) and overlap (default 200 chars)

#### Chat Features
- **Interactive Chat**: Local RAG chatbot with conversation history
- **History Compaction**: Token-based history management with automatic summarization
- **Multi-Backend Support**: Ollama, Claude, and Gemini backends
- **Context Formatting**: Rich context display with source attribution
- **Streaming Responses**: Real-time response streaming with markdown rendering

#### Configuration & Logging
- **YAML Configuration**: Persistent configuration at `~/.obsidian_rag_config.yaml`
- **Environment Variables**: Override any config setting via environment variables
- **Rotating Logs**: Automatic log rotation (10MB files, 5 backups)
- **Configurable Log Levels**: DEBUG/INFO/WARNING/ERROR/CRITICAL

#### Testing & Quality
- **Comprehensive Test Suite**: 110 tests covering all major functionality
- **Security Scanning**: Bandit integration for security checks
- **Pre-commit Hooks**: Automated linting, formatting, and security checks
- **CI/CD**: GitHub Actions workflows for testing and releases
- **Type Hints**: Full type annotation coverage
- **Directory Traversal Protection**: Security measures for file access

### Technical Details

#### Dependencies
- Python 3.10+
- LanceDB 0.26.1
- Sentence Transformers 5.2.0 (nomic-embed-text-v1.5)
- Docling 2.67.0 for PDF conversion
- MCP 1.25.0 for Model Context Protocol
- Typer & Rich for CLI
- Pydantic 2.12.5 for data validation

#### Architecture
- **Singleton Pattern**: Efficient resource management for models and database connections
- **Async-Ready**: Foundation for future async operations
- **Modular Design**: Clean separation of concerns across 11 core modules
- **Security-First**: Input validation, path sanitization, API key protection

### Documentation
- README.md with quick start guide
- Comprehensive usage documentation (docs/usage.md)
- Configuration guide (docs/configuration.md)
- CLAUDE.md for AI assistant integration
- Implementation documentation (docs/IMPLEMENTATION.md)

### Development Tools
- Ruff for linting and formatting
- Pre-commit hooks with auto-fix
- GitHub Actions CI/CD
- Bandit security scanning
- Pytest test framework

[Unreleased]: https://github.com/sfilges/obsidian-vault-rag/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sfilges/obsidian-vault-rag/releases/tag/v0.1.0
