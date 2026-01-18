"""Tests for the chat module."""

from unittest.mock import MagicMock, patch

import pytest

from obsidian.chat import (
    ChatSession,
    ClaudeChatClient,
    ConversationHistory,
    GeminiChatClient,
    Message,
    OllamaChatClient,
    format_context,
    format_context_summary,
    get_chat_client,
)


class TestMessage:
    """Tests for the Message model."""

    def test_user_message(self):
        """Message should accept user role."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_assistant_message(self):
        """Message should accept assistant role."""
        msg = Message(role="assistant", content="Hi there")
        assert msg.role == "assistant"
        assert msg.content == "Hi there"


class TestConversationHistory:
    """Tests for ConversationHistory."""

    def test_add_message(self):
        """Messages should be added correctly."""
        history = ConversationHistory(max_turns=10)
        history.add("user", "Hello")
        history.add("assistant", "Hi")

        messages = history.get_messages()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"

    def test_respects_max_turns(self):
        """History should trim old messages when exceeding max_turns."""
        history = ConversationHistory(max_turns=2)

        # Add 3 turns (6 messages)
        for i in range(3):
            history.add("user", f"User {i}")
            history.add("assistant", f"Assistant {i}")

        messages = history.get_messages()
        # Should keep only last 2 turns (4 messages)
        assert len(messages) == 4
        assert messages[0].content == "User 1"
        assert messages[-1].content == "Assistant 2"

    def test_clear(self):
        """Clear should remove all messages."""
        history = ConversationHistory()
        history.add("user", "test")
        history.clear()

        assert len(history.get_messages()) == 0

    def test_to_ollama_format(self):
        """Should convert to Ollama API format."""
        history = ConversationHistory()
        history.add("user", "Hello")
        history.add("assistant", "Hi")

        result = history.to_ollama_format()
        assert result == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

    def test_to_gemini_format(self):
        """Should convert to Gemini API format with role mapping."""
        history = ConversationHistory()
        history.add("user", "Hello")
        history.add("assistant", "Hi")

        result = history.to_gemini_format()
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "model"  # Gemini uses "model" for assistant


class TestContextFormatting:
    """Tests for context formatting functions."""

    def test_format_context_empty(self):
        """Empty chunks should return placeholder message."""
        result = format_context([])
        assert "No relevant context" in result

    def test_format_context_single(self):
        """Single chunk should format correctly."""
        chunks = [{"title": "Test Note", "relative_path": "notes/test.md", "content": "Test content here."}]
        result = format_context(chunks)

        assert "Test Note" in result
        assert "notes/test.md" in result
        assert "Test content here." in result

    def test_format_context_multiple(self):
        """Multiple chunks should be separated."""
        chunks = [
            {"title": "Note 1", "relative_path": "a.md", "content": "Content 1"},
            {"title": "Note 2", "relative_path": "b.md", "content": "Content 2"},
        ]
        result = format_context(chunks)

        assert "Note 1" in result
        assert "Note 2" in result
        assert "---" in result  # Separator

    def test_format_context_summary_empty(self):
        """Empty chunks should return 'no matching' message."""
        result = format_context_summary([])
        assert "No matching notes" in result

    def test_format_context_summary_lists_sources(self):
        """Summary should list note titles."""
        chunks = [
            {"title": "My Note", "filename": "note.md"},
            {"title": "", "filename": "other.md"},  # Falls back to filename
        ]
        result = format_context_summary(chunks)

        assert "My Note" in result
        assert "other.md" in result


class TestGetChatClient:
    """Tests for the get_chat_client factory function."""

    def test_returns_ollama_by_default(self, monkeypatch):
        """get_chat_client should return OllamaClient when backend is ollama."""
        import obsidian.chat

        obsidian.chat._chat_client = None
        monkeypatch.setattr("obsidian.chat.CHAT_BACKEND", "ollama")

        client = get_chat_client()
        assert isinstance(client, OllamaChatClient)

    def test_singleton_pattern(self, monkeypatch):
        """get_chat_client should return the same instance on repeated calls."""
        import obsidian.chat

        obsidian.chat._chat_client = None
        monkeypatch.setattr("obsidian.chat.CHAT_BACKEND", "ollama")

        client1 = get_chat_client()
        client2 = get_chat_client()
        assert client1 is client2

    def test_unknown_backend_raises_error(self, monkeypatch):
        """Unknown backend should raise ValueError."""
        import obsidian.chat

        obsidian.chat._chat_client = None
        monkeypatch.setattr("obsidian.chat.CHAT_BACKEND", "unknown")

        with pytest.raises(ValueError, match="Unknown chat backend"):
            get_chat_client()

    def test_claude_requires_api_key(self, monkeypatch):
        """Claude client should require API key."""
        import obsidian.chat

        obsidian.chat._chat_client = None
        monkeypatch.setattr("obsidian.chat.CHAT_BACKEND", "claude")
        monkeypatch.setattr("obsidian.chat.ANTHROPIC_API_KEY", None)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            get_chat_client()

    def test_gemini_requires_api_key(self, monkeypatch):
        """Gemini client should require API key."""
        import obsidian.chat

        obsidian.chat._chat_client = None
        monkeypatch.setattr("obsidian.chat.CHAT_BACKEND", "gemini")
        monkeypatch.setattr("obsidian.chat.GOOGLE_API_KEY", None)

        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            get_chat_client()


class TestChatSession:
    """Tests for ChatSession orchestrator."""

    def test_session_initialization(self, monkeypatch):
        """ChatSession should initialize with default client."""
        mock_client = MagicMock()
        session = ChatSession(client=mock_client, use_rag=False)

        assert session.client is mock_client
        assert session.use_rag is False

    @patch("obsidian.chat.search_context")
    def test_send_without_rag(self, mock_search, monkeypatch):
        """ChatSession with use_rag=False should not search context."""
        mock_client = MagicMock()
        mock_client.chat.return_value = "Response"

        session = ChatSession(client=mock_client, use_rag=False)
        response, chunks = session.send("Hello")

        mock_search.assert_not_called()
        assert response == "Response"
        assert chunks == []

    @patch("obsidian.chat.search_context")
    def test_send_with_rag(self, mock_search, monkeypatch):
        """ChatSession with RAG should search and include context."""
        mock_search.return_value = [{"title": "Note", "content": "Context"}]
        mock_client = MagicMock()
        mock_client.chat.return_value = "Response with context"

        session = ChatSession(client=mock_client, use_rag=True)
        response, chunks = session.send("Question")

        mock_search.assert_called_once()
        assert len(chunks) == 1
        # Verify system prompt was passed with context
        call_args = mock_client.chat.call_args
        assert call_args.kwargs.get("system_prompt") is not None

    def test_clear_resets_state(self):
        """Clear should reset history and context."""
        mock_client = MagicMock()
        session = ChatSession(client=mock_client, use_rag=False)
        session.history.add("user", "test")
        session._last_context = [{"test": "context"}]

        session.clear()

        assert len(session.history.get_messages()) == 0
        assert session.get_last_context() == []
