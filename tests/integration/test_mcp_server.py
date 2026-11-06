from pathlib import Path

from sarthi.mcp.tools import MCPToolHandlers

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_mcp_initialize_project():
    handlers = MCPToolHandlers()
    root = str(FIXTURES_DIR / "fastapi_app")
    res = handlers.initialize_project(root, force=True)

    assert res["status"] == "initialized"
    assert "fastapi" in res["active_layers"]
    assert "next_step" in res
    assert "core_contract_summary" in res


def test_mcp_get_project_context():
    handlers = MCPToolHandlers()
    root = str(FIXTURES_DIR / "fastapi_app")
    res = handlers.get_project_context(root)

    assert "context_version" in res
    assert "active_layers" in res
    assert "python" in res["languages"]


def test_mcp_get_standards():
    handlers = MCPToolHandlers()
    root = str(FIXTURES_DIR / "fastapi_app")
    res = handlers.get_standards(
        root=root,
        task="Create user authentication route",
        task_type="feature",
    )

    assert "rules" in res
    assert res["total_returned"] > 0
    rule_ids = [r["id"] for r in res["rules"]]
    # Should include fastapi or security or universal rules
    assert any("FAPI" in rid or "SEC" in rid or "UNI" in rid for rid in rule_ids)


def test_mcp_get_workflow():
    handlers = MCPToolHandlers()
    root = str(FIXTURES_DIR / "fastapi_app")
    res = handlers.get_workflow(root=root, task_type="feature")

    assert res["task_type"] == "feature"
    assert "## 1. Plan" in res["workflow_markdown"]
    assert "## 4. Verify" in res["workflow_markdown"]


def test_mcp_get_rule():
    handlers = MCPToolHandlers()
    res = handlers.get_rule("FAPI-ARCH-001")

    assert "error" not in res
    assert res["id"] == "FAPI-ARCH-001"
    assert "Route handlers" in res["title"]
    assert res["layer"] == "fastapi"


def test_mcp_verify_project():
    handlers = MCPToolHandlers()
    root = str(FIXTURES_DIR / "violations_app")
    res = handlers.verify_project(root=root, scope="all")

    assert res["status"] == "failed"
    assert res["summary"]["critical"] > 0
    assert len(res["findings"]) > 0
