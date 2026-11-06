from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from forgecore.mcp.prompts import PROMPT_TEMPLATES
from forgecore.mcp.resources import MCPResources
from forgecore.mcp.tools import MCPToolHandlers

logger = logging.getLogger("forgecore")


def configure_logging() -> None:
    """Routes all logging to stderr so stdout remains exclusively reserved for the JSON-RPC protocol."""
    debug_enabled = os.environ.get("FORGECORE_DEBUG", "").lower() in {"1", "true", "yes"}
    log_level = logging.DEBUG if debug_enabled else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to prevent duplicate or stdout logging
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    logger.setLevel(log_level)
    if debug_enabled:
        logger.debug("FORGECORE_DEBUG enabled: all logging routed to stderr.")


def create_server(standards_dir: Path | str | None = None) -> MCPServer:
    resources_mgr = MCPResources(standards_dir)
    handlers = MCPToolHandlers(standards_dir)

    # Core contract as server instructions
    contract = resources_mgr.get_contract()

    server = MCPServer(
        name="forgecore",
        instructions=contract,
    )

    # 1. Register Tools
    @server.tool(name="initialize_project", description="Detects project stack, active layers, and initializes ForgeCore context.")
    def initialize_project(root: str = ".", force: bool = False) -> dict[str, Any]:
        return handlers.initialize_project(root, force=force)

    @server.tool(name="get_project_context", description="Retrieves cached project context and staleness status.")
    def get_project_context(root: str = ".") -> dict[str, Any]:
        return handlers.get_project_context(root)

    @server.tool(name="get_standards", description="Retrieves ranked, budgeted engineering standards for the active task.")
    def get_standards(
        task: str,
        root: str = ".",
        task_type: str = "feature",
        layers: list[str] | None = None,
        max_rules: int = 15,
    ) -> dict[str, Any]:
        return handlers.get_standards(root=root, task=task, task_type=task_type, layers=layers, max_rules=max_rules)

    @server.tool(name="get_workflow", description="Returns step-by-step workflow with project-specific verification commands.")
    def get_workflow(root: str = ".", task_type: str = "feature") -> dict[str, Any]:
        return handlers.get_workflow(root=root, task_type=task_type)

    @server.tool(name="get_rule", description="Fetches full details, rationale, examples, and verifier for a specific rule ID.")
    def get_rule(rule_id: str) -> dict[str, Any]:
        return handlers.get_rule(rule_id)

    @server.tool(name="verify_project", description="Runs deterministic verifiers (ruff, semgrep, tests, secrets) and returns structured report.")
    def verify_project(root: str = ".", scope: str = "changed", checks: list[str] | None = None) -> dict[str, Any]:
        return handlers.verify_project(root=root, scope=scope, checks=checks)

    # 2. Register Resources
    @server.resource("forgecore://contract", description="The ForgeCore Core Contract")
    def get_contract_resource() -> str:
        return resources_mgr.get_contract()

    @server.resource("forgecore://standards/{layer}", description="All rules for a specific architectural layer")
    def get_layer_resource(layer: str) -> str:
        return resources_mgr.get_layer_standards(layer)

    @server.resource("forgecore://workflows/{task_type}", description="Task workflow template")
    def get_workflow_resource(task_type: str) -> str:
        return resources_mgr.get_workflow_template(task_type)

    @server.resource("forgecore://ecc/{resource_id}", description="Everything Claude Code (ECC) bundled knowledge resource")
    def get_ecc_resource(resource_id: str) -> str:
        return resources_mgr.get_ecc_resource(resource_id)

    # 3. Register Prompts
    @server.prompt("new-feature", description="Prompt template for implementing a new feature with ForgeCore discipline")
    def prompt_new_feature(task: str) -> str:
        return PROMPT_TEMPLATES["new-feature"].format(task=task)

    @server.prompt("fix-bug", description="Prompt template for fixing a bug with regression tests and verification")
    def prompt_fix_bug(description: str) -> str:
        return PROMPT_TEMPLATES["fix-bug"].format(description=description)

    @server.prompt("refactor", description="Prompt template for refactoring code with architectural discipline")
    def prompt_refactor(scope: str) -> str:
        return PROMPT_TEMPLATES["refactor"].format(scope=scope)

    @server.prompt("new-project", description="Prompt template for scaffolding a new project skeleton")
    def prompt_new_project(name: str) -> str:
        return PROMPT_TEMPLATES["new-project"].format(name=name)

    return server


def run_server() -> None:
    """Entrypoint to run the MCP server over stdio."""
    configure_logging()
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    run_server()
