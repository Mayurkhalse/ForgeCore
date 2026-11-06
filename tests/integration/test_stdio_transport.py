from __future__ import annotations

import os
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.anyio
@pytest.mark.parametrize(
    "cmd_args",
    [
        ["-u", "-m", "sarthi.mcp.server"],
        ["-u", "-m", "sarthi.cli", "serve"],
    ],
)
async def test_mcp_real_stdio_transport(cmd_args: list[str]) -> None:
    """Launch the Sarthi MCP server as a subprocess over real stdio.

    Verifies the real stdio transport handshake, tool listing,
    and initialize_project execution with a 25-second timeout.
    Tests both direct server entrypoint and CLI serve command.
    """
    fixture_dir = Path("tests/fixtures/fastapi_app").resolve()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=cmd_args,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    with anyio.fail_after(25):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Initialize handshake
                init_result = await session.initialize()
                assert init_result.server_info.name == "sarthi"

                # 2. List tools
                tools_result = await session.list_tools()
                tool_names = {t.name for t in tools_result.tools}
                expected_tools = {
                    "initialize_project",
                    "get_project_context",
                    "get_standards",
                    "get_workflow",
                    "get_rule",
                    "verify_project",
                }
                assert expected_tools.issubset(tool_names)

                # 3. Call initialize_project
                call_result = await session.call_tool(
                    "initialize_project",
                    {"root": str(fixture_dir)},
                )
                assert call_result.is_error is False
                assert call_result.structured_content is not None
                assert call_result.structured_content["status"] == "initialized"
                assert "fastapi" in call_result.structured_content["active_layers"]


def test_mcp_stdout_strictly_jsonrpc_only() -> None:
    """Launch the MCP server with SARTHI_DEBUG enabled over real stdio.

    Asserts that:
    1. Every line emitted on stdout is valid JSON with "jsonrpc": "2.0".
    2. Debug logs and diagnostics are routed exclusively to stderr, not stdout.
    """
    import json
    import subprocess

    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "SARTHI_DEBUG": "1",
    }
    fixture_dir = Path("tests/fixtures/fastapi_app").resolve()

    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "sarthi.mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        # 1. Send initialize request
        init_req = (
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            })
            + "\n"
        )
        proc.stdin.write(init_req)
        proc.stdin.flush()

        init_line = proc.stdout.readline()
        assert init_line.strip(), "Server produced empty output on initialize"
        init_data = json.loads(init_line)
        assert init_data.get("jsonrpc") == "2.0"
        assert init_data.get("id") == 1
        assert "serverInfo" in init_data.get("result", {})

        # 2. Send initialized notification
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        proc.stdin.write(notif)
        proc.stdin.flush()

        # 3. Send tools/list request
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
        proc.stdin.write(list_req)
        proc.stdin.flush()

        list_line = proc.stdout.readline()
        assert list_line.strip(), "Server produced empty output on tools/list"
        list_data = json.loads(list_line)
        assert list_data.get("jsonrpc") == "2.0"
        assert list_data.get("id") == 2
        assert "tools" in list_data.get("result", {})

        # 4. Call initialize_project tool
        call_req = (
            json.dumps({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "initialize_project",
                    "arguments": {"root": str(fixture_dir)},
                },
            })
            + "\n"
        )
        proc.stdin.write(call_req)
        proc.stdin.flush()

        call_line = proc.stdout.readline()
        assert call_line.strip(), "Server produced empty output on tools/call"
        call_data = json.loads(call_line)
        assert call_data.get("jsonrpc") == "2.0"
        assert call_data.get("id") == 3

    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    remaining_stdout = proc.stdout.read()
    stderr_output = proc.stderr.read()

    for line in remaining_stdout.splitlines():
        trimmed = line.strip()
        if trimmed:
            data = json.loads(trimmed)
            assert data.get("jsonrpc") == "2.0", f"Non-JSONRPC line on stdout: {trimmed}"

    assert "SARTHI_DEBUG enabled" in stderr_output
    assert "logging routed to stderr" in stderr_output
