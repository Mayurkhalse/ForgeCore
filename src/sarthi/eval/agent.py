"""Sandboxed Agent Execution Loop with PathGuard Enforcement for Layer 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sarthi.core.pathguard import (
    GitDirectoryAccessError,
    PathGuard,
    PathGuardError,
    PathTraversalError,
    SecretFileAccessError,
)
from sarthi.eval.budget import BudgetExceededError, LiveEvalBudgetManager
from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.providers.base import (
    ChatMessage,
    LLMProviderAdapter,
    ToolCall,
    ToolDefinition,
    ToolResult,
)


@dataclass
class AgentTrajectory:
    """Records the execution trajectory and artifacts of an evaluated agent."""

    workspace_root: Path
    steps: int
    completed: bool
    messages: list[ChatMessage]
    tool_calls_count: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    budget_summary: dict[str, Any] = field(default_factory=dict)


class SandboxedAgentLoop:
    """Executes an AI coding agent inside an isolated workspace guarded by PathGuard."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.guard = PathGuard(self.workspace_root)
        self.tool_definitions = self._build_tool_definitions()

    def _build_tool_definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Read contents of a source or configuration file within the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to file within workspace",
                        }
                    },
                    "required": ["path"],
                },
            ),
            ToolDefinition(
                name="write_file",
                description="Write or overwrite contents of a file within the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to file within workspace",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full text contents to write",
                        },
                    },
                    "required": ["path", "content"],
                },
            ),
            ToolDefinition(
                name="list_directory",
                description="List files and directories in a given relative path within workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path (defaults to root '.')",
                        }
                    },
                },
            ),
            ToolDefinition(
                name="complete_task",
                description="Signal that implementation is finished and ready for automated verification.",
                parameters={
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Concise summary of changes made",
                        }
                    },
                    "required": ["summary"],
                },
            ),
        ]

    def dispatch_tool(self, call: ToolCall) -> ToolResult:
        """Executes a single tool call with strict PathGuard sandboxing."""
        tool_name = call.name.strip()
        args = call.arguments or {}

        try:
            if tool_name == "read_file":
                rel_path = args.get("path", "")
                if not rel_path:
                    return ToolResult(tool_call_id=call.id, output="Missing 'path' argument", is_error=True)
                content = self.guard.read_text(rel_path)
                return ToolResult(tool_call_id=call.id, output=content, is_error=False)

            elif tool_name == "write_file":
                rel_path = args.get("path", "")
                content = args.get("content", "")
                if not rel_path:
                    return ToolResult(tool_call_id=call.id, output="Missing 'path' argument", is_error=True)
                target = self.guard.safe_path(rel_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolResult(tool_call_id=call.id, output=f"Successfully wrote {rel_path}", is_error=False)

            elif tool_name == "list_directory":
                rel_path = args.get("path", ".") or "."
                target = self.guard.safe_path(rel_path)
                if not target.is_dir():
                    return ToolResult(tool_call_id=call.id, output=f"'{rel_path}' is not a directory", is_error=True)

                items = []
                for p in sorted(target.iterdir()):
                    # Avoid displaying noisy or internal directories
                    if p.name.lower() in {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}:
                        continue
                    suffix = "/" if p.is_dir() else ""
                    items.append(f"{p.name}{suffix}")
                return ToolResult(tool_call_id=call.id, output="\n".join(items) or "(empty)", is_error=False)

            elif tool_name == "complete_task":
                summary = args.get("summary", "Task completed")
                return ToolResult(tool_call_id=call.id, output=f"Task complete signal acknowledged: {summary}", is_error=False)

            else:
                return ToolResult(tool_call_id=call.id, output=f"Unknown tool '{tool_name}'", is_error=True)

        except (PathTraversalError, SecretFileAccessError, GitDirectoryAccessError, PathGuardError) as e:
            return ToolResult(tool_call_id=call.id, output=f"SECURITY_ERROR: {e}", is_error=True)
        except Exception as e:
            return ToolResult(tool_call_id=call.id, output=f"TOOL_ERROR: {e}", is_error=True)

    def run(
        self,
        provider: LLMProviderAdapter,
        system_prompt: str,
        user_prompt: str,
        budget_manager: LiveEvalBudgetManager,
        config: LiveEvalConfig,
    ) -> AgentTrajectory:
        """Runs the multi-turn agent interaction loop until completion or budget cutoff."""
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=user_prompt))

        tool_counts: dict[str, int] = {}
        completed = False
        loop_error: str | None = None

        while budget_manager.steps_count < config.max_agent_steps:
            try:
                budget_manager.record_step(config)
            except BudgetExceededError as e:
                loop_error = str(e)
                break

            # Pre-dispatch budget reservation
            model_name = getattr(provider, "model", config.model_name)
            est_input_tokens = sum(len(m.content) for m in messages) // 4 + 200
            allowed, reservation_reason = budget_manager.can_dispatch_call(
                model=model_name,
                max_tokens=config.max_tokens_per_call,
                estimated_input_tokens=est_input_tokens,
                config=config,
            )
            if not allowed:
                loop_error = reservation_reason
                break

            try:
                resp = provider.generate(
                    messages=messages,
                    tools=self.tool_definitions,
                    max_tokens=config.max_tokens_per_call,
                )
            except Exception as e:
                loop_error = f"Provider generation failed: {e}"
                break

            try:
                # Track usage and enforce financial / token budget with defensive fallbacks
                p_tokens = (
                    resp.prompt_tokens
                    if (resp.prompt_tokens is not None and resp.prompt_tokens >= 0)
                    else est_input_tokens
                )
                c_tokens = (
                    resp.completion_tokens
                    if (resp.completion_tokens is not None and resp.completion_tokens >= 0)
                    else config.max_tokens_per_call
                )
                budget_manager.record_usage(
                    model=model_name,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    config=config,
                )
            except BudgetExceededError as e:
                loop_error = str(e)
                # Still record the assistant response before exiting
                messages.append(
                    ChatMessage(
                        role="assistant",
                        content=resp.content,
                        tool_calls=resp.tool_calls,
                    )
                )
                break

            messages.append(
                ChatMessage(
                    role="assistant",
                    content=resp.content,
                    tool_calls=resp.tool_calls,
                )
            )

            if not resp.tool_calls:
                # Agent finished or replied without tool calls
                completed = True
                break

            has_completion = False
            for tc in resp.tool_calls:
                tool_counts[tc.name] = tool_counts.get(tc.name, 0) + 1
                result = self.dispatch_tool(tc)
                messages.append(
                    ChatMessage(
                        role="tool",
                        content=result.output,
                        tool_call_id=tc.id,
                    )
                )
                if tc.name == "complete_task":
                    has_completion = True

            if has_completion:
                completed = True
                break

        if not completed and loop_error is None:
            loop_error = (
                f"Agent step limit reached ({budget_manager.steps_count}/{config.max_agent_steps}) "
                "without task completion"
            )

        return AgentTrajectory(
            workspace_root=self.workspace_root,
            steps=budget_manager.steps_count,
            completed=completed,
            messages=messages,
            tool_calls_count=tool_counts,
            error=loop_error,
            budget_summary=budget_manager.summary(),
        )
