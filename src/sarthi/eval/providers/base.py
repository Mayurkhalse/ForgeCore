"""Abstract Provider Protocol & Data Models for AI Coding Agent Evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """Schema definition for a tool available to the evaluated agent."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """Structured tool call invocation made by the agent."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """Result of an executed tool returned to the agent."""

    tool_call_id: str
    output: str
    is_error: bool = False


@dataclass
class ChatMessage:
    """Message in the agent conversation trajectory."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass(frozen=True)
class ProviderResponse:
    """Unified response from an LLM provider."""

    content: str
    tool_calls: list[ToolCall]
    prompt_tokens: int
    completion_tokens: int
    raw_response: dict[str, Any] = field(default_factory=dict)


class LLMProviderAdapter(ABC):
    """Abstract interface implemented by all LLM evaluation adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'anthropic', 'gemini', 'openai', 'mock')."""
        ...

    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        """Generates a completion from the underlying model."""
        ...

