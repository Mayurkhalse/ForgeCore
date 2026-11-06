"""OpenAI Provider Adapter for Live AI Evaluation."""

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


class OpenAIProviderAdapter(LLMProviderAdapter):
    """Adapter for OpenAI models via REST API."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o") -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model

    @property
    def name(self) -> str:
        return "openai"

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]]:
        if not tools:
            return []
        converted = []
        for t in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            })
        return converted

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        converted = []
        for msg in messages:
            entry: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content or "",
            }
            if msg.role == "tool" and msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            converted.append(entry)
        return converted

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        converted_messages = self._convert_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            payload["tools"] = converted_tools

        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=req_body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error (HTTP {e.code}): {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to connect to OpenAI API: {e}") from e

        choices = data.get("choices", [])
        msg = choices[0].get("message", {}) if choices else {}
        text_content = msg.get("content") or ""

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=fn.get("name", ""),
                    arguments=args,
                )
            )

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return ProviderResponse(
            content=text_content,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=data,
        )

