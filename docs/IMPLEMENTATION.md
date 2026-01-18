# Obsidian Implementation Specs

Obsidian allows you to import an Obsidian/Markdown vault into a local LanceDB database and exposes it via MCP for Chatbot (e.g. Claude) access.

## Architecture

The package lives in `src/obsidian/` with these core modules:

- **cli.py** - Typer-based CLI entry point (`obsidian` command) + rich for pretty formatting
- **config.py** - Configuration management (YAML at `~/.obsidian_rag_config.yaml` + env vars)
- **core.py** - Database schema (`NoteChunk`) and singletons for embedding model, LanceDB connection, and table
- **ingest.py** - Markdown ingestion pipeline with hybrid chunking (header-aware + recursive character splitting)
- **server.py** - MCP server with `search_notes` and `read_full_note` tools
- **import_doc.py** - Document import (PDF, DOCX, HTML, etc.) using Docling
- **extract.py** - LLM-based metadata extraction with pluggable backends (Ollama, Claude, Gemini)
- **utils.py** - Frontmatter parsing and metadata utilities

### Tech Stack

1. **Package Manager**: Use `uv` for environment management and dependency resolution.
2. **Linter/Formatter**: Assume `ruff` is used. Adhere to PEP 8 but prefer modern concise syntax.
3. **DataFrames**: Use `polars` instead of `pandas`. Prefer LazyFrames (`scan_csv`, `scan_parquet`) over eager execution.
4. **Data Validation**: Use `pydantic` (v2+) for all data modeling and configuration management.
5. **CLI**: Use `typer` for command-line interfaces. Use `rich` for terminal output.
6. **Build Backend**: Use `hatchling` in `pyproject.toml`.
7. **HTTP Client**: Use `httpx` for HTTP requests (async-capable, modern API).

## Configuration

Settings are loaded from `~/.obsidian_rag_config.yaml` with environment variable overrides.

### Core Settings

- `vault_path` / `VAULT_PATH` - Path to Obsidian vault
- `lancedb_path` / `LANCE_DB_PATH` - Path to LanceDB storage
- `embedding_model` - SentenceTransformer model (default: nomic-ai/nomic-embed-text-v1.5)
- `chunk_size` / `chunk_overlap` - Chunking parameters (default: 2000/200)

### LLM Extraction Settings

