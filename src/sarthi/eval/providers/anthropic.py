"""Anthropic Claude Provider Adapter for Live AI Evaluation."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from sarthi.eval.providers.base import (
    ChatMessage,
    LLMProviderAdapter,
    ProviderResponse,
    ToolCall,
    ToolDefinition,
)


class AnthropicProviderAdapter(LLMProviderAdapter):
    """Adapter for Anthropic Claude models via standard HTTPS REST API."""

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022") -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model

    @property
    def name(self) -> str:
        return "anthropic"

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]]:
        if not tools:
            return []
        converted = []
        for t in tools:
            converted.append({
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            })
        return converted

    def _convert_messages(self, messages: list[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        system_prompt = ""
        converted = []

        for msg in messages:
            if msg.role == "system":
                system_prompt += f"{msg.content}\n"
                continue

            if msg.role == "tool":
                converted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "tool_0",
                            "content": msg.content,
                        }
                    ],
                })
            elif msg.role == "assistant":
                content_blocks: list[dict[str, Any]] = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                converted.append({"role": "assistant", "content": content_blocks or msg.content})
            else:  # user
                converted.append({"role": "user", "content": msg.content})

        return system_prompt.strip(), converted

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        system_prompt, converted_messages = self._convert_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": converted_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            payload["tools"] = converted_tools

        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=req_body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION,
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error (HTTP {e.code}): {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Anthropic API: {e}") from e

        # Parse content and tool calls
        text_content = ""
        tool_calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                    )
                )

        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)

        return ProviderResponse(
            content=text_content,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=data,
        )

