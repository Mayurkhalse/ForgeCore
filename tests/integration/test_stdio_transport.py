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
        ["-u", "-m", "forgecore.mcp.server"],
        ["-u", "-m", "forgecore.cli", "serve"],
    ],
)
async def test_mcp_real_stdio_transport(cmd_args: list[str]) -> None:
    """Launch the ForgeCore MCP server as a subprocess over real stdio.

    Verifies the real stdio transport handshake, tool listing,
    and initialize_project execution with a hard 10-second timeout.
    Tests both direct server entrypoint and CLI serve command.
    """
    fixture_dir = Path("tests/fixtures/fastapi_app").resolve()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=cmd_args,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    with anyio.fail_after(10):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Initialize handshake
                init_result = await session.initialize()
                assert init_result.server_info.name == "forgecore"

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
