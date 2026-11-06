"""Google Gemini Provider Adapter for Live AI Evaluation."""

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


class GeminiProviderAdapter(LLMProviderAdapter):
    """Adapter for Google Gemini models via REST API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-pro-latest") -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model

    @property
    def name(self) -> str:
        return "gemini"

    def _convert_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]]:
        if not tools:
            return []
        declarations = []
        for t in tools:
            declarations.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            })
        return [{"functionDeclarations": declarations}]

    def _convert_messages(self, messages: list[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        system_prompt = ""
        contents = []

        for msg in messages:
            if msg.role == "system":
                system_prompt += f"{msg.content}\n"
                continue

            role = "user" if msg.role in {"user", "tool"} else "model"
            parts: list[dict[str, Any]] = []

            if msg.role == "tool":
                parts.append({
                    "functionResponse": {
                        "name": msg.tool_call_id or "tool_response",
                        "response": {"output": msg.content},
                    }
                })
            else:
                if msg.content:
                    parts.append({"text": msg.content})
                for tc in msg.tool_calls:
                    parts.append({
                        "functionCall": {
                            "name": tc.name,
                            "args": tc.arguments,
                        }
                    })

            if parts:
                contents.append({"role": role, "parts": parts})

        return system_prompt.strip(), contents

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ProviderResponse:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        system_prompt, contents = self._convert_messages(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            payload["tools"] = converted_tools

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_body,
            headers={"content-type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error (HTTP {e.code}): {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Gemini API: {e}") from e

        text_content = ""
        tool_calls: list[ToolCall] = []

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for idx, part in enumerate(parts):
                if "text" in part:
                    text_content += part["text"]
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{idx}",
                            name=fc.get("name", ""),
                            arguments=fc.get("args", {}),
                        )
                    )

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        return ProviderResponse(
            content=text_content,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=data,
        )

