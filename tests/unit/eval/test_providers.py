"""Unit tests for Live AI Provider Adapters and Factory."""

from __future__ import annotations

import pytest

from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.providers import (
    AnthropicProviderAdapter,
    ChatMessage,
    GeminiProviderAdapter,
    MockProviderAdapter,
    OpenAIProviderAdapter,
    ProviderResponse,
    ToolCall,
    ToolDefinition,
    get_provider,
)


def test_mock_provider_adapter_default_generation():
    provider = MockProviderAdapter()
    assert provider.name == "mock"

    msg = ChatMessage(role="user", content="Hello, agent!")
    resp = provider.generate([msg])

    assert "Mock response" in resp.content
    assert resp.tool_calls == []
    assert resp.prompt_tokens > 0
    assert resp.completion_tokens > 0
    assert len(provider.call_history) == 1
    assert provider.call_history[0][0].content == "Hello, agent!"


def test_mock_provider_adapter_enqueued_responses():
    provider = MockProviderAdapter()
    tc = ToolCall(id="tc_1", name="read_file", arguments={"path": "main.py"})
    canned = ProviderResponse(
        content="Inspecting file...",
        tool_calls=[tc],
        prompt_tokens=50,
        completion_tokens=20,
    )
    provider.enqueue_response(canned)

    resp = provider.generate([ChatMessage(role="user", content="Check code")])
    assert resp.content == "Inspecting file..."
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "read_file"


def test_provider_factory_and_config():
    mock_cfg = LiveEvalConfig(provider="mock")
    prov = get_provider(mock_cfg)
    assert isinstance(prov, MockProviderAdapter)

    anthropic_cfg = LiveEvalConfig(provider="anthropic", model_name="claude-test")
    prov_anthropic = get_provider(anthropic_cfg)
    assert isinstance(prov_anthropic, AnthropicProviderAdapter)
    assert prov_anthropic.model == "claude-test"

    gemini_cfg = LiveEvalConfig(provider="gemini", model_name="gemini-test")
    prov_gemini = get_provider(gemini_cfg)
    assert isinstance(prov_gemini, GeminiProviderAdapter)
    assert prov_gemini.model == "gemini-test"

    openai_cfg = LiveEvalConfig(provider="openai", model_name="gpt-test")
    prov_openai = get_provider(openai_cfg)
    assert isinstance(prov_openai, OpenAIProviderAdapter)
    assert prov_openai.model == "gpt-test"

    with pytest.raises(ValueError, match="Unknown or unsupported provider"):
        get_provider(LiveEvalConfig(provider="unsupported"))


def test_config_credentials_validation(monkeypatch):
    cfg_mock = LiveEvalConfig(enabled=True, provider="mock")
    ok, msg = cfg_mock.validate_credentials()
    assert ok is True

    # Anthropic without key
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg_anthropic = LiveEvalConfig(enabled=True, provider="anthropic")
    ok, msg = cfg_anthropic.validate_credentials()
    assert ok is False
    assert "Missing ANTHROPIC_API_KEY" in msg

    # Anthropic with key
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    ok, msg = cfg_anthropic.validate_credentials()
    assert ok is True

    # Gemini without key
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cfg_gemini = LiveEvalConfig(enabled=True, provider="gemini")
    ok, msg = cfg_gemini.validate_credentials()
    assert ok is False

    # OpenAI without key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg_openai = LiveEvalConfig(enabled=True, provider="openai")
    ok, msg = cfg_openai.validate_credentials()
    assert ok is False


def test_anthropic_payload_conversion():
    adapter = AnthropicProviderAdapter(api_key="test-key")
    messages = [
        ChatMessage(role="system", content="You are a senior engineer."),
        ChatMessage(role="user", content="Fix the bug."),
        ChatMessage(
            role="assistant",
            content="I will call a tool.",
            tool_calls=[ToolCall(id="call_1", name="read_file", arguments={"path": "auth.py"})],
        ),
        ChatMessage(role="tool", content="file contents", tool_call_id="call_1"),
    ]
    system_prompt, converted = adapter._convert_messages(messages)
    assert system_prompt == "You are a senior engineer."
    assert len(converted) == 3
    assert converted[0]["role"] == "user"
    assert converted[1]["role"] == "assistant"
    assert converted[2]["role"] == "user"
    assert converted[2]["content"][0]["type"] == "tool_result"

    tools = [
        ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        )
    ]
    converted_tools = adapter._convert_tools(tools)
    assert len(converted_tools) == 1
    assert converted_tools[0]["name"] == "read_file"
    assert "input_schema" in converted_tools[0]


def test_gemini_payload_conversion():
    adapter = GeminiProviderAdapter(api_key="test-key")
    messages = [
        ChatMessage(role="system", content="System instruction."),
        ChatMessage(role="user", content="Task instruction."),
        ChatMessage(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="call_1", name="write_file", arguments={"path": "a.txt"})],
        ),
        ChatMessage(role="tool", content="ok", tool_call_id="call_1"),
    ]
    system_prompt, contents = adapter._convert_messages(messages)
    assert system_prompt == "System instruction."
    assert len(contents) == 3
    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"
    assert "functionCall" in contents[1]["parts"][0]
    assert contents[2]["role"] == "user"
    assert "functionResponse" in contents[2]["parts"][0]


def test_openai_payload_conversion():
    adapter = OpenAIProviderAdapter(api_key="test-key")
    messages = [
        ChatMessage(role="system", content="System instruction."),
        ChatMessage(role="user", content="Task instruction."),
        ChatMessage(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="call_1", name="write_file", arguments={"path": "a.txt"})],
        ),
        ChatMessage(role="tool", content="ok", tool_call_id="call_1"),
    ]
    converted = adapter._convert_messages(messages)
    assert len(converted) == 4
    assert converted[0]["role"] == "system"
    assert converted[2]["role"] == "assistant"
    assert "tool_calls" in converted[2]
    assert converted[3]["role"] == "tool"
    assert converted[3]["tool_call_id"] == "call_1"

