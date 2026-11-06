"""Unit tests for Sandboxed Agent Loop and Security Enforcement."""

from __future__ import annotations

import pytest

from sarthi.eval.agent import SandboxedAgentLoop
from sarthi.eval.budget import LiveEvalBudgetManager
from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.providers.base import ProviderResponse, ToolCall
from sarthi.eval.providers.mock import MockProviderAdapter


@pytest.fixture
def agent_sandbox(tmp_path):
    workspace = tmp_path / "agent_ws"
    workspace.mkdir()
    (workspace / "main.py").write_text("# initial main\n", encoding="utf-8")
    (workspace / ".env").write_text("SECRET_KEY=12345\n", encoding="utf-8")
    return workspace


def test_sandbox_tool_dispatch_read_and_write(agent_sandbox):
    loop = SandboxedAgentLoop(agent_sandbox)

    # 1. Read existing file
    res_read = loop.dispatch_tool(
        ToolCall(id="tc1", name="read_file", arguments={"path": "main.py"})
    )
    assert res_read.is_error is False
    assert res_read.output == "# initial main\n"

    # 2. Write updated file
    res_write = loop.dispatch_tool(
        ToolCall(
            id="tc2",
            name="write_file",
            arguments={"path": "main.py", "content": "print('updated')\n"},
        )
    )
    assert res_write.is_error is False
    assert (agent_sandbox / "main.py").read_text(encoding="utf-8") == "print('updated')\n"

    # 3. List directory
    res_list = loop.dispatch_tool(
        ToolCall(id="tc3", name="list_directory", arguments={"path": "."})
    )
    assert res_list.is_error is False
    assert "main.py" in res_list.output


def test_sandbox_pathguard_blocks_secret_file(agent_sandbox):
    loop = SandboxedAgentLoop(agent_sandbox)
    res = loop.dispatch_tool(
        ToolCall(id="tc_sec", name="read_file", arguments={"path": ".env"})
    )
    assert res.is_error is True
    assert "SECURITY_ERROR" in res.output
    assert "sensitive secret file" in res.output


def test_sandbox_pathguard_blocks_traversal_escape(agent_sandbox):
    loop = SandboxedAgentLoop(agent_sandbox)
    res = loop.dispatch_tool(
        ToolCall(id="tc_trav", name="read_file", arguments={"path": "../../../etc/passwd"})
    )
    assert res.is_error is True
    assert "SECURITY_ERROR" in res.output


def test_agent_multi_turn_loop_execution(agent_sandbox):
    loop = SandboxedAgentLoop(agent_sandbox)
    provider = MockProviderAdapter()

    # Step 1: Agent reads file
    provider.enqueue_response(
        ProviderResponse(
            content="Reading file",
            tool_calls=[ToolCall(id="c1", name="read_file", arguments={"path": "main.py"})],
            prompt_tokens=50,
            completion_tokens=20,
        )
    )
    # Step 2: Agent writes file and completes task
    provider.enqueue_response(
        ProviderResponse(
            content="Writing patch and completing",
            tool_calls=[
                ToolCall(id="c2", name="write_file", arguments={"path": "main.py", "content": "# patched"}),
                ToolCall(id="c3", name="complete_task", arguments={"summary": "done"}),
            ],
            prompt_tokens=80,
            completion_tokens=30,
        )
    )

    budget = LiveEvalBudgetManager()
    config = LiveEvalConfig(max_agent_steps=4)

    trajectory = loop.run(
        provider=provider,
        system_prompt="You are an engineer.",
        user_prompt="Patch main.py",
        budget_manager=budget,
        config=config,
    )

    assert trajectory.completed is True
    assert trajectory.error is None
    assert trajectory.steps == 2
    assert trajectory.tool_calls_count["read_file"] == 1
    assert trajectory.tool_calls_count["write_file"] == 1
    assert trajectory.tool_calls_count["complete_task"] == 1
    assert (agent_sandbox / "main.py").read_text(encoding="utf-8") == "# patched"


def test_agent_loop_halts_on_budget_exhaustion(agent_sandbox):
    loop = SandboxedAgentLoop(agent_sandbox)
    provider = MockProviderAdapter()

    # Agent attempts infinite loop
    provider.enqueue_response(
        ProviderResponse(
            content="Step 1",
            tool_calls=[ToolCall(id="c1", name="list_directory", arguments={})],
            prompt_tokens=200,
            completion_tokens=50,
        )
    )
    provider.enqueue_response(
        ProviderResponse(
            content="Step 2",
            tool_calls=[ToolCall(id="c2", name="list_directory", arguments={})],
            prompt_tokens=200,
            completion_tokens=50,
        )
    )

    budget = LiveEvalBudgetManager()
    config = LiveEvalConfig(max_agent_steps=1)  # Only 1 step permitted

    trajectory = loop.run(
        provider=provider,
        system_prompt="System",
        user_prompt="Prompt",
        budget_manager=budget,
        config=config,
    )

    assert trajectory.completed is False
    assert trajectory.error is not None
    assert "Agent step limit reached" in trajectory.error
