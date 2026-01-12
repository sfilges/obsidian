
import typer
import yaml
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

# Import the functionality from existing scripts
# We need to make sure these imports work. 
# Since cli.py is in obsidian/, imports like 'from obsidian.config import ...' might fail if run directly.
# Proper usage: python -m obsidian.cli
try:
    from obsidian.config import VAULT_PATH, CONFIG_FILE, LANCE_DB_PATH, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_NAME
    # We delay importing ingest/server to avoid heavy load on simple config commands if possible, 
    # but for simplicity we can import them.
    from obsidian import ingest
    from obsidian import server
except ImportError:
    # Fallback for direct execution if needed (mostly for testing dev setup)
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from obsidian.config import VAULT_PATH, CONFIG_FILE
    from obsidian import ingest
    from obsidian import server

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
    
    # Save to yaml
    config_data = {
        "vault_path": str(new_vault_path),
        "lancedb_path": str(Path(new_db).expanduser().resolve()),
        "embedding_model": new_model,
        "chunk_size": CHUNK_SIZE, # Persist existing if not changed
        "chunk_overlap": CHUNK_OVERLAP
    }
    
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f)
        
    console.print(f"[green]Configuration saved to {CONFIG_FILE}[/green]")
    console.print(f"Vault: {config_data['vault_path']}")
    console.print(f"DB: {config_data['lancedb_path']}")

@app.command()
def ingest_vault():
    """
    Ingest the Obsidian vault into LanceDB.
    """
    console.print(f"[bold green]Starting Ingestion for {VAULT_PATH}...[/bold green]")
    # We call the main function from ingest.py
    # We might need to reload config if it was just changed in the same session, 
    # but since this is a CLI, each command is a fresh process usually.
    ingest.main()

@app.command()
def serve(
    mode: str = typer.Option("stdio", help="Server mode: 'stdio' or 'sse' (future)")
):
    """
    Start the MCP Server.
    """
    console.print(f"[bold green]Starting MCP Server...[/bold green]")
    # server.mcp.run() handles stdio by default.
    server.mcp.run()

if __name__ == "__main__":
    app()
