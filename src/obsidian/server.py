"""
MCP Server module for obsidian package.

Provides semantic search and note reading tools via Model Context Protocol.
"""

from mcp.server.fastmcp import FastMCP

from obsidian.config import VAULT_PATH
from obsidian.core import get_model, get_table


# --- INITIALIZATION ---
mcp = FastMCP("Obsidian-Vault")


# --- TOOL 1: SEMANTIC SEARCH ---
@mcp.tool()
def search_notes(query: str, limit: int = 5) -> str:
    """
    Search through Obsidian notes using vector similarity.
    Use this to find relevant context, memories, or technical details.
    """
    # 1. Prefix the query for Asymmetric Search (CRITICAL STEP)
    # This aligns the user's "Question" vector with the "Document" vectors
    prefixed_query = f"search_query: {query}"
    
    # 2. Generate Embedding
    query_vector = get_model().encode(prefixed_query).tolist()
    
    # 3. Search LanceDB
    # We select the fields we want to return to Claude
    results = get_table().search(query_vector) \
        .limit(limit) \
        .select(["title", "content", "filename", "created_date", "note_type"]) \
        .to_list()
    
    if not results:
        return "No matching notes found."

    # 4. Format the output for Claude
    formatted_response = f"Found {len(results)} relevant notes for '{query}':\n\n"
    
    for r in results:
        formatted_response += (
            f"--- NOTE: {r['title']} ({r['created_date']}) ---\n"
            f"Type: {r['note_type']}\n"
            f"File: {r['filename']}\n"
            f"Content Match:\n{r['content']}\n\n"
        )
        
    return formatted_response


# --- TOOL 2: READ FULL NOTE ---
@mcp.tool()
def read_full_note(filename: str) -> str:
    """
    Read the entire content of a specific markdown note file.
    Use this when the search result snippet isn't enough and you need the full context.
    """
    import os
    
    # Security: prevent directory traversal
    clean_filename = os.path.basename(filename)
    # We need to find where this file lives in the vault (since we store relative paths)
    # Simple search or you can query the DB for the 'relative_path'
    
    # Faster: Query DB to get the path
    try:
        # Search for exact filename match in DB to get path
        matches = get_table().search().where(f"filename = '{clean_filename}'").limit(1).to_list()
        if not matches:
             return f"Error: File '{clean_filename}' not found in the index."
             
        relative_path = matches[0]["relative_path"]
        full_path = os.path.join(VAULT_PATH, relative_path)
        
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
            
    except Exception as e:
        return f"Error reading file: {str(e)}"