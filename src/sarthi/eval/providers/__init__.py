"""Provider Registry and Factory for Layer 4 Evaluations."""

from __future__ import annotations

from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.providers.anthropic import AnthropicProviderAdapter
from sarthi.eval.providers.base import (
    ChatMessage,
    LLMProviderAdapter,
    ProviderResponse,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from sarthi.eval.providers.gemini import GeminiProviderAdapter
from sarthi.eval.providers.mock import MockProviderAdapter
from sarthi.eval.providers.openai import OpenAIProviderAdapter

__all__ = [
    "LLMProviderAdapter",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "ChatMessage",
    "ProviderResponse",
    "MockProviderAdapter",
    "AnthropicProviderAdapter",
    "GeminiProviderAdapter",
    "OpenAIProviderAdapter",
    "get_provider",
]


def get_provider(config: LiveEvalConfig) -> LLMProviderAdapter:
    """Instantiates the appropriate provider adapter according to configuration."""
    provider_name = config.provider.lower().strip()
    if provider_name == "mock":
        return MockProviderAdapter()
    elif provider_name == "anthropic":
        return AnthropicProviderAdapter(model=config.model_name)
    elif provider_name == "gemini":
        return GeminiProviderAdapter(model=config.model_name)
    elif provider_name == "openai":
        return OpenAIProviderAdapter(model=config.model_name)
    else:
        raise ValueError(f"Unknown or unsupported provider: '{provider_name}'")