- `extractor_backend` / `EXTRACTOR_BACKEND` - Backend: "ollama", "claude", "gemini", or "none"
- `ollama_host` / `OLLAMA_HOST` - Ollama API URL (default: <http://localhost:11434>)
- `ollama_model` / `OLLAMA_MODEL` - Ollama model name (default: llama3.2)
- `ANTHROPIC_API_KEY` - Claude API key (env var only)
- `GOOGLE_API_KEY` - Gemini API key (env var only)

## Phase 1 (Data Layer)

### Local-first approach

Consider the markdown vault the single source of truth.

Configs and vectordb should be stored locally first.

### Files and imports

The user manages a (local) markdown vault, e.g. using Obsidian or Joplin. They create files and optionally add a standardized metdata header (frontmatter)
at the top of each file.

The users can use the package functions to import any supported documents with Docling into their vault.

### Frontmatter schema

Frontmatter YAML schema should added and be enforced strictly for files newly added to the vault.

Frontmatter should added or fixed time if not present or incomplete at the time of ingestions into the vector database, e.g. if the user changed
the file or added a file outside of the import functionality.

The metadata should have a document_status tag: pending | active | archived | deleted

- pending signals file is not ready for inclusion in vectordb
- active signals files to be included in vectordb
- deleted signals soft deletion

**Status handling during ingestion:**

- `active` - Indexed into vector database (default if status missing)
- `pending`, `archived`, `deleted` - Skipped during ingestion

### Document Import Workflows

**Default Workflow (Two-Step)**:

1. `obsidian import <dir>` → Documents converted with `status="pending"`, no LLM extraction
2. User reviews markdown files in vault
3. `obsidian extract <file.md> -u --activate` → Extracts metadata, sets `status="active"`
4. `obsidian lance` → Indexes only active files

**Quick Workflow (One-Step, for personal/low-volume use)**:

1. `obsidian import <dir> --extract` → Documents converted with immediate LLM extraction, `status="active"`
2. `obsidian lance` → Indexes active files

**CLI Flags**:

- `obsidian import --extract` (`-e`): Run LLM extraction during import, set status to "active"
- `obsidian extract --update` (`-u`): Update file frontmatter with extracted metadata
- `obsidian extract --activate` (`-a`): Set status to "active" (requires `-u`)

### cli.py

The CLI module should only contain thin wrappers around core modules.

### Vector database (lancedb)

The vector database is generated and updated via the obsidian lance command.

### Phase 1 Checklist

**Completed:**

- [x] Enable LLM metadata extraction (`extract.py` with Ollama/Claude/Gemini backends)
- [x] Improve frontmatter schema (id, title, authors, summary, type, status, created, tags, source)
- [x] Make CLI user-friendly (Typer + Rich, interactive `obsidian config` wizard)
- [x] Add `obsidian extract` command for standalone metadata extraction
- [x] Add `obsidian import` command for document conversion (PDF, DOCX, etc.) with Docling

**In Progress / TODO:**

*Integration*

- [x] Add `--extract` flag to `obsidian import` for immediate LLM extraction + active status
- [x] Add `--activate` flag to `obsidian extract` to set status to active
- [ ] Integrate LLM extraction into `ingest.process_file()` - auto-extract metadata for files with incomplete frontmatter
- [ ] Add frontmatter auto-repair in `ingest.process_file()` - fix/complete frontmatter during ingestion

*Configuration & Validation*

- [x] Migrate `config.py` to Pydantic model for type validation and better defaults handling
- [x] Add `obsidian config --show` to display current configuration without interactive prompts
- [x] Add programmatic API for setting vault path (`set_vault_path()` function)

*Database*

- [ ] Add schema versioning field to `NoteChunk` for future migrations
- [ ] Add `obsidian lance --force` to rebuild database from scratch

*Testing*

- [ ] Add integration tests for `ingest.process_file()` with mock database
- [ ] Add tests for `ingest.main()` end-to-end pipeline
- [ ] Add tests for MCP server tools (`search_notes`, `read_full_note`)
- [ ] Add tests for `import_doc` pipeline
- [ ] Add mocked tests for Claude/Gemini/Ollama extractors

## Phase 2 (Custom Chatbot + RAG)

A terminal-based chatbot with RAG using LanceDB vector search. Supports local LLMs (Ollama) and cloud APIs (Claude, Gemini).

### Architecture

New module `chat.py` with:

- `ConversationHistory` - In-memory conversation state
- `BaseChatClient` - Abstract base for LLM clients
- `OllamaChatClient`, `ClaudeChatClient`, `GeminiChatClient` - Backend implementations
- `search_context()` - Vector search with Nomic prefixing
- `ChatSession` - Orchestrates RAG pipeline

### CLI Command

```bash
obsidian chat                    # Interactive RAG chat
obsidian chat --no-rag           # Direct chat without retrieval
obsidian chat --context 10       # Retrieve 10 context chunks (default: 5)
```

**Terminal UI (Rich):**

- Colored prompts (green for user, blue for assistant)
- Markdown rendering for responses
- Special commands: `exit`, `clear`, `help`

### Configuration

```yaml
# ~/.obsidian_rag_config.yaml
chat_backend: ollama              # or "claude", "gemini"
chat_model: llama3.2              # model for chat (can differ from extractor)
chat_max_turns: 10                # conversation history limit
chat_context_limit: 5             # default RAG context chunks
```

Environment overrides: `CHAT_BACKEND`, `CHAT_MODEL`, `CHAT_MAX_TURNS`, `CHAT_CONTEXT_LIMIT`

### RAG Prompt Template

```
You are a helpful assistant with access to the user's Obsidian vault.
Use the following retrieved context from their notes to answer questions.
If the context doesn't contain relevant information, say so and answer based on general knowledge.

Retrieved Context:
{context}

Guidelines:
- Reference specific notes when relevant (mention titles/filenames)
- Be concise but thorough
- Acknowledge when information is not in the vault
```

### Phase 2 Checklist

**Core Implementation:**

- [x] Create `chat.py` module with data classes and ConversationHistory
- [x] Implement `OllamaChatClient` (POST to /api/chat)
- [x] Implement `ClaudeChatClient` (POST to /v1/messages)
- [x] Implement `GeminiChatClient` (POST to generateContent)
- [x] Implement `search_context()` and `format_context()` for RAG
- [x] Implement `ChatSession` orchestrator
- [x] Add `chat` command to CLI with Rich terminal UI
- [x] Add chat configuration to `config.py`

**Testing:**

- [x] Add tests for ConversationHistory
- [x] Add tests for context formatting
- [x] Add mocked tests for chat clients

**Future Enhancements (not in initial scope):**

- [ ] Streaming responses for better UX
- [ ] Session persistence to JSON files
- [ ] `--resume` flag for continuing sessions
- [ ] Token/cost tracking

## Inspirations & Resources

- [Obsidian](https://obsidian.md/)
- [LanceDB](https://lancedb.com/)
- [LangChain](https://docs.langchain.com/oss/python/langchain/overview)
- [Docling](https://github.com/docling-project/docling)
- [continuum](https://github.com/BioInfo/continuum/tree/main)
- [obsidian-ai](https://pypi.org/project/obsidian-ai/)

## Coding Standards

## 1. Filesystem

- **ALWAYS** use `pathlib.Path` for file manipulation.
- **NEVER** use `os.path` or string concatenation for paths.

## 2. Typing

- Python 3.10+ type syntax is required (use `|` instead of `Union`, `list[str]` instead of `List[str]`).
- All function signatures must be fully type-hinted.
- Use `typing.NewType` or `pydantic` models for complex data structures, avoiding nested dicts/lists.

## 3. Configuration

- All project metadata must reside in `pyproject.toml`.
- Do not generate `setup.py` or `requirements.txt` (unless as output from `uv pip compile`).

## 4. Error Handling & Logic

- Use `tenacity` for retries on network/IO operations.
- Use `loguru` for logging (not standard `logging`).
- Prefer `f-strings` over `.format()`.

## 5. Testing

- Use `pytest`.
- Use `pytest.fixture` for setup/teardown.
- Use `conftest.py` for shared fixtures.
