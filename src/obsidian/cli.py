"""
CLI module for obsidian package.

Provides the command-line interface for the Obsidian RAG tool.
"""

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt

from obsidian import ingest, server, convert_to_md
from obsidian.config import CHUNK_OVERLAP, CHUNK_SIZE, CONFIG_FILE, EMBEDDING_MODEL_NAME, LANCE_DB_PATH, VAULT_PATH

app = typer.Typer(help="Obsidian RAG CLI - Ingest and Chat with your notes.")
console = Console()


@app.command()
def config():
    """
    Interactive configuration wizard.
    Saves settings to ~/.obsidian_rag_config.yaml.
    """
    console.print("[bold blue]Obsidian RAG Configuration[/bold blue]")

    current_vault = str(VAULT_PATH)
    new_vault = Prompt.ask("Enter your Obsidian Vault Path", default=current_vault)
    new_vault_path = Path(new_vault).expanduser().resolve()

    if not new_vault_path.exists():
        console.print(f"[yellow]Warning: Path {new_vault_path} does not exist.[/yellow]")

    current_db = str(LANCE_DB_PATH)
    new_db = Prompt.ask("Enter LanceDB Path (where to store embeddings)", default=current_db)

    current_model = EMBEDDING_MODEL_NAME
    new_model = Prompt.ask("Enter Embedding Model Name", default=current_model)

    current_chunk_size = str(CHUNK_SIZE)
    new_chunk_size = Prompt.ask("Enter Chunk Size", default=current_chunk_size)

    current_chunk_overlap = str(CHUNK_OVERLAP)
    new_chunk_overlap = Prompt.ask("Enter Chunk Overlap", default=current_chunk_overlap)

    # Save to yaml
    config_data = {
        "vault_path": str(new_vault_path),
        "lancedb_path": str(Path(new_db).expanduser().resolve()),
        "embedding_model": new_model,
        "chunk_size": int(new_chunk_size),
        "chunk_overlap": int(new_chunk_overlap),
    }

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f)

    console.print(f"[green]Configuration saved to {CONFIG_FILE}[/green]")
    console.print(f"Vault: {config_data['vault_path']}")
    console.print(f"DB: {config_data['lancedb_path']}")


@app.command()
def lance():
    """
    Ingest the Obsidian vault into LanceDB.
    """
    console.print(f"[bold green]Starting Ingestion for {VAULT_PATH}...[/bold green]")
    ingest.main()


@app.command()
def convert(
    input_path: str = typer.Argument(..., help="Path to directory containing files to convert"),
    output_path: str = typer.Option(None, help="Output directory (defaults to configured Vault path)"),
):
    """
    Convert PDFs to markdown and save to vault.
    """
    input_p = Path(input_path).resolve()
    if not input_p.exists():
        console.print(f"[bold red]Error: Input path {input_p} does not exist.[/bold red]")
        raise typer.Exit(code=1)

    output_p = Path(output_path).resolve() if output_path else VAULT_PATH

    console.print(f"[bold green]Converting PDFs from {input_p} to {output_p}...[/bold green]")
    convert_to_md.batch_convert_pdfs(input_p, output_p)
    console.print("[bold green]Conversion complete![/bold green]")


@app.command()
def serve(mode: str = typer.Option("stdio", help="Server mode: 'stdio' or 'sse' (future)")):
    """
    Start the MCP Server.
    """
    console.print("[bold green]Starting MCP Server...[/bold green]")
    server.mcp.run()
