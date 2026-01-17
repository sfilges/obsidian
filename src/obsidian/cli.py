"""
CLI module for obsidian package.

Provides the command-line interface for the Obsidian RAG tool.
This module should only contain thin wrappers around core modules.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

from obsidian import convert_to_md, ingest, server
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
        for key, value in current.items():
            console.print(f"  {key}: {value}")
        return

    console.print("[bold blue]Obsidian RAG Configuration[/bold blue]")

    # Interactive prompts (UI concern stays in CLI)
    new_vault = Prompt.ask("Enter your Obsidian Vault Path", default=current["vault_path"])
    new_vault_path = Path(new_vault).expanduser().resolve()

    if not new_vault_path.exists():
        console.print(f"[yellow]Warning: Path {new_vault_path} does not exist.[/yellow]")

    new_db = Prompt.ask("Enter LanceDB Path (where to store embeddings)", default=current["lancedb_path"])
    new_model = Prompt.ask("Enter Embedding Model Name", default=current["embedding_model"])
    new_chunk_size = Prompt.ask("Enter Chunk Size", default=str(current["chunk_size"]))
    new_chunk_overlap = Prompt.ask("Enter Chunk Overlap", default=str(current["chunk_overlap"]))

    # Build config and save using core function
    config_data = {
        "vault_path": str(new_vault_path),
        "lancedb_path": str(Path(new_db).expanduser().resolve()),
        "embedding_model": new_model,
        "chunk_size": int(new_chunk_size),
        "chunk_overlap": int(new_chunk_overlap),
    }

    config_path = save_config(config_data)
    console.print(f"[green]Configuration saved to {config_path}[/green]")
    console.print(f"Vault: {config_data['vault_path']}")
    console.print(f"DB: {config_data['lancedb_path']}")


@app.command()
def lance():
    """
    Ingest the Obsidian vault into LanceDB.
    """
    current = get_current_config()
    console.print(f"[bold green]Starting Ingestion for {current['vault_path']}...[/bold green]")
    ingest.main()


@app.command()
def convert(
    input_path: str = typer.Argument(..., help="Path to directory containing files to convert"),
    output_path: str = typer.Option(None, help="Output directory (defaults to configured Vault path)"),
    extract: bool = typer.Option(False, "--extract", "-e", help="Extract metadata with LLM and set status to active"),
):
    """
    Convert PDFs to markdown and save to vault.

    By default, converted files have status="pending". Use --extract to run
    LLM metadata extraction and set status to "active" for immediate indexing.
    """
    input_p = Path(input_path).resolve()
    if not input_p.exists():
        console.print(f"[bold red]Error: Input path {input_p} does not exist.[/bold red]")
        raise typer.Exit(code=1)

    current = get_current_config()
    output_p = Path(output_path).resolve() if output_path else Path(current["vault_path"])

    console.print(f"[bold green]Converting PDFs from {input_p} to {output_p}...[/bold green]")
    if extract:
        console.print("[blue]Metadata extraction enabled - files will be set to 'active'[/blue]")
    else:
        console.print("[blue]Files will be saved with status='pending'[/blue]")
    convert_to_md.batch_convert_pdfs(input_p, output_p, extract=extract)
    console.print("[bold green]Conversion complete![/bold green]")


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
    console.print(f"Using backend: {current['extractor_backend']}")

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
