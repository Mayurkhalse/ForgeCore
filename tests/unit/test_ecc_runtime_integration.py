"""Tests for runtime context compilation, MCP tool integration, and prompt assembly."""
from __future__ import annotations

from pathlib import Path

from sarthi.core.resources.compiler import ContextCompiler
from sarthi.mcp.tools import MCPToolHandlers


def test_context_compiler_structured_output():
    """Verifies that ContextCompiler generates complete structured context with security and provenance."""
    compiler = ContextCompiler()
    ctx = compiler.compile_context(
        active_layers=["universal", "security", "fastapi", "python"],
        task="Build FastAPI authentication route with JWT rotation",
        task_type="feature",
        max_tokens=3000,
    )

    assert len(ctx.security_invariants) >= 5
    assert len(ctx.core_contract_rules) >= 1
    assert len(ctx.native_standards) > 0
    assert len(ctx.ecc_skills) > 0
    assert len(ctx.provenance_records) > 0
    assert ctx.selection_trace.token_count <= 3000

    # Render Markdown
    md = compiler.render_markdown_instructions(ctx)
    assert "# Sarthi Engineering Intelligence Instructions" in md
    assert "[SECURITY]" in md
    assert "[CONTRACT]" in md
    assert "Fastapi Patterns" in md or "fastapi" in md.lower()
    assert "c05b2d6" in md


def test_mcp_initialize_project_reports_ecc_capabilities(tmp_path: Path):
    """Verifies that initialize_project returns knowledge providers and available ECC resource count."""
    handlers = MCPToolHandlers()
    init_res = handlers.initialize_project(root=str(tmp_path))

    assert init_res["status"] == "initialized"
    assert "knowledge_providers" in init_res
    assert "ecc" in init_res["knowledge_providers"]
    assert init_res["total_available_resources"] > 500


def test_mcp_get_standards_includes_skills_and_provenance(tmp_path: Path):
    """Verifies that get_standards includes selected ECC skills, conflict reports, and provenance."""
    handlers = MCPToolHandlers()
    handlers.initialize_project(root=str(tmp_path))

    standards_res = handlers.get_standards(
        root=str(tmp_path),
        task="Implement FastAPI login route with rate limiting",
        task_type="feature",
        layers=["universal", "security", "fastapi", "python"],
    )

    assert "rules" in standards_res
    assert len(standards_res["rules"]) > 0
    assert "skills" in standards_res
    assert "conflict_report" in standards_res
    assert "provenance" in standards_res
    assert any(p["commit"] == "c05b2d6614f62f6db0047669aa4eefb223d478f9" for p in standards_res["provenance"])


def test_mcp_get_rule_retrieves_ecc_resources():
    """Verifies that get_rule can retrieve both native YAML rules and full ECC skill markdown."""
    handlers = MCPToolHandlers()

    # 1. Native rule
    native_rule = handlers.get_rule("FAPI-ARCH-001")
    assert "id" in native_rule
    assert native_rule["id"] == "FAPI-ARCH-001"

    # 2. ECC skill
    ecc_skill = handlers.get_rule("ecc.skill.tdd-workflow")
    assert "id" in ecc_skill
    assert ecc_skill["id"] == "ecc.skill.tdd-workflow"
    assert ecc_skill["provider"] == "ecc"
    assert len(ecc_skill["content"]) > 1000


def test_mcp_resource_read_ecc():
    """Verifies reading an ECC resource directly through MCPResources."""
    import json

    from sarthi.mcp.resources import MCPResources

    res_mgr = MCPResources()
    raw = res_mgr.get_ecc_resource("ecc.skill.fastapi-patterns")
    data = json.loads(raw)
    assert data["id"] == "ecc.skill.fastapi-patterns"
    assert "Fastapi" in data["name"]
    assert len(data["content"]) > 500
