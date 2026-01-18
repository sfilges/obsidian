# Plan: Improve Obsidian Chat UI and Suppress Warnings

## Goal
Suppress initialization warnings from `transformers` libraries and improve the terminal UI for the `obsidian chat` command.

## Proposed Changes

### 1. Suppress Warnings
**File:** `src/obsidian/core.py`
**Action:** Modify `get_model()` to set logging levels to `ERROR` for noisy libraries before loading the model.

```python
def get_model() -> SentenceTransformer:
    """..."""
    global _model
    if _model is None:
        # Suppress noisy warnings from huggingface libraries
        logging.getLogger("transformers").setLevel(logging.ERROR)
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("transformers_modules").setLevel(logging.ERROR)

        logger.info("Loading %s...", EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME, trust_remote_code=True)
    return _model
```

### 2. Disable Progress Bars
**File:** `src/obsidian/chat.py`
**Action:** In `search_context()`, disable the progress bar when encoding the query.

```python
def search_context(query: str, limit: int = CHAT_CONTEXT_LIMIT) -> list[dict]:
    # ...
    model = get_model()
    # Nomic requires "search_query: " prefix for retrieval
    # CHANGE: Added show_progress_bar=False
    query_vector = model.encode(f"search_query: {query}", show_progress_bar=False) 
    # ...
```

### 3. Enhance Terminal UI
**File:** `src/obsidian/cli.py`
**Action:** Update the `chat` command loop to include visual separators and better spacing.

1.  **Imports:** Add `Rule` and `Text` from `rich`.
    ```python
    from rich.rule import Rule
    from rich.text import Text
    ```

2.  **Chat Loop Improvements:**
    *   Add `console.rule(style="dim")` before the user input prompt to separate turns.
    *   Add a newline `\n` before "You:" for spacing.
    *   Add `console.print()` (newline) before showing the "Thinking..." status.
    *   Ensure the "Assistant:" label is printed *after* the thinking status and *before* the stream starts.

**Code Snippet for `src/obsidian/cli.py`:**
```python
    # Chat loop
    while True:
        try:
            console.rule(style="dim")  # Visual separator
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break
        
        # ... (command handling) ...

        # Send message and get response
        try:
            console.print() # Spacing
            
            with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                response_gen, context_chunks = session.stream_send(user_input)

            # Show retrieved context if available
            if context_chunks:
                # ... existing context display code ...
                # (Optional: Wrap in a Panel if desired, but Tree is fine)

            console.print("[bold blue]Assistant:[/bold blue]")

            # Stream response
            response_text = ""
            with Live(Markdown(""), refresh_per_second=10, transient=False) as live:
                for token in response_gen:
                    response_text += token
                    live.update(Markdown(response_text))
            console.print()
```

## Verification
1.  Run `obsidian chat`.
2.  Verify no `transformers` warnings appear on startup or first query.
3.  Verify no `Batches: 100%` progress bar appears during query.
4.  Verify the new UI layout with separators.
