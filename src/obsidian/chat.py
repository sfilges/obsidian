"""
Chat module for obsidian package.

Provides a terminal-based RAG chatbot using LanceDB vector search
and local/cloud LLMs (Ollama, Claude, Gemini).
"""

import logging
from abc import ABC, abstractmethod
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from obsidian.config import (
    ANTHROPIC_API_KEY,
    CHAT_BACKEND,
    CHAT_CONTEXT_LIMIT,
    CHAT_ENABLE_COMPACTION,
    CHAT_MAX_TURNS,
    CHAT_MODEL,
    CHAT_RECENT_TURNS,
    CHAT_TOKEN_LIMIT,
    GOOGLE_API_KEY,
    OLLAMA_HOST,
)
from obsidian.core import get_model, get_table

logger = logging.getLogger(__name__)


# --- DATA CLASSES ---


class Message(BaseModel):
    """A single message in a conversation."""

    role: Literal["user", "assistant"] = Field(description="Message sender role")
    content: str = Field(description="Message content")


class ConversationHistory:
    """Manages conversation history with configurable max turns."""

    def __init__(self, max_turns: int = CHAT_MAX_TURNS):
        self.max_turns = max_turns
        self._messages: list[Message] = []

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        """Add a message to history."""
        self._messages.append(Message(role=role, content=content))
        # Trim old messages if exceeding max turns (keep 2 messages per turn)
        max_messages = self.max_turns * 2
        if len(self._messages) > max_messages:
            self._messages = self._messages[-max_messages:]

    def get_messages(self) -> list[Message]:
        """Get all messages in history."""
        return self._messages.copy()

    def clear(self) -> None:
        """Clear conversation history."""
        self._messages = []

    def to_ollama_format(self) -> list[dict]:
        """Convert to Ollama API format."""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def to_claude_format(self) -> list[dict]:
        """Convert to Claude API format."""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def to_gemini_format(self) -> list[dict]:
        """Convert to Gemini API format (user/model roles)."""
        return [
            {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
            for m in self._messages
        ]


# --- COMPACTION PROMPT ---

COMPACTION_PROMPT = """Summarize this conversation concisely in prose form, preserving key context \
like project names, file paths, decisions made, and any facts the user shared. \
Do not include greetings or filler. Focus on information needed for continuity.

Previous summary:
{existing_summary}

Conversation to incorporate:
{messages}"""


class CompactingHistory:
    """Token-aware conversation history with automatic summarization."""

    def __init__(
        self,
        token_limit: int = CHAT_TOKEN_LIMIT,
        recent_turns: int = CHAT_RECENT_TURNS,
        summarizer: "BaseChatClient | None" = None,
    ):
        self.token_limit = token_limit
        self.recent_turns = recent_turns
        self._summarizer: "BaseChatClient | None" = summarizer
        self.summary: str = ""
        self._messages: list[Message] = []

    def set_summarizer(self, client: "BaseChatClient") -> None:
        """Set the chat client used for summarization."""
        self._summarizer = client

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        """Add message and trigger compaction if over token limit."""
        self._messages.append(Message(role=role, content=content))
        if self._estimate_tokens() > self.token_limit:
            self._compact()

    def _estimate_tokens(self) -> int:
        """Rough token estimate: ~4 chars per token."""
        summary_tokens = len(self.summary) // 4
        message_tokens = sum(len(m.content) // 4 for m in self._messages)
        return summary_tokens + message_tokens

    def _compact(self) -> None:
        """Summarize older turns into prose, keep recent_turns verbatim."""
        keep_count = self.recent_turns * 2
        if len(self._messages) <= keep_count:
            return

        old_msgs = self._messages[:-keep_count]
        self._messages = self._messages[-keep_count:]

        # Format messages for summarization
        formatted = "\n".join(f"{m.role.upper()}: {m.content}" for m in old_msgs)
        prompt = COMPACTION_PROMPT.format(
            existing_summary=self.summary or "(No previous summary)",
            messages=formatted,
        )

        if self._summarizer:
            try:
                self.summary = self._summarizer.chat(
                    [Message(role="user", content=prompt)],
                    system_prompt="You are a concise summarizer. Output only the summary, no preamble.",
                )
                logger.info("Compacted %d messages into summary (%d chars)", len(old_msgs), len(self.summary))
            except Exception as e:
                logger.warning("Compaction summarization failed: %s. Keeping raw messages.", e)
                # Fallback: just concatenate old messages as summary
                self.summary = f"{self.summary}\n\n{formatted}" if self.summary else formatted
        else:
            logger.warning("No summarizer set, using raw concatenation for compaction")
            self.summary = f"{self.summary}\n\n{formatted}" if self.summary else formatted

    def get_messages(self) -> list[Message]:
        """Get all messages in history."""
        return self._messages.copy()

    def get_summary(self) -> str:
        """Get the compacted summary of older turns."""
        return self.summary

    def clear(self) -> None:
        """Clear conversation history and summary."""
        self._messages = []
        self.summary = ""

    def to_ollama_format(self) -> list[dict]:
        """Convert to Ollama API format."""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def to_claude_format(self) -> list[dict]:
        """Convert to Claude API format."""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def to_gemini_format(self) -> list[dict]:
        """Convert to Gemini API format (user/model roles)."""
        return [
            {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
            for m in self._messages
        ]


# --- RAG SYSTEM PROMPT ---

RAG_SYSTEM_PROMPT = """You are a helpful assistant with access to the user's Obsidian vault.
Use the following retrieved context from their notes to answer questions.
If the context doesn't contain relevant information, say so and answer based on general knowledge.

Retrieved Context:
{context}

Guidelines:
- Reference specific notes when relevant (mention titles/filenames)
- Be concise but thorough
- Acknowledge when information is not in the vault"""


# --- CHAT CLIENTS ---


class BaseChatClient(ABC):
    """Abstract base class for chat LLM clients."""

    @abstractmethod
    def chat(self, messages: list[Message], system_prompt: str | None = None) -> str:
        """Send messages and return assistant response."""


class OllamaChatClient(BaseChatClient):
    """Chat client using local Ollama LLM."""

    def __init__(self, host: str = OLLAMA_HOST, model: str = CHAT_MODEL):
        self.host = host.rstrip("/")
        self.model = model

    def chat(self, messages: list[Message], system_prompt: str | None = None) -> str:
        """Send chat request to Ollama."""
        ollama_messages = [{"role": m.role, "content": m.content} for m in messages]

        # Prepend system message if provided
        if system_prompt:
            ollama_messages.insert(0, {"role": "system", "content": system_prompt})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(f"{self.host}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error("Ollama chat request failed: %s", e)
            raise RuntimeError(f"Ollama chat failed: {e}") from e


class ClaudeChatClient(BaseChatClient):
    """Chat client using Anthropic Claude API."""

    def __init__(self, api_key: str | None = ANTHROPIC_API_KEY, model: str = "claude-sonnet-4-20250514"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude chat")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[Message], system_prompt: str | None = None) -> str:
        """Send chat request to Claude."""
        claude_messages = [{"role": m.role, "content": m.content} for m in messages]

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": claude_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                # Claude returns content as array of blocks
                content_blocks = data.get("content", [])
                return "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        except httpx.HTTPError as e:
            logger.error("Claude chat request failed: %s", e)
            raise RuntimeError(f"Claude chat failed: {e}") from e


class GeminiChatClient(BaseChatClient):
    """Chat client using Google Gemini API."""

    def __init__(self, api_key: str | None = GOOGLE_API_KEY, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini chat")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[Message], system_prompt: str | None = None) -> str:
        """Send chat request to Gemini."""
        # Convert messages to Gemini format
        gemini_contents = [
            {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]} for m in messages
        ]

        payload = {"contents": gemini_contents}

        # Add system instruction if provided
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                # Extract text from response
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts)
                return ""
        except httpx.HTTPError as e:
            logger.error("Gemini chat request failed: %s", e)
            raise RuntimeError(f"Gemini chat failed: {e}") from e


# --- FACTORY ---

_chat_client: BaseChatClient | None = None


def get_chat_client() -> BaseChatClient:
    """
    Get the configured chat client singleton.

    Returns client based on CHAT_BACKEND config:
    - "ollama": Local Ollama LLM
    - "claude": Anthropic Claude API
    - "gemini": Google Gemini API
    """
    global _chat_client
    if _chat_client is None:
        backend = CHAT_BACKEND.lower()
        logger.info("Initializing chat client: %s", backend)

        if backend == "ollama":
            _chat_client = OllamaChatClient()
        elif backend == "claude":
            _chat_client = ClaudeChatClient()
        elif backend == "gemini":
            _chat_client = GeminiChatClient()
        else:
            raise ValueError(f"Unknown chat backend: {backend}. Use 'ollama', 'claude', or 'gemini'.")

    return _chat_client


# --- RAG FUNCTIONS ---


def search_context(query: str, limit: int = CHAT_CONTEXT_LIMIT) -> list[dict]:
    """
    Search for relevant context chunks using vector similarity.

    Uses Nomic prefix for asymmetric search.

    Args:
        query: User query to search for
        limit: Number of chunks to retrieve

    Returns:
        List of matching chunks as dicts with content, title, filename, relative_path
    """
    table = get_table()
    if table is None:
        logger.warning("LanceDB table not found - RAG context unavailable")
        return []

    model = get_model()
    # Nomic requires "search_query: " prefix for retrieval
    query_vector = model.encode(f"search_query: {query}")

    try:
        results = table.search(query_vector).limit(limit).to_list()
        return [
            {
                "content": r.get("content", ""),
                "title": r.get("title", ""),
                "filename": r.get("filename", ""),
                "relative_path": r.get("relative_path", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.error("Vector search failed: %s", e)
        return []


def format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks for prompt injection.

    Args:
        chunks: List of chunk dicts from search_context

    Returns:
        Formatted string for RAG prompt
    """
    if not chunks:
        return "(No relevant context found in vault)"

    formatted = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title") or chunk.get("filename", "Unknown")
        path = chunk.get("relative_path", "")
        content = chunk.get("content", "")
        formatted.append(f"[{i}] {title} ({path})\n{content}")

    return "\n\n---\n\n".join(formatted)


def format_context_summary(chunks: list[dict]) -> str:
    """
    Format a brief summary of retrieved context for display.

    Args:
        chunks: List of chunk dicts from search_context

    Returns:
        Brief summary string listing sources
    """
    if not chunks:
        return "No matching notes found."

    sources = []
    for chunk in chunks:
        title = chunk.get("title") or chunk.get("filename", "Unknown")
        sources.append(f"  • {title}")

    return "Retrieved context from:\n" + "\n".join(sources)


# --- CHAT SESSION ---


class ChatSession:
    """
    Orchestrates a RAG chat session.

    Combines conversation history, context retrieval, and LLM chat.
    Uses CompactingHistory when enabled, otherwise falls back to ConversationHistory.
    """

    def __init__(
        self,
        client: BaseChatClient | None = None,
        use_rag: bool = True,
        context_limit: int = CHAT_CONTEXT_LIMIT,
        max_turns: int = CHAT_MAX_TURNS,
        enable_compaction: bool = CHAT_ENABLE_COMPACTION,
        token_limit: int = CHAT_TOKEN_LIMIT,
        recent_turns: int = CHAT_RECENT_TURNS,
    ):
        self.client = client or get_chat_client()
        self.use_rag = use_rag
        self.context_limit = context_limit
        self.enable_compaction = enable_compaction
        self._last_context: list[dict] = []

        # Choose history implementation based on config
        if enable_compaction:
            self.history: CompactingHistory | ConversationHistory = CompactingHistory(
                token_limit=token_limit,
                recent_turns=recent_turns,
                summarizer=self.client,
            )
        else:
            self.history = ConversationHistory(max_turns=max_turns)

    def send(self, user_message: str) -> tuple[str, list[dict]]:
        """
        Send a user message and get assistant response.

        Args:
            user_message: The user's input

        Returns:
            Tuple of (assistant response, retrieved context chunks)
        """
        # Retrieve context if RAG enabled
        context_chunks = []
        system_prompt = None

        if self.use_rag:
            context_chunks = search_context(user_message, limit=self.context_limit)
            if context_chunks:
                context_str = format_context(context_chunks)
                system_prompt = RAG_SYSTEM_PROMPT.format(context=context_str)

        self._last_context = context_chunks

        # Add user message to history
        self.history.add("user", user_message)

        # Build final system prompt, injecting compaction summary if present
        if self.enable_compaction and isinstance(self.history, CompactingHistory):
            summary = self.history.get_summary()
            if summary:
                summary_block = f"\n\nConversation Summary (earlier context):\n{summary}"
                if system_prompt:
                    system_prompt = system_prompt + summary_block
                else:
                    system_prompt = f"Conversation Summary (earlier context):\n{summary}"

        # Get response from LLM
        response = self.client.chat(self.history.get_messages(), system_prompt=system_prompt)

        # Add assistant response to history
        self.history.add("assistant", response)

        return response, context_chunks

    def get_last_context(self) -> list[dict]:
        """Get the context chunks from the last query."""
        return self._last_context

    def clear(self) -> None:
        """Clear conversation history."""
        self.history.clear()
        self._last_context = []
