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


def test_sandbox_pathguard_blocks_git_access(agent_sandbox):
    """Verifies that agents cannot read, write, list, or traverse into .git directories."""
    # Create a dummy .git directory and hooks
    git_dir = agent_sandbox / ".git"
    git_dir.mkdir(exist_ok=True)
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    loop = SandboxedAgentLoop(agent_sandbox)

    # 1. Block reading .git/config
    res_read = loop.dispatch_tool(
        ToolCall(id="tc_git_read", name="read_file", arguments={"path": ".git/config"})
    )
    assert res_read.is_error is True
    assert "SECURITY_ERROR" in res_read.output
    assert ".git" in res_read.output

    # 2. Block writing to .git/hooks/pre-commit
    res_hook = loop.dispatch_tool(
        ToolCall(
            id="tc_git_hook",
            name="write_file",
            arguments={"path": ".git/hooks/pre-commit", "content": "#!/bin/sh\nmalicious\n"},
        )
    )
    assert res_hook.is_error is True
    assert "SECURITY_ERROR" in res_hook.output
    assert not (hooks_dir / "pre-commit").exists()

    # 3. Block writing to .git/config
    res_cfg_write = loop.dispatch_tool(
        ToolCall(
            id="tc_git_cfg",
            name="write_file",
            arguments={"path": ".git/config", "content": "[malicious]\n"},
        )
    )
    assert res_cfg_write.is_error is True
    assert "SECURITY_ERROR" in res_cfg_write.output

    # 4. Block case-insensitive variations (.GIT, .Git)
    res_case = loop.dispatch_tool(
        ToolCall(
            id="tc_git_case",
            name="write_file",
            arguments={"path": ".GIT/hooks/pre-commit", "content": "#!/bin/sh\n"},
        )
    )
    assert res_case.is_error is True
    assert "SECURITY_ERROR" in res_case.output

    # 5. Block nested subdirectories containing .git
    res_nested = loop.dispatch_tool(
        ToolCall(
            id="tc_git_nested",
            name="write_file",
            arguments={"path": "submodule/.git/config", "content": "[core]\n"},
        )
    )
    assert res_nested.is_error is True
    assert "SECURITY_ERROR" in res_nested.output

    # 6. Block listing .git directory directly
    res_list = loop.dispatch_tool(
        ToolCall(id="tc_git_list", name="list_directory", arguments={"path": ".git"})
    )
    assert res_list.is_error is True
    assert "SECURITY_ERROR" in res_list.output

    # 7. Block path traversal attempting to reach .git
    res_trav = loop.dispatch_tool(
        ToolCall(id="tc_git_trav", name="read_file", arguments={"path": "../.git/config"})
    )
    assert res_trav.is_error is True
    assert "SECURITY_ERROR" in res_trav.output



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


def test_agent_loop_halts_on_pre_dispatch_budget_failure(agent_sandbox):
    """Verifies that the agent loop stops before dispatching to provider if worst-case cost exceeds cap."""
    loop = SandboxedAgentLoop(agent_sandbox)
    provider = MockProviderAdapter()
    provider.model = "claude-3-5-sonnet-20241022"

    provider.enqueue_response(
        ProviderResponse(
            content="Should never be called",
            tool_calls=[],
            prompt_tokens=100,
            completion_tokens=20,
        )
    )

    budget = LiveEvalBudgetManager()
    # Claude 3.5 Sonnet worst-case for 4000 max tokens is ~$0.063. Cap is $0.01.
    config = LiveEvalConfig(cost_cap_usd=0.01, max_tokens_per_call=4000)

    trajectory = loop.run(
        provider=provider,
        system_prompt="System",
        user_prompt="Prompt",
        budget_manager=budget,
        config=config,
    )

    assert trajectory.completed is False
    assert trajectory.error is not None
    assert "Pre-dispatch budget reservation failed" in trajectory.error
    # Provider queue was never dequeued!
    assert len(provider._responses) == 1

