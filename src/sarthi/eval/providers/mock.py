"""Deterministic Mock LLM Provider for Offline Layer 4 Testing."""

from __future__ import annotations

from sarthi.eval.providers.base import (
    ChatMessage,
    LLMProviderAdapter,
    ProviderResponse,
    ToolCall,
    ToolDefinition,
)


class MockProviderAdapter(LLMProviderAdapter):
    """Zero-network, deterministic provider adapter for offline evaluation testing."""

    def __init__(
        self,
        canned_responses: list[ProviderResponse] | None = None,
        default_tool_calls: list[ToolCall] | None = None,
    ) -> None:
        self._responses = list(canned_responses) if canned_responses else []
        self._default_tool_calls = default_tool_calls or []
        self.call_history: list[list[ChatMessage]] = []

    @property
    def name(self) -> str:
        return "mock"

    def enqueue_response(self, response: ProviderResponse) -> None:
        """Enqueues a pre-configured response for sequential delivery."""
        self._responses.append(response)

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        self.call_history.append(list(messages))

        if self._responses:
            return self._responses.pop(0)

        # Default fallback behavior: return default tool calls or a text completion
        if self._default_tool_calls:
            return ProviderResponse(
                content="Executing requested tool calls.",
                tool_calls=self._default_tool_calls,
                prompt_tokens=120,
                completion_tokens=40,
                raw_response={"status": "mock_tool_calls"},
            )

        return ProviderResponse(
            content="Mock response: Task completed successfully.",
            tool_calls=[],
            prompt_tokens=100,
            completion_tokens=25,
            raw_response={"status": "mock_completed"},
        )
