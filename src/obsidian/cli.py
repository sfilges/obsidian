"""
CLI module for obsidian package.

Provides the command-line interface for the Obsidian RAG tool.
This module should only contain thin wrappers around core modules.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

from obsidian import import_doc, ingest, server
from obsidian.config import get_current_config, save_config

app = typer.Typer(help="Obsidian RAG CLI - Ingest and Chat with your notes.")
console = Console()


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current config without prompts"),
):
    """
    Interactive configuration wizard.
    Saves settings to ~/.obsidian_rag_config.yaml.
    """
    current = get_current_config()

    if show:
        console.print("[bold blue]Current Configuration:[/bold blue]")
        for key, value in current.to_dict().items():
            console.print(f"  {key}: {value}")
        return

    console.print("[bold blue]Obsidian RAG Configuration[/bold blue]")

    # Interactive prompts
    new_vault = Prompt.ask("Enter your Obsidian Vault Path", default=str(current.vault_path))
    new_vault_path = Path(new_vault).expanduser().resolve()

    if not new_vault_path.exists():
        console.print(f"[yellow]Warning: Path {new_vault_path} does not exist.[/yellow]")

    new_db = Prompt.ask("Enter LanceDB Path (where to store embeddings)", default=str(current.lancedb_path))
    new_model = Prompt.ask("Enter Embedding Model Name", default=current.embedding_model)
    new_chunk_size = Prompt.ask("Enter Chunk Size", default=str(current.chunk_size))
    new_chunk_overlap = Prompt.ask("Enter Chunk Overlap", default=str(current.chunk_overlap))

    # Extractor settings
    new_extractor = Prompt.ask(
        "Enter Extractor Backend (ollama, claude, gemini, none)",
        default=current.extractor_backend,
    )
    new_ollama_host = Prompt.ask("Enter Ollama Host", default=current.ollama_host)
    new_ollama_model = Prompt.ask("Enter Ollama Model", default=current.ollama_model)

    # Update config object (using copy to avoid mutating global state unexpectedly, though we just save it)
    updated_config = current.model_copy()
    updated_config.vault_path = new_vault_path
    updated_config.lancedb_path = Path(new_db).expanduser().resolve()
    updated_config.embedding_model = new_model
    updated_config.chunk_size = int(new_chunk_size)
    updated_config.chunk_overlap = int(new_chunk_overlap)
    updated_config.extractor_backend = new_extractor
    updated_config.ollama_host = new_ollama_host
    updated_config.ollama_model = new_ollama_model

    config_path = save_config(updated_config)
    console.print(f"[green]Configuration saved to {config_path}[/green]")
    console.print(f"Vault: {updated_config.vault_path}")
    console.print(f"DB: {updated_config.lancedb_path}")


@app.command()
def lance():
    """
    Ingest the Obsidian vault into LanceDB.
    """
    current = get_current_config()
    console.print(f"[bold green]Starting Ingestion for {current.vault_path}...[/bold green]")
    ingest.main()


@app.command(name="import")
def import_docs(
    source: str = typer.Argument(..., help="Path to file/directory or URL to import"),
    output_path: str = typer.Option(None, help="Output directory (defaults to configured Vault path)"),
    extract: bool = typer.Option(False, "--extract", "-e", help="Extract metadata with LLM and set status to active"),
):
    """
    Import documents (PDF, DOCX, URL, etc.) to markdown and save to vault.

    By default, converted files have status="pending". Use --extract to run
    LLM metadata extraction and set status to "active" for immediate indexing.
    """
    # Check if source is URL
    if source.startswith("http://") or source.startswith("https://"):
        input_source = source
        is_url = True
    else:
        input_source = Path(source).resolve()
        is_url = False
        if not input_source.exists():
            console.print(f"[bold red]Error: Input source {input_source} does not exist.[/bold red]")
            raise typer.Exit(code=1)

    current = get_current_config()
    output_p = current.vault_path / output_path if output_path else current.vault_path
    
    # Ensure output directory exists
    if not output_p.exists():
        console.print(f"[blue]Creating directory: {output_p}[/blue]")
        output_p.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold green]Importing from {source} to {output_p}...[/bold green]")
    if extract:
        console.print("[blue]Metadata extraction enabled - files will be set to 'active'[/blue]")
    else:
        console.print("[blue]Files will be saved with status='pending'[/blue]")

    if is_url or input_source.is_file():
        import_doc.import_file(input_source, output_p, extract=extract)
    elif input_source.is_dir():
        import_doc.bulk_import(input_source, output_p, extract=extract)

    console.print("[bold green]Import complete![/bold green]")


@app.command()
def serve(mode: str = typer.Option("stdio", help="Server mode: 'stdio' or 'sse' (future)")):
    """
    Start the MCP Server.
    """
    console.print("[bold green]Starting MCP Server...[/bold green]")
    server.mcp.run()


@app.command()
def extract(
    file_path: Path = typer.Argument(..., help="Markdown file to extract metadata from"),
    update: bool = typer.Option(False, "--update", "-u", help="Update file frontmatter in-place"),
    activate: bool = typer.Option(False, "--activate", "-a", help="Set status to 'active' (requires --update)"),
):
    """
    Extract metadata from a document using LLM.

    Uses the configured extractor backend (ollama, claude, gemini) to analyze
    document content and extract title, authors, summary, and tags.
    """
    from obsidian.extract import extract_and_update_file

    if activate and not update:
        console.print("[bold red]Error: --activate requires --update flag[/bold red]")
        raise typer.Exit(code=1)

    current = get_current_config()
    console.print(f"[bold blue]Extracting metadata from {file_path.name}...[/bold blue]")
    console.print(f"Using backend: {current.extractor_backend}")

    try:
        metadata = extract_and_update_file(file_path.resolve(), update=update, activate=activate)

        console.print("\n[bold green]Extracted Metadata:[/bold green]")
        console.print(f"  Title: {metadata.title}")
        console.print(f"  Authors: {', '.join(metadata.authors) if metadata.authors else '(none)'}")
        console.print(f"  Summary: {metadata.summary}")
        console.print(f"  Tags: {', '.join(metadata.tags) if metadata.tags else '(none)'}")

        if update:
            status_msg = " Status set to 'active'." if activate else ""
            console.print(f"\n[bold green]Updated {file_path.name} with extracted metadata.{status_msg}[/bold green]")

    except FileNotFoundError:
        console.print(f"[bold red]Error: File {file_path} does not exist.[/bold red]")
        raise typer.Exit(code=1) from None
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1) from None
